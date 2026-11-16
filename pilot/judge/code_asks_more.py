"""2026-11-16：把求助類型編碼補到所有開源模型（Qwen2.5、Granite、Qwen3 開啟思考的全部問句）。

規則與 code_asks.py 完全相同（直接 import rule_code、iter_asks），只是：
- 輸出到 judge/asks_coded_all.json，不覆寫原本的 asks_coded.json（報告既有數字由它算出）；
- 排除已移除的 Breeze2；
- --sample：從「規則沒驗證過的模型」（Qwen2.5、Granite、Qwen3 開啟思考）每個模型 × 語言抽 14 筆，
  存成 ask_sample_new.json／.txt，供 Claude 判定後計算一致率（judge/ask_sample_new_gold.json）。

用法：python judge/code_asks_more.py [--sample]
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import glob  # noqa: E402

from code_asks import ROOT, rule_code  # noqa: E402


def iter_asks():
    """同 code_asks.iter_asks，但容許 Granite 早期把工具參數寫成字串（整段當成問句）。"""
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
                    args = a["args"]
                    q = args.get("question", "") if isinstance(args, dict) else args
                    yield r, i, str(q), problem, it[f"teacher_{r['lang']}"]

HERE = Path(__file__).resolve().parent
NEW = ("Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct", "Qwen3-8B-FP8")

rows = [{"model": r["model"], "step": "step1" if "level" in r else "step0", "lang": r["lang"],
         "need": r["need"], "level": r.get("level", "L0"), "key": r["key"], "turn": i,
         "question": q, "code": rule_code(q, p, r["need"], t)}
        for r, i, q, p, t in iter_asks() if "Breeze" not in r["model"]]
json.dump(rows, open(HERE / "asks_coded_all.json", "w"), ensure_ascii=False)
print(len(rows), "asks")
for m, n in sorted(Counter(r["model"] for r in rows).items()):
    print(f"  {m}: {n}  {dict(Counter(r['code'] for r in rows if r['model'] == m))}")

if "--sample" in sys.argv:
    rng = random.Random(16)
    sample = []
    for m in NEW:
        for lang in ("en", "zh"):
            pool = [r for r in rows if r["model"] == m and r["lang"] == lang]
            sample += rng.sample(pool, min(14, len(pool)))
    for i, s in enumerate(sample):
        s["sid"] = f"N{i:03d}"
    json.dump(sample, open(HERE / "ask_sample_new.json", "w"), ensure_ascii=False, indent=0)
    with open(HERE / "ask_sample_new.txt", "w") as f:
        for s in sample:
            f.write(f"{s['sid']} [{s['model'][:8]}|{s['lang']}|{s['need'][:4]}] | {s['question'][:300]}\n")
    print("sample", len(sample))

gold_p = HERE / "ask_sample_new_gold.json"
if gold_p.exists():
    gold = json.load(open(gold_p))
    sample = json.load(open(HERE / "ask_sample_new.json"))
    pairs = [(gold[s["sid"]], s["code"], s) for s in sample]
    agree = sum(g == c for g, c, _ in pairs)
    cats = sorted({g for g, _, _ in pairs} | {c for _, c, _ in pairs})
    n = len(pairs)
    po = agree / n
    pe = sum((sum(g == k for g, _, _ in pairs) / n) * (sum(c == k for _, c, _ in pairs) / n) for k in cats)
    print(f"rule vs Claude gold（新模型）: {po:.1%} agreement, kappa = {(po - pe) / (1 - pe):.2f}, n = {n}")
    for m in NEW:
        sub = [(g, c) for g, c, s in pairs if s["model"] == m]
        print(f"  {m}: {sum(g == c for g, c in sub)}/{len(sub)}")
    print("disagreements:", Counter((g, c) for g, c, _ in pairs if g != c).most_common())
