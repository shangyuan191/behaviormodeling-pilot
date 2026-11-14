"""11/13 補跑：低求助 persona × 只學過加減。
低求助 15 個 persona 來自 results/step1_extra/<model>-low-ability.jsonl；
L0 與中性對照沿用 results/step1/<model>-high.jsonl 裡 need=ability 的資料（提示詞完全相同）。
印出各層級的求助率（呼叫 ask_teacher）、答對率與跳過率（最後動作是 skip），分乘除題（應該問）、加減題（對照）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS = ["Llama-3.1-8B-Instruct", "Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct", "Qwen3-8B-FP8-nothink", "Qwen3-8B-FP8"]
LEVELS = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]


def load(p):
    return [json.loads(l) for l in p.open()] if p.exists() else []


def lvl(r):
    return {"none": "L0", "neutral": "neutral"}.get(r["direction"], r["level"])


for m in (sys.argv[1:] or MODELS):
    low = load(ROOT / "results" / "step1_extra" / f"{m}-low-ability.jsonl")
    if not low:
        continue
    ctrl = [r for r in load(ROOT / "results" / "step1" / f"{m}-high.jsonl")
            if r["need"] == "ability" and r["direction"] in ("none", "neutral")]
    rows = ctrl + low
    print(f"\n## {m}（低求助 {len(low)} 行＋對照 {len(ctrl)} 行）")
    print("| 題目 | 語言 | 指標 | " + " | ".join(LEVELS) + " |")
    print("|" + " --- |" * (3 + len(LEVELS)))
    for op, oplabel in (("muldiv", "乘除（應問）"), ("addsub", "加減（對照）")):
        for lang in ("en", "zh"):
            for key, klabel in (("asked", "求助率"), ("correct", "答對率"), ("skip", "跳過率")):
                cells = []
                for lv in LEVELS:
                    rs = [r for r in rows if r["op"] == op and r["lang"] == lang and lvl(r) == lv]
                    val = (lambda r: r["final_action"] == "skip") if key == "skip" else (lambda r: bool(r[key]))
                    cells.append(f"{100 * sum(map(val, rs)) / len(rs):.0f}%" if rs else "–")
                print(f"| {oplabel} | {lang} | {klabel} | " + " | ".join(cells) + " |")
