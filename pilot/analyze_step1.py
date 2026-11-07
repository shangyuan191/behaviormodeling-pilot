"""彙整 Step 1：各 persona 層級的求助率（依語言、題型分開），並畫出 TACT 階梯折線圖。

用法：~/miniforge3/envs/adl_hw3_py311/bin/python analyze_step1.py
輸出：results/step1/summary_<model>.csv、results/step1/ladder_<model>.png
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze import wilson

ROOT = Path(__file__).resolve().parent / "results" / "step1"
LEVELS = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
LEVEL_LABEL = {"L0": "無", "neutral": "中性", "0": "0", "T": "T", "TA": "T+A", "TAC": "T+A+C", "TACT": "T+A+C+T"}
# 圖中的三個面板：(方向, need, op)
PANELS = [("high", "ability", "muldiv", "高求助｜只學過加減・乘除題"),
          ("high", "complete", None, "高求助｜一般題"),
          ("low", "missing", None, "低求助｜缺條件題")]


def main():
    by_model = defaultdict(list)
    for f in sorted(ROOT.glob("*.jsonl")):
        for line in f.open():
            r = json.loads(line)
            r["direction_file"] = f.stem.rsplit("-", 1)[1]
            by_model[r["model"]].append(r)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = ["DejaVu Sans", "Droid Sans Fallback"]

    for model, rows in by_model.items():
        table = []
        fig, axes = plt.subplots(1, len(PANELS), figsize=(14, 4), sharey=True)
        for ax, (direction, need, op, title) in zip(axes, PANELS):
            for lang, color in (("en", "#3b82f6"), ("zh", "#ef4444")):
                ys, los, his = [], [], []
                for level in LEVELS:
                    rs = [r for r in rows if r["direction_file"] == direction and r["need"] == need
                          and r["lang"] == lang and r["level"] == level and (op is None or r["op"] == op)]
                    n, k = len(rs), sum(r["asked"] for r in rs)
                    lo, hi = wilson(k, n)
                    p = k / n if n else float("nan")
                    ys.append(p); los.append(max(p - lo, 0)); his.append(max(hi - p, 0))  # 浮點誤差可能產生 -0.0
                    table.append({"model": model, "direction": direction, "need": need, "op": op or "all",
                                  "lang": lang, "level": level, "n": n, "ask_rate": p, "ask_lo": lo, "ask_hi": hi,
                                  "correct_rate": sum(r["correct"] for r in rs) / n if n else float("nan"),
                                  "text_only_rate": sum(r["final_action"] == "text" for r in rs) / n if n else float("nan")})
                x = range(len(LEVELS))
                ax.errorbar(x, ys, yerr=[los, his], color=color, marker="o", capsize=3,
                            label="English" if lang == "en" else "繁中")
            ax.set_xticks(range(len(LEVELS)), [LEVEL_LABEL[l] for l in LEVELS], fontsize=8)
            ax.axvline(1.5, color="#ccc", lw=0.8)
            ax.set_ylim(0, 1.05)
            ax.set_title(title, fontsize=10)
        axes[0].set_ylabel("呼叫 ask_teacher 的比例")
        axes[0].legend(fontsize=8)
        fig.suptitle(f"{model}：persona 吻合要素數 vs 求助率", fontsize=11)
        fig.tight_layout()
        fig.savefig(ROOT / f"ladder_{model}.png", dpi=150)

        with (ROOT / f"summary_{model}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
            w.writeheader()
            w.writerows(table)
        for t in table:
            print(f"{t['direction']:4s} {t['need']:8s} {t['op']:6s} {t['lang']} {t['level']:7s} n={t['n']:4d} "
                  f"ask={t['ask_rate']:.2f} [{t['ask_lo']:.2f},{t['ask_hi']:.2f}] correct={t['correct_rate']:.2f} "
                  f"text={t['text_only_rate']:.2f}")


if __name__ == "__main__":
    main()
