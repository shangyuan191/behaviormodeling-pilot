"""文字求助版（run_pilot.py --help-mode text）vs 工具版：各模型的求助率與跳過率（無 persona）。
文字版把「只回文字」一律記成 ask_teacher（_via=text），其中有些只是陳述或列算式，所以文字版的求助率是上限。
用法：python3 -I analyze_textask.py > results/textask_summary.txt
"""
import json
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
MODELS = [("Qwen3-8B-FP8", "Qwen3 開啟思考"), ("Qwen3-8B-FP8-nothink", "Qwen3 關閉思考"), ("Llama-3.1-8B-Instruct", "Llama-3.1"),
          ("Qwen2.5-7B-Instruct", "Qwen2.5"), ("granite-3.3-8b-instruct", "Granite-3.3")]
NEEDS = [("complete", None, "一般題"), ("ability", "muldiv", "只學加減・乘除"), ("ability", "addsub", "只學加減・加減"), ("missing", None, "缺條件題")]


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def pct(rows, f):
    return f"{sum(map(f, rows)) / len(rows):4.0%}" if rows else "   –"


print("# 文字求助版 vs 工具版（無 persona）\n")
print("求助率：工具版 → 文字版（文字版＝只回文字也算求助）；括號為文字版的跳過率\n")
for tag, name in MODELS:
    tool, text = load(RES / f"{tag}.jsonl"), load(RES / f"{tag}-textask.jsonl")
    if not text:
        print(f"## {name}：尚無文字版資料\n")
        continue
    print(f"## {name}（文字版 {len(text)} 回合）")
    for lang in ("en", "zh"):
        cells = []
        for need, op, lab in NEEDS:
            sel = lambda rs: [r for r in rs if r["lang"] == lang and r["need"] == need and (op is None or r["op"] == op)]
            a, b = sel(tool), sel(text)
            cells.append(f"{lab} {pct(a, lambda r: r['asked'])} → {pct(b, lambda r: r['asked'])}（跳過 {pct(b, lambda r: r['final_action'] == 'skip')}）")
        print(f"  {lang}: " + "；".join(cells))
    print()
