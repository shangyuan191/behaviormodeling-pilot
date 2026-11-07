"""CAPS「只回文字」回覆的編碼（2026-11-03）。

問題：CAPS 的求助率只算工具呼叫（raise_hand / ask_after_class）。Qwen3 關閉思考有約一半回合沒有呼叫工具、
只回一段文字，裡面常常其實說了「我會舉手問老師」或「請問總共有幾枝鉛筆？」，被當成沒求助。

做法：對每則只回文字的回覆，用關鍵字規則歸類（優先順序由上而下，先符合者勝）：
  tool_in_text  文字裡寫出工具名稱（格式錯誤的工具呼叫），依工具名稱再歸到 public/private/skip/answer
  private       說要下課／私下問老師
  public        說要舉手／在課堂上問老師
  undecided     問「該舉手還是下課問？」「Should I raise my hand?」但沒有決定（有求助意圖，管道不明）
  ask_teacher   說要問老師，沒說公開或私下
  skip          說要跳過
  request_info  直接向對話對象要缺少的資訊（「請問…？」「請告訴我…」），沒提老師
  answer        自己假設數字或給出答案
  state_missing 只陳述題目缺資訊，沒有向任何人要、也沒說要做什麼
  other         以上皆非
同時提到公開與私下的回覆標記 both=True，需人工確認方向。

輸出：results/caps_coded/<model>.jsonl（每則只回文字的回覆一列，含 code 與命中的關鍵字），
      以及 results/caps_coded/review_sample.csv（分層抽樣，供人工檢查）。
用法：~/miniforge3/bin/python3 -I code_caps_text.py
"""
import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "results"
MODELS = ["Qwen3-8B-FP8-nothink", "Qwen2.5-7B-Instruct", "Llama-3.1-8B-Instruct", "granite-3.3-8b-instruct"]

TOOLS = r"(raise_hand|ask_after_class|skip|submit_answer)"
CALL_RE = re.compile(r'"name"\s*:\s*"' + TOOLS + '"|\\b' + TOOLS + r'\s*\(')  # 真正的呼叫格式優先
TOOL_RE = re.compile(r"\b" + TOOLS + r"\b")
UNDECIDED_RE = re.compile(r"(還是|还是|或是|\bor\b)[^。？?\n]*(下課|课后|課後|私下|after class|privately|舉手|举手|raise)[^。\n]*[？?]"
                         r"|(舉手|举手|下課|课后|課後|私下)[^。\n]*(還是|还是)[^。\n]*[？?]"
                         r"|should i (raise|ask)[^.?]*\?|(應該|应该)(先)?(舉手|举手)?(問|问)老師?[^。]*嗎|(應該|应该)(先)?(问|問)老(师|師)吗")
TOOL_MAP = {"raise_hand": "public", "ask_after_class": "private", "skip": "skip", "submit_answer": "answer"}
RULES = [
    ("private", r"after class|after the class|privately|in private|下課|課後|课后|私下|單獨|单独"),
    ("public", r"raise (my|your|a|the)? ?hand|raising (my )?hand|in front of the (whole )?class|during class|in class"
               r"|舉手|举手|全班|課堂上|课堂上|當場|当场"),
    ("ask_teacher", r"ask (the|my) teacher|ask a teacher|teacher for (clarification|help|more)|with the teacher|consult (the|my) teacher"
                    r"|問老師|问老师|請教老師|请教老师|詢問老師|询问老师|向老師|向老师|找老師|找老师"),
    ("skip", r"\bskip\b|跳過|跳过|略過|略过|先不做|move on"),
    ("request_info", r"\?|？|please (provide|tell|let me know|specify|clarify)|could you|can you|請告訴|请告诉|請提供|请提供"
                     r"|請問|请问|請說明|请说明"),
    ("answer", r"answer is|assum|let'?s say|答案是|答案為|假設|假设|\\boxed"),
    ("state_missing", r"not enough|insufficient|missing|need (more|to know)|does not (provide|specify|give|mention)|doesn'?t (provide|specify|mention)"
                      r"|without (this|that|additional|more)|not possible|cannot determine|can'?t determine"
                      r"|不足|不夠|不够|缺少|需要更多|需要知道|沒有提供|没有提供|沒有給|没有给|無法|无法|不知道"),
]


def code(text):
    t = text.lower()
    m = CALL_RE.search(t) or TOOL_RE.search(t)
    if m:
        name = next(g for g in m.groups() if g)
        return "tool_in_text", TOOL_MAP[name], m.group(0)
    m = UNDECIDED_RE.search(t)
    if m:  # 問「該舉手還是下課問？」但沒有決定：有求助意圖，管道不明
        return "undecided", "undecided", m.group(0)[:30]
    for name, pat in RULES:
        m = re.search(pat, t)
        if m:
            return name, name, m.group(0)
    return "other", "other", ""


def main():
    out_dir = ROOT / "caps_coded"
    out_dir.mkdir(exist_ok=True)
    sample = []
    for model in MODELS:
        rows = [json.loads(l) for l in open(ROOT / "caps" / f"{model}.jsonl")]
        coded = []
        for r in rows:
            if r["first_action"] != "text":
                continue
            text = r["actions"][0]["text"]
            raw, final, hit = code(text)
            t = text.lower()
            both = bool(re.search(RULES[0][1], t)) and bool(re.search(RULES[1][1], t))
            coded.append({"key": r["key"], "model": model, "ptype": r["ptype"], "lang": r["lang"],
                          "persona": r["persona"], "rule": raw, "code": final, "hit": hit, "both": both, "text": text})
        with open(out_dir / f"{model}.jsonl", "w") as f:
            for c in coded:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"{model}: {len(coded)} 則只回文字", dict(Counter(c["code"] for c in coded).most_common()),
              f"tool_in_text={sum(c['rule'] == 'tool_in_text' for c in coded)} both={sum(c['both'] for c in coded)}")
        # 分層抽樣：每個 code 最多 6 則，加上所有 both
        rnd = random.Random(0)
        by = {}
        for c in coded:
            by.setdefault(c["code"], []).append(c)
        for k, v in by.items():
            sample += rnd.sample(v, min(6, len(v)))
        sample += [c for c in coded if c["both"] and c not in sample]
    with open(out_dir / "review_sample.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "key", "lang", "ptype", "code", "hit", "both", "human_code", "text"])
        for c in sample:
            w.writerow([c["model"], c["key"], c["lang"], c["ptype"], c["code"], c["hit"], c["both"], "", c["text"]])
    print(f"人工檢查樣本：{len(sample)} 則 → {out_dir / 'review_sample.csv'}")


if __name__ == "__main__":
    main()
