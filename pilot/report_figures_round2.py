"""產生 pilot 報告（results/report/pilot_report_full.md；舊的分輪報告在 results/report/archive/）用的圖 4–8。

fig4_step0_models.png  Step 0：6 個模型在三種題型的求助率（無 persona，英／中）
fig5_ladders.png       Step 1：TACT 階梯（5 組設定；低求助×缺條件、高求助×只學過加減的乘除題）
fig6_say_do.png        說 vs 做：每個 persona 的迴避分數與實際求助率（低求助×缺條件），依層級上色
fig7_caps.png          CAPS：各類 persona 的公開占比（只回文字的回覆依 code_caps_text.py 的編碼併回）
fig8_third.png         第一人稱 vs 第三人稱：低求助階梯與能力外洩

用法：~/miniforge3/envs/adl_hw3_py311/bin/python report_figures_round2.py
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
OUT = RES / "report"
plt.rcParams["font.family"] = ["DejaVu Sans", "Droid Sans Fallback"]
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

LEVELS = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
LEVEL_LABEL = ["無", "中性", "0", "T", "T+A", "T+A+C", "T+A+C+T"]
BLUE, RED = "#2563eb", "#dc2626"
CONFIGS = [("Qwen3-8B-FP8-nothink", "Qwen3（不思考）", "#2563eb"), ("Qwen3-8B-FP8", "Qwen3（思考）", "#7c3aed"),
           ("Llama-3.1-8B-Instruct", "Llama-3.1", "#dc2626"), ("Qwen2.5-7B-Instruct", "Qwen2.5", "#059669"),
           ("granite-3.3-8b-instruct", "Granite-3.3", "#d97706")]
LANG = {"en": "English", "zh": "繁中"}


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def level_of(r):
    if r["persona"] == "L0":
        return "L0"
    if r["persona"].startswith("N"):
        return "neutral"
    return r.get("level") or r["persona"].split("-")[1]


def panel(rows, direction, need, op=None):
    return [r for r in rows if r["need"] == need and (op is None or r["op"] == op)
            and (r["persona"] == "L0" or r["persona"].startswith("N") or r["persona"][0] == direction[0].upper())]


def wilson_half(k, n, z=1.96):
    if n == 0:
        return 0
    p = k / n
    d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


def ladder_points(rows, lang, key="asked"):
    ys, es = [], []
    for lv in LEVELS:
        rs = [r for r in rows if r["lang"] == lang and level_of(r) == lv]
        k = sum(bool(r[key]) for r in rs)
        ys.append(k / len(rs) if rs else float("nan"))
        es.append(wilson_half(k, len(rs)))
    return ys, es


# ---------------------------------------------------------------- fig4

def fig4():
    models = [("gemini-3.5-flash-lite", "Gemini\nFlash Lite"), ("Qwen3-8B-FP8", "Qwen3\n（思考）"),
              ("Qwen3-8B-FP8-nothink", "Qwen3\n（不思考）"), ("Llama-3.1-8B-Instruct", "Llama-3.1"),
              ("Qwen2.5-7B-Instruct", "Qwen2.5"), ("granite-3.3-8b-instruct", "Granite-3.3")]
    needs = [("complete", "一般題（不需要問）"), ("ability", "只學過加減的乘除題（應該問）"), ("missing", "缺條件題（應該問）")]
    data = {m: load(RES / f"{m}.jsonl") for m, _ in models}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=True)
    for ax, (need, title) in zip(axes, needs):
        for j, (lang, color) in enumerate((("en", BLUE), ("zh", RED))):
            for i, (m, _) in enumerate(models):
                rs = [r for r in data[m] if r["need"] == need and r["lang"] == lang
                      and (need != "ability" or r["op"] == "muldiv")]
                if not rs:
                    continue
                y = sum(r["asked"] for r in rs) / len(rs)
                x = i + (j - 0.5) * 0.38
                ax.bar(x, y, width=0.36, color=color, alpha=0.85, label=LANG[lang] if i == 0 else None)
                ax.text(x, y + 0.02, f"{y:.0%}", ha="center", fontsize=7)
        ax.set_xticks(range(len(models)), [l for _, l in models], fontsize=8)
        ax.set_title(title, fontsize=10.5)
        ax.set_ylim(0, 1.12)
    axes[0].set_ylabel("先問老師的比例")
    axes[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle("Step 0：沒有 persona 時，各模型原本會不會問老師", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig4_step0_models.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- fig5

def fig5():
    panels = [("low", "missing", None, "低求助 persona × 缺條件題（預期越來越少問）"),
              ("high", "ability", "muldiv", "高求助 persona × 只學過加減的乘除題（預期越來越常問）")]
    fig, axes = plt.subplots(2, 2, figsize=(13, 7.5), sharey=True)
    for row, (direction, need, op, title) in enumerate(panels):
        for col, lang in enumerate(("en", "zh")):
            ax = axes[row][col]
            for tag, name, color in CONFIGS:
                rows = panel(load(RES / "step1" / f"{tag}-{direction}.jsonl"), direction, need, op)
                if not rows:
                    continue
                ys, es = ladder_points(rows, lang)
                ax.errorbar(range(len(LEVELS)), ys, yerr=es, color=color, marker="o", ms=4, lw=1.6,
                            capsize=2, label=name, alpha=0.9)
            ax.axvspan(3.5, 6.5, color="#64748b", alpha=0.07)
            ax.set_xticks(range(len(LEVELS)), LEVEL_LABEL, fontsize=8.5)
            ax.set_ylim(-0.03, 1.05)
            ax.set_title(f"{title}｜{LANG[lang]}", fontsize=9.5)
            if col == 0:
                ax.set_ylabel("先問老師的比例")
    axes[0][0].legend(fontsize=8, frameon=False, loc="lower left")
    fig.text(0.5, 0.005, "灰底＝persona 寫到「行動」（T+A 以上）。誤差線為 Wilson 95% 信賴區間。", ha="center", fontsize=8.5)
    fig.suptitle("Step 1：TACT persona 階梯（第一人稱）", fontsize=11.5)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(OUT / "fig5_ladders.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- fig6

def fig6():
    cfgs = CONFIGS[:4]
    groups = [({"L0", "neutral"}, "無／中性", "#94a3b8", "s"), ({"0", "T"}, "0、T（沒寫行動）", "#f59e0b", "o"),
              ({"TA", "TAC", "TACT"}, "T+A 以上（寫到行動）", "#2563eb", "^")]
    fig, axes = plt.subplots(2, 4, figsize=(15, 7), sharex=True, sharey=True)
    for c, (tag, name, _) in enumerate(cfgs):
        sv = load(RES / "survey" / f"{tag}.jsonl")
        sc = defaultdict(lambda: defaultdict(list))
        for r in sv:
            if r["score"] is not None:
                sc[(r["persona"], r["lang"])][r["scale"]].append(r["score"])
        mean = lambda v: sum(v) / len(v) if v else float("nan")
        avoid = {k: mean(v["avoid"]) - mean(v["adaptive"]) for k, v in sc.items()}
        rows = panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing")
        for rr, lang in enumerate(("en", "zh")):
            ax = axes[rr][c]
            by = defaultdict(list)
            for r in rows:
                if r["lang"] == lang:
                    by[r["persona"]].append(r["asked"])
            for lvset, label, color, mk in groups:
                xs, ys = [], []
                for pid, a in by.items():
                    lv = level_of({"persona": pid, "level": None if "-" not in pid else pid.split("-")[1]})
                    if lv in lvset and (pid, lang) in avoid:
                        xs.append(avoid[(pid, lang)])
                        ys.append(sum(a) / len(a))
                ax.scatter(xs, ys, color=color, marker=mk, s=38, alpha=0.85, label=label, edgecolor="white", lw=0.5)
            ax.set_xlim(-6.3, 6.3)
            ax.set_ylim(-0.05, 1.05)
            ax.axvline(0, color="#cbd5e1", lw=0.8)
            ax.set_title(f"{name}｜{LANG[lang]}", fontsize=9.5)
            if rr == 1:
                ax.set_xlabel("量表迴避分數（AV−AD；越右越說自己迴避）", fontsize=8.5)
            if c == 0:
                ax.set_ylabel("缺條件題的實際求助率")
    h, l = axes[0][0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 0.955), ncol=3, fontsize=8.5, frameon=False)
    fig.suptitle("說 vs 做：每個點是一個低求助 persona（缺條件題）。橘點往右移卻仍在上方＝「說自己迴避，但照樣問」", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "fig6_say_do.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- fig7

def caps_channels(tag):
    rows = load(RES / "caps" / f"{tag}.jsonl")
    codes = {c["key"]: c["code"] for c in load(RES / "caps_coded" / f"{tag}.jsonl")}

    def chan(r):
        if r["first_action"] != "text":
            return "public" if r["public"] and not r["private"] else "private" if r["private"] else r["first_action"]
        return codes.get(r["key"], "other")
    return [dict(r, _c=chan(r)) for r in rows]


def fig7():
    models = [("Llama-3.1-8B-Instruct", "Llama-3.1"), ("Qwen2.5-7B-Instruct", "Qwen2.5"),
              ("Qwen3-8B-FP8-nothink", "Qwen3（不思考）"), ("Qwen3-8B-FP8", "Qwen3（思考）"),
              ("granite-3.3-8b-instruct", "Granite-3.3")]
    ptypes = [("none", "無"), ("neutral", "中性"), ("trait", "特質\n（害羞）"), ("process", "歷程\n（怕被看扁）"),
              ("ifthen", "if–then\n（明說私下）"), ("reverse", "反向\n（對照）")]
    fig, axes = plt.subplots(1, 5, figsize=(19, 4.2), sharey=True)
    for ax, (tag, name) in zip(axes, models):
        rows = caps_channels(tag)
        for j, (lang, color) in enumerate((("en", BLUE), ("zh", RED))):
            for i, (pt, _) in enumerate(ptypes):
                rs = [r for r in rows if r["ptype"] == pt and r["lang"] == lang and r["_c"] in ("public", "private")]
                if not rs:
                    continue
                k = sum(r["_c"] == "public" for r in rs)
                y = k / len(rs)
                x = i + (j - 0.5) * 0.38
                ax.bar(x, y, width=0.36, color=color, alpha=0.85, label=LANG[lang] if i == 0 else None)
                ax.errorbar(x, y, yerr=wilson_half(k, len(rs)), color="#334155", lw=0.8, capsize=1.5)
        ax.axvspan(2.5, 4.5, color="#64748b", alpha=0.07)
        ax.set_xticks(range(len(ptypes)), [l for _, l in ptypes], fontsize=7.5)
        ax.set_ylim(0, 1.1)
        ax.set_title(name, fontsize=10.5)
    axes[0].set_ylabel("公開占比（舉手 ÷ 有求助）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, 0.93), ncol=2, fontsize=8.5, frameon=False)
    fig.suptitle("CAPS：有求助時選「全班面前舉手」的比例（灰底＝H8 的關鍵比較；只回文字的回覆依內容編碼）", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT / "fig7_caps.png", dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------- fig8

def fig8():
    models = [("Qwen3-8B-FP8-nothink", "Qwen3（不思考）"), ("Qwen3-8B-FP8", "Qwen3（思考）"), ("Qwen2.5-7B-Instruct", "Qwen2.5"),
              ("Llama-3.1-8B-Instruct", "Llama-3.1"), ("granite-3.3-8b-instruct", "Granite-3.3")]
    rowspec = [("low", "missing", None, "asked", "低求助×缺條件：求助率"),
               ("high", "ability", "muldiv", "correct", "高求助×只學過加減的乘除題：答對率（能力外洩）")]
    fig, axes = plt.subplots(2, 5, figsize=(18.5, 7), sharey=True)
    for r_i, (direction, need, op, key, ylabel) in enumerate(rowspec):
        for c, (tag, name) in enumerate(models):
            ax = axes[r_i][c]
            for persp, sub, suf, ls in (("第一人稱", "step1", "", "-"), ("第三人稱", "step1_third", "-third", "--")):
                rows = panel(load(RES / sub / f"{tag}-{direction}{suf}.jsonl"), direction, need, op)
                for lang, color in (("en", BLUE), ("zh", RED)):
                    ys, _ = ladder_points(rows, lang, key)
                    ax.plot(range(len(LEVELS)), ys, ls=ls, color=color, marker="o" if ls == "-" else "x", ms=4,
                            lw=1.5, alpha=0.9, label=f"{LANG[lang]}・{persp}")
            ax.set_xticks(range(len(LEVELS)), LEVEL_LABEL, fontsize=7.5)
            ax.set_ylim(-0.03, 1.05)
            ax.set_title(name if r_i == 0 else "", fontsize=10.5)
            if c == 0:
                ax.set_ylabel(ylabel, fontsize=9)
    axes[0][0].legend(fontsize=7.5, frameon=False, loc="lower left")
    fig.suptitle("第一人稱（實線）vs 第三人稱（虛線）：上排看 persona 效果多早出現，下排看能力外洩", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig8_third.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    for f in (fig4, fig5, fig6, fig7, fig8):
        f()
        print("ok", f.__name__)
