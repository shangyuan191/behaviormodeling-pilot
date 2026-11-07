"""彙整 results/*.jsonl：各條件的求助率、首步求助率、跳過率、答對率，並畫圖。

用法：~/miniforge3/envs/adl_hw3_py311/bin/python analyze.py   # 需要 matplotlib；讀取 results/ 下所有模型
輸出：results/summary.csv、results/ask_rate.png
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NEEDS = ["complete", "missing", "ability"]
NEED_LABEL = {"complete": "一般題", "missing": "缺條件", "ability": "只學過加減"}


def wilson(k, n, z=1.96):
    """二項比例的 95% Wilson 信賴區間。"""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def load():
    rows = []
    for f in sorted((ROOT / "results").glob("*.jsonl")):
        rows += [json.loads(l) for l in f.open()]
    return rows


def summarize(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["model"], r["lang"], r["op"], r["need"])].append(r)
    table = []
    for (model, lang, op, need), rs in sorted(groups.items()):
        n = len(rs)
        asked = sum(r["asked"] for r in rs)
        lo, hi = wilson(asked, n)
        table.append({
            "model": model, "lang": lang, "op": op, "need": need, "n": n,
            "ask_rate": asked / n, "ask_lo": lo, "ask_hi": hi,
            "first_ask_rate": sum(r["first_action"] == "ask_teacher" for r in rs) / n,
            "skip_rate": sum(r["final_action"] == "skip" for r in rs) / n,
            "text_only_rate": sum(r["final_action"] == "text" for r in rs) / n,
            "correct_rate": sum(r["correct"] for r in rs) / n,
        })
    return table


def plot(table, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["DejaVu Sans", "Droid Sans Fallback"]  # 伺服器上唯一的中文字型

    models = sorted({t["model"] for t in table})
    fig, axes = plt.subplots(len(models), 2, figsize=(10, 3.2 * len(models)), squeeze=False, sharey=True)
    colors = {"complete": "#9aa5b1", "missing": "#3b82f6", "ability": "#f59e0b"}
    for i, model in enumerate(models):
        for j, op in enumerate(["addsub", "muldiv"]):
            ax = axes[i][j]
            for k, need in enumerate(NEEDS):
                for m, lang in enumerate(["en", "zh"]):
                    t = next((t for t in table if (t["model"], t["op"], t["need"], t["lang"]) == (model, op, need, lang)), None)
                    if not t:
                        continue
                    x = m * 4 + k
                    ax.bar(x, t["ask_rate"], color=colors[need], label=NEED_LABEL[need] if m == 0 else None)
                    ax.errorbar(x, t["ask_rate"], yerr=[[t["ask_rate"] - t["ask_lo"]], [t["ask_hi"] - t["ask_rate"]]],
                                color="#333", capsize=3, lw=1)
            ax.set_xticks([1, 5], ["English", "繁中"])
            ax.set_ylim(0, 1.05)
            ax.set_title(f"{model}｜{'加減題' if op == 'addsub' else '乘除題'}", fontsize=10)
            if j == 0:
                ax.set_ylabel("呼叫 ask_teacher 的比例")
    axes[0][1].legend(fontsize=8, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main():
    rows = load()
    table = summarize(rows)
    out = ROOT / "results" / "summary.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    for t in table:
        print(f"{t['model']:28s} {t['lang']} {t['op']:6s} {t['need']:8s} n={t['n']:3d} "
              f"ask={t['ask_rate']:.2f} [{t['ask_lo']:.2f},{t['ask_hi']:.2f}] first_ask={t['first_ask_rate']:.2f} "
              f"skip={t['skip_rate']:.2f} text={t['text_only_rate']:.2f} correct={t['correct_rate']:.2f}")
    plot(table, ROOT / "results" / "ask_rate.png")
    print("wrote", out, "and ask_rate.png")


if __name__ == "__main__":
    main()
