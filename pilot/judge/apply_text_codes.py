"""把只回文字的分類結果對回每個 episode，計算「有效求助率」。

有效求助 = 呼叫 ask_teacher，或最後一則文字被分類為
  R（明確請求）、I（說要去問但沒行動）、M（想呼叫 ask_teacher 但格式壞掉）。
輸出 judge/effective_help_<step>.csv，並印出 Step 1 低求助的對照表。
"""
import csv
import glob
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELP_CODES = {"R", "I", "M"}


def load_codes():
    units = json.load(open(ROOT / "judge" / "text_only_units.json"))
    return {u["text"]: u["code"] for u in units}


def classify(r, codes):
    """回傳這個 episode 的結果類別。"""
    if r["asked"]:
        return "tool_ask"
    if r["final_action"] == "text":
        return "text_" + codes.get(r["actions"][-1]["text"].strip(), "?")
    return r["final_action"]  # submit_answer / skip


def main():
    codes = load_codes()
    rows = []
    for f in glob.glob(str(ROOT / "results" / "*.jsonl")) + glob.glob(str(ROOT / "results" / "step1" / "*.jsonl")):
        if "textask" in f:
            continue
        step = "step1" if "/step1/" in f else "step0"
        for line in open(f):
            r = json.loads(line)
            r["step"] = step
            r["outcome"] = classify(r, codes)
            rows.append(r)

    groups = defaultdict(list)
    for r in rows:
        level = r.get("level", "L0")
        groups[(r["step"], r["model"], r["need"], r.get("op") if r["need"] == "ability" else "all", r["lang"], level)].append(r)

    out = []
    for key, rs in sorted(groups.items()):
        c = Counter(r["outcome"] for r in rs)
        n = len(rs)
        tool = c["tool_ask"] / n
        text_help = sum(c[f"text_{k}"] for k in HELP_CODES) / n
        out.append({"step": key[0], "model": key[1], "need": key[2], "op": key[3], "lang": key[4], "level": key[5],
                    "n": n, "tool_ask": round(tool, 3), "text_help": round(text_help, 3),
                    "effective_help": round(tool + text_help, 3),
                    "text_R": c["text_R"] / n, "text_I": c["text_I"] / n, "text_M": c["text_M"] / n,
                    "text_S": c["text_S"] / n, "text_P": c["text_P"] / n,
                    "skip": c["skip"] / n, "submit_no_ask": c["submit_answer"] / n})
    with open(ROOT / "judge" / "effective_help.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    levels = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
    print("Step 1 低求助（缺條件題）：工具求助 / 文字求助 / 有效求助 / 跳過 / 硬答")
    for model in sorted({o["model"] for o in out if o["step"] == "step1"}):
        for lang in ("en", "zh"):
            for level in levels:
                o = next(o for o in out if (o["step"], o["model"], o["need"], o["lang"], o["level"]) ==
                         ("step1", model, "missing", lang, level))
                print(f"{model:24s} {lang} {level:7s} tool={o['tool_ask']:.2f} text={o['text_help']:.2f} "
                      f"eff={o['effective_help']:.2f} skip={o['skip']:.2f} submit={o['submit_no_ask']:.2f} "
                      f"[R={o['text_R']:.2f} I={o['text_I']:.2f} M={o['text_M']:.2f} S={o['text_S']:.2f}]")
    print("\nStep 0 缺條件題（無 persona）")
    for o in out:
        if o["step"] == "step0" and o["need"] == "missing":
            print(f"{o['model']:24s} {o['lang']} tool={o['tool_ask']:.2f} text={o['text_help']:.2f} "
                  f"eff={o['effective_help']:.2f} [R={o['text_R']:.2f} I={o['text_I']:.2f} S={o['text_S']:.2f}]")


if __name__ == "__main__":
    main()
