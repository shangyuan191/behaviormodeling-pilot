"""11/4 工具名稱穩健性檢查＋Llama L0 補樣本的分析（只用標準函式庫，佇列跑完會自動執行）。

1. 低求助階梯（缺條件題、第一人稱）：ask_teacher（原資料 results/step1/）vs ask_for_help vs raise_hand（中性說明）
   各層級求助率、Spearman ρ（層級序號 vs 15 個 persona 的求助率）與 persona 層次置換檢定（20,000 次）。
2. Llama 高求助「只學過加減」乘除題：L0（無 persona）原本 3 次 + 補的 6 次，對照中性 persona。
輸出到 stdout（佇列導到 results/toolname_summary.txt）。
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "results"
LEVELS = ["0", "T", "TA", "TAC", "TACT"]
COLS = ["L0", "neutral"] + LEVELS
TOOLS = [("ask_teacher", "ask_teacher（原版）"), ("ask_for_help", "ask_for_help（不提老師）"),
         ("raise_hand_neutral", "raise_hand（中性說明）")]
MODELS = [("Qwen3-8B-FP8-nothink", "Qwen3 關閉思考"), ("Llama-3.1-8B-Instruct", "Llama-3.1")]


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def col_of(r):
    return "L0" if r["level"] == "L0" else "neutral" if r["direction"] == "neutral" else r["level"]


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    out = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return out


def spearman(x, y):
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx) ** 0.5
    syy = sum((b - my) ** 2 for b in ry) ** 0.5
    return sxy / (sxx * syy) if sxx and syy else 0.0


def trend(rows, lang, n_perm=20000):
    by = {}
    for r in rows:
        if r["lang"] == lang and r["level"] in LEVELS:
            by.setdefault(r["persona"], [LEVELS.index(r["level"]), []])[1].append(r["asked"])
    lv = [v[0] for v in by.values()]
    rt = [sum(v[1]) / len(v[1]) for v in by.values()]
    if len(lv) < 5:
        return None
    rho = spearman(lv, rt)
    rng = random.Random(0)
    hits = 0
    for _ in range(n_perm):
        sh = lv[:]
        rng.shuffle(sh)
        hits += abs(spearman(sh, rt)) >= abs(rho) - 1e-12
    return rho, (hits + 1) / (n_perm + 1), len(lv)


def rate(rs, key="asked"):
    return f"{sum(r[key] for r in rs) / len(rs):4.0%}（{len(rs):3d}）" if rs else "   —     "


def main():
    print("# 工具名稱穩健性檢查（低求助階梯 × 缺條件題，第一人稱）\n")
    print("數字＝至少呼叫一次求助工具的比例（括號為回合數）。ρ＝層級 0→TACT 與 persona 求助率的 Spearman 相關；")
    print("p＝persona 層次置換檢定（雙尾，20,000 次，未做多重比較校正）。\n")
    for tag, name in MODELS:
        print(f"## {name}")
        print(f"{'工具':24s} 語言 | " + " | ".join(f"{c:^10s}" for c in COLS) + " |   ρ    |   p    | 第一步沒呼叫工具")
        for tool, tname in TOOLS:
            p = ROOT / "step1" / f"{tag}-low.jsonl" if tool == "ask_teacher" else ROOT / "step1_toolname" / f"{tag}-low-{tool}.jsonl"
            rows = [r for r in load(p) if r["need"] == "missing"]
            if not rows:
                print(f"{tname:24s} （沒有資料：{p.name}）")
                continue
            for lang in ("en", "zh"):
                rl = [r for r in rows if r["lang"] == lang]
                cells = [rate([r for r in rl if col_of(r) == c]) for c in COLS]
                t = trend(rows, lang)
                ts = f"{t[0]:+.2f}  | {t[1]:.4f}" if t else "  —    |   —   "
                text = sum(r["first_action"] == "text" for r in rl) / len(rl)
                print(f"{tname:24s} {lang}   | " + " | ".join(cells) + f" | {ts} | {text:4.0%}")
        print()

    print("# Llama：高求助「只學過加減」乘除題的 L0 補樣本\n")
    main_rows = load(ROOT / "step1" / "Llama-3.1-8B-Instruct-high.jsonl")
    extra = load(ROOT / "step1_extra" / "Llama-3.1-8B-Instruct-high-L0extra.jsonl")
    sel = lambda rs, lang, c: [r for r in rs if r["need"] == "ability" and r["op"] == "muldiv"
                               and r["lang"] == lang and col_of(r) == c]
    print("語言 | L0 原本（rep 0–2） | L0 補的（rep 3–8） | L0 合計 | 中性 persona | 加減題 L0 合計（對照）")
    for lang in ("en", "zh"):
        a, b = sel(main_rows, lang, "L0"), sel(extra, lang, "L0")
        addsub = [r for r in main_rows + extra if r["need"] == "ability" and r["op"] != "muldiv"
                  and r["lang"] == lang and col_of(r) == "L0"]
        print(f"{lang}   | {rate(a)} | {rate(b)} | {rate(a + b)} | {rate(sel(main_rows, lang, 'neutral'))} | {rate(addsub)}")
    print("\n同一批補樣本也含一般題（complete）：")
    for lang in ("en", "zh"):
        a = [r for r in main_rows + extra if r["need"] == "complete" and r["lang"] == lang and col_of(r) == "L0"]
        n = [r for r in main_rows if r["need"] == "complete" and r["lang"] == lang and col_of(r) == "neutral"]
        print(f"{lang}   | 一般題 L0 合計 {rate(a)} | 中性 {rate(n)}")


if __name__ == "__main__":
    main()
