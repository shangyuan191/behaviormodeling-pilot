"""產生 pilot 報告用的三張圖（results/report/）。

fig1_step0.png  Step 0：各模型在三種題型的求助率（無 persona，英／中）
fig2_ladder.png Step 1：TACT 階梯（低求助：缺條件題的有效求助率；高求助：只學過加減的乘除題）
fig3_types.png  求助類型：工具性 vs 執行性（Step 0 + Step 1 高求助，依模型與語言）

用法：~/miniforge3/envs/adl_hw3_py311/bin/python report_figures.py
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "report"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams["font.family"] = ["DejaVu Sans", "Droid Sans Fallback"]
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

MODELS = [("Qwen3-8B-FP8-nothink", "Qwen3-8B（不思考）"), ("Qwen3-8B-FP8", "Qwen3-8B（思考）"),
          ("Llama-3.1-8B-Instruct", "Llama-3.1-8B"), ("gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite")]
NEEDS = [("complete", "一般題"), ("ability", "只學過加減\n（乘除題）"), ("missing", "缺條件題")]
LEVELS = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
LEVEL_LABEL = ["無", "中性", "0", "T", "T+A", "T+A+C", "T+A+C+T"]
BLUE, RED = "#2563eb", "#dc2626"


def load_step0():
    rows = []
    for f in (ROOT / "results").glob("*.jsonl"):
        if "textask" not in f.name:
            rows += [json.loads(l) for l in f.open()]
    return rows


def fig1():
    rows = load_step0()
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, (need, nlabel) in zip(axes, NEEDS):
        for j, (lang, color) in enumerate((("en", BLUE), ("zh", RED))):
            xs, ys, ns = [], [], []
            for i, (m, _) in enumerate(MODELS):
                rs = [r for r in rows if r["model"] == m and r["need"] == need and r["lang"] == lang
                      and (need != "ability" or r["op"] == "muldiv")]
                if not rs:
                    continue
                xs.append(i + (j - 0.5) * 0.36)
                ys.append(sum(r["asked"] for r in rs) / len(rs))
                ns.append(len(rs))
            bars = ax.bar(xs, ys, width=0.34, color=color, alpha=0.85, label="English" if lang == "en" else "繁中")
            for x, y, n in zip(xs, ys, ns):
                ax.text(x, y + 0.02, f"{y:.0%}", ha="center", fontsize=7.5)
        ax.set_xticks(range(len(MODELS)), [lbl for _, lbl in MODELS], fontsize=7.5, rotation=15)
        ax.set_title(nlabel.replace("\n", ""), fontsize=11)
        ax.set_ylim(0, 1.1)
    axes[0].set_ylabel("呼叫 ask_teacher 的比例")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("Step 0：沒有 persona 時，模型會不會問老師（Gemini 每格約 20–30 題，其餘 60 題）", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig1_step0.png", dpi=160)


def fig2():
    eff = list(csv.DictReader(open(ROOT / "judge" / "effective_help.csv")))
    step1 = defaultdict(list)
    for f in (ROOT / "results" / "step1").glob("*.jsonl"):
        for l in f.open():
            r = json.loads(l)
            step1[(r["model"], r["lang"], r["level"], r["need"], r["op"])].append(r["asked"])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), sharey=True)
    styles = {("Qwen3-8B-FP8-nothink", "en"): (BLUE, "-", "Qwen 英"), ("Qwen3-8B-FP8-nothink", "zh"): (RED, "-", "Qwen 中"),
              ("Llama-3.1-8B-Instruct", "en"): (BLUE, "--", "Llama 英"), ("Llama-3.1-8B-Instruct", "zh"): (RED, "--", "Llama 中")}
    for (model, lang), (color, ls, label) in styles.items():
        ys = [float(next(e for e in eff if (e["step"], e["model"], e["need"], e["lang"], e["level"]) ==
                         ("step1", model, "missing", lang, lv))["effective_help"]) for lv in LEVELS]
        axes[0].plot(range(7), ys, color=color, ls=ls, marker="o", label=label)
        ys2 = [sum(v) / len(v) for v in (step1[(model, lang, lv, "ability", "muldiv")] for lv in LEVELS)]
        axes[1].plot(range(7), ys2, color=color, ls=ls, marker="o", label=label)
    axes[0].set_title("低求助 persona × 缺條件題（有效求助率：工具＋文字）", fontsize=11)
    axes[1].set_title("高求助 persona × 只學過加減的乘除題（呼叫 ask_teacher）", fontsize=11)
    for ax in axes:
        ax.set_xticks(range(7), LEVEL_LABEL, fontsize=8.5)
        ax.axvline(1.5, color="#bbb", lw=0.8)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("persona 與行為吻合的要素（左兩點為對照組）", fontsize=9)
    axes[0].set_ylabel("求助率")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("Step 1：寫到「行動」（A）之後，persona 才控制得了求助行為", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "fig2_ladder.png", dpi=160)


def fig3():
    asks = json.load(open(ROOT / "judge" / "asks_coded.json"))
    groups = [("Qwen3-8B-FP8-nothink", "Qwen（不思考）"), ("Llama-3.1-8B-Instruct", "Llama"), ("gemini-3.5-flash-lite", "Gemini")]
    cats = [("INFO", "問缺少的資訊", "#93c5fd"), ("METHOD", "問解法", "#3b82f6"), ("VERIFY", "確認答案", "#1d4ed8"),
            ("EXEC", "轉貼題目／要答案", "#dc2626"), ("OTHER", "其他", "#d1d5db")]
    labels, data = [], []
    for m, mlabel in groups:
        for lang in ("en", "zh"):
            c = Counter(a["code"] for a in asks if a["model"] == m and a["lang"] == lang
                        and (a["step"] == "step0" or a["need"] != "missing"))
            n = sum(c.values())
            labels.append(f"{mlabel}\n{'英' if lang == 'en' else '中'}（n={n}）")
            data.append([c[k] / n for k, _, _ in cats])
    fig, ax = plt.subplots(figsize=(11, 4))
    left = [0] * len(labels)
    for k, (code, clabel, color) in enumerate(cats):
        vals = [d[k] for d in data]
        ax.barh(labels, vals, left=left, color=color, label=clabel)
        for i, v in enumerate(vals):
            if v >= 0.08:
                ax.text(left[i] + v / 2, i, f"{v:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if code in ("METHOD", "VERIFY", "EXEC") else "black")
        left = [l + v for l, v in zip(left, vals)]
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("所有 ask_teacher 呼叫中的比例（Step 0 + Step 1 高求助）")
    ax.legend(ncol=5, fontsize=8, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
    fig.suptitle("求助類型：藍色為工具性求助，紅色為執行性求助", fontsize=12, y=1.08)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_types.png", dpi=160, bbox_inches="tight")


if __name__ == "__main__":
    fig1(); fig2(); fig3()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
