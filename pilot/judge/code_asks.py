"""ask_teacher 問題內容分類（Karabenick：工具性 vs 執行性求助）。

INFO   詢問缺少／題目中的某個條件（工具性）
METHOD 詢問解法、運算方式或提示（工具性）
VERIFY 確認自己的答案或推理（工具性，自我檢核）
EXEC   轉貼整題、直接要答案、要老師幫忙算（執行性）
OTHER  亂碼或無法判斷

先用規則分類；Claude 人工判定一個分層樣本（ask_sample_labels.json），用來估計規則的準確度。
"""
import difflib
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MISSING = re.compile(r"not (?:provide|specif|give|mention|state)|doesn't (?:provide|specify|give|mention|say|state)|"
                     r"isn't (?:given|provided|specified|mentioned)|is not (?:given|provided|specified|mentioned)|missing|"
                     r"incomplete|no (?:information|total|specific)|not enough information|"
                     r"沒有(?:提到|說明|提供|給|告訴)|没有(?:提到|说明|提供|给)|未(?:說明|提供|給出)|遺漏|遗漏|漏[掉了給]|缺少|不完整|"
                     r"有給出.*嗎|有提供.*嗎", re.I)
VERIFY = re.compile(r"對[嗎吗]|对吗|正確[嗎吗]|正确吗|是不是|沒錯|答案是[^。？?]{0,15}[嗎吗]|就是.{0,30}[嗎吗]|"
                    r"是要[^。？?]{0,20}[嗎吗]|可以用[^。？?]*\d[^。？?]*[嗎吗]|一直[減减加][^。？?]*[嗎吗]|"
                    r"is (?:that|this|it|my answer|the answer) (?:right|correct)|is \d+ (?:right|correct)|correct\?|"
                    r"is the answer|does (?:that|this) mean|so (?:the answer|.{0,30}) is .{0,20}\?|do i (?:add|subtract)|"
                    r"can i (?:add|subtract|solve this by|use (?:addition|subtraction) by|calculate \d|find the total by)|"
                    r"does \w+ have \d+", re.I)
METHOD = re.compile(r"怎麼|怎么|如何|該用|应该用|應該用|用什麼|什麼運算|加法還是減法|加法还是减法|可以用.{0,15}[嗎吗]|怎樣|怎样|能用|方法|提示|列式|"
                    r"how (?:should|do|can|would|to|could)|which operation|what (?:math )?operation|can i use|could i use|"
                    r"should i use|can i solve .* using|hint|approach|method|equation|definition|what does .* (?:mean|represent)|"
                    r"is there a way", re.I)
COMPUTE = re.compile(r"等於多少|等于多少|要[減减加]幾次|=\s*[?？]|what number|equals? \d|help me solve|solve (?:this|it) for me|"
                     r"答案是多少|告訴我答案|告诉我答案|幫我算|帮我算|幫助計算|帮助计算|請計算|请计算", re.I)
QUANTITY = re.compile(r"多少|幾|几|how many|how much|how long|how far|what (?:is|was) the (?:number|total|price|cost|amount)", re.I)


def similarity(a, b):
    a, b = re.sub(r"\s", "", a.lower()), re.sub(r"\s", "", b.lower())
    return difflib.SequenceMatcher(None, a, b).ratio()


def rule_code(question, problem, need, teacher_info):
    """問題內容 → INFO / METHOD / VERIFY / EXEC / OTHER。teacher_info 是缺條件題中缺少的那句資訊。"""
    q = question.strip()
    if not q or len(re.findall(r"\\u[0-9a-f]{4}|\u3000", q)) > 5:
        return "OTHER"
    target = re.split(r"[。.!！]", problem.rstrip("？? "))[-1]  # 題目最後的問句
    if MISSING.search(q):
        return "INFO"
    if COMPUTE.search(q):
        return "EXEC"
    if VERIFY.search(q):
        return "VERIFY"
    if METHOD.search(q):
        return "METHOD"
    if similarity(q, problem) >= 0.6:
        return "EXEC"
    if QUANTITY.search(q) or re.search(r"price|cost|initial|original|start|總數|原本|總共", q, re.I):
        # 缺條件題：除非幾乎就是題目本身的問句，否則視為在問缺少的條件
        if need == "missing" and similarity(q, target) < 0.8:
            return "INFO"
        return "EXEC"
    return "OTHER"


def iter_asks():
    items = {it["id"]: it for it in json.loads((ROOT / "items" / "pilot_items.json").read_text())}
    for f in glob.glob(str(ROOT / "results" / "*.jsonl")) + glob.glob(str(ROOT / "results" / "step1" / "*.jsonl")):
        if "textask" in f:
            continue
        for line in open(f):
            r = json.loads(line)
            it = items[r["item"]]
            problem = it[f"missing_{r['lang']}"] if r["need"] == "missing" else it[f"complete_{r['lang']}"]
            for i, a in enumerate(r["actions"]):
                if a["tool"] == "ask_teacher":
                    yield r, i, str(a["args"].get("question", "")), problem, it[f"teacher_{r['lang']}"]


if __name__ == "__main__":
    rows = [{"model": r["model"], "step": "step1" if "level" in r else "step0", "lang": r["lang"],
             "need": r["need"], "level": r.get("level", "L0"), "key": r["key"], "turn": i,
             "question": q, "code": rule_code(q, p, r["need"], t)} for r, i, q, p, t in iter_asks()]
    json.dump(rows, open(ROOT / "judge" / "asks_coded.json", "w"), ensure_ascii=False)
    print(len(rows), Counter(r["code"] for r in rows))
    gold_path = ROOT / "judge" / "ask_sample_gold.json"
    if gold_path.exists():
        gold = json.load(open(gold_path))
        sample = json.load(open(ROOT / "judge" / "ask_sample.json"))
        coded = {(r["key"], r["turn"], r["model"]): r["code"] for r in rows}
        pairs = [(gold[s["sid"]], coded[(s["key"], s["turn"], s["model"])], s) for s in sample]
        acc = sum(g == c for g, c, _ in pairs) / len(pairs)
        print(f"rule vs Claude gold: {acc:.1%} agreement on {len(pairs)}")
        print("confusion (gold -> rule):", Counter((g, c) for g, c, _ in pairs if g != c).most_common(12))
        for g, c, s in pairs:
            if g != c and "--show" in sys.argv:
                print(f"  {s['sid']} gold={g} rule={c} | {s['question'][:120]}")
    if len(sys.argv) > 1 and sys.argv[1] == "--sample":
        import random
        rng = random.Random(7)
        strata = {}
        for r in rows:
            strata.setdefault((r["model"], r["lang"]), []).append(r)
        sample = []
        for key, rs in sorted(strata.items()):
            sample += rng.sample(rs, min(40, len(rs)))
        for i, s in enumerate(sample):
            s["sid"] = f"S{i:03d}"
        json.dump(sample, open(ROOT / "judge" / "ask_sample.json", "w"), ensure_ascii=False, indent=0)
        with open(ROOT / "judge" / "ask_sample.txt", "w") as f:
            for s in sample:
                f.write(f"{s['sid']} [{s['model'][:6]}|{s['lang']}|{s['need'][:4]}] rule={s['code']:6s} | "
                        f"{s['question'][:200]}\n")
        print("sample", len(sample))
