"""投影片用的數據圖（白底黑字、字大、一張圖只講一件事）。輸出到 results/report/slides/。

和 report_figures*.py 用同一份資料與同一套計算（直接 import 它們的函式），只是版面改成投影片用。
用法：~/miniforge3/envs/adl_hw3_py311/bin/python slides_figures.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import report_figures_round2 as rf

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
OUT = RES / "report" / "slides"
OUT.mkdir(parents=True, exist_ok=True)

INK, GRAY, LIGHT, ACCENT, ACCENT2 = "#111111", "#8a8a8a", "#d9d9d9", "#1f4e9c", "#c0392b"
plt.rcParams.update({
    "font.family": ["DejaVu Sans", "Droid Sans Fallback"], "font.size": 17,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 1.2,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "legend.frameon": False, "legend.fontsize": 15, "axes.titlesize": 19, "axes.titleweight": "bold", "axes.titlepad": 30,
})
LV = rf.LEVELS
LV_LABEL = ["無", "中性", "0", "T", "T+A", "T+A\n+C", "T+A\n+C+T"]
MODELS = [("Qwen3-8B-FP8", "Qwen3 思考", "#1f4e9c"), ("Qwen3-8B-FP8-nothink", "Qwen3 不思考", "#5b8fd6"),
          ("Llama-3.1-8B-Instruct", "Llama-3.1", "#c0392b"), ("Qwen2.5-7B-Instruct", "Qwen2.5", "#2e8b57"),
          ("granite-3.3-8b-instruct", "Granite-3.3", GRAY)]
load = rf.load


def pct_axis(ax, label="求助率"):
    ax.set_ylim(-0.03, 1.05)
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_ylabel(label)
    ax.grid(axis="y", color=LIGHT, lw=0.8)
    ax.set_axisbelow(True)


def shade_action(ax):
    ax.axvspan(3.5, 6.5, color="#f2f2f2", zorder=0)
    ax.text(5, 1.065, "寫到「行動」", ha="center", va="bottom", fontsize=14, color=GRAY)


def ladder_axes(ax):
    ax.set_xticks(range(len(LV)), LV_LABEL, fontsize=14)
    ax.set_xlim(-0.4, 6.4)


def save(fig, name):
    if not getattr(fig, "_laid", False):
        fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", name)


# ---------------------------------------------------------------- 第 7 頁：無 persona 基線
def s07_baseline():
    rows_by = {"Gemini": load(RES / "gemini-3.5-flash-lite.jsonl")}
    for tag, name, _ in MODELS:
        rows_by[name] = load(RES / f"{tag}.jsonl")
    order = ["Gemini", "Qwen3 思考", "Qwen3 不思考", "Llama-3.1", "Qwen2.5", "Granite-3.3"]
    tick = ["Gemini", "Qwen3\n思考", "Qwen3\n不思考", "Llama\n3.1", "Qwen\n2.5", "Granite\n3.3"]
    kinds = [("一般題（不用問）", lambda r: r["need"] == "complete", LIGHT),
             ("缺條件題（該問）", lambda r: r["need"] == "missing", INK)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for ax, lang in zip(axes, ("en", "zh")):
        for j, (lab, f, color) in enumerate(kinds):
            for i, m in enumerate(order):
                rs = [r for r in rows_by[m] if r["lang"] == lang and f(r)]
                y = sum(r["asked"] for r in rs) / len(rs)
                ax.bar(i + (j - .5) * .38, y, width=.36, color=color, edgecolor=INK, lw=0.8, label=lab if i == 0 else None)
                ax.text(i + (j - .5) * .38, y + .02, f"{y:.0%}", ha="center", fontsize=12)
        ax.set_xticks(range(len(order)), tick, fontsize=14)
        ax.set_title("英文" if lang == "en" else "繁中")
        pct_axis(ax)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=2, bbox_to_anchor=(.5, 1.0))
    axes[1].set_ylabel("")
    fig.tight_layout(rect=(0, 0, 1, .9)); fig._laid = True
    save(fig, "s07_baseline.png")


# ---------------------------------------------------------------- 第 8 頁：思考模式、工具 vs 文字
def s08_think_text():
    think, nothink = load(RES / "Qwen3-8B-FP8.jsonl"), load(RES / "Qwen3-8B-FP8-nothink.jsonl")
    rate = lambda rows, need, lang: (lambda rs: sum(r["asked"] for r in rs) / len(rs))(
        [r for r in rows if r["need"] == need and (lang is None or r["lang"] == lang)])
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    xs = []
    for g, (gl, need) in enumerate((("一般題", "complete"), ("缺條件題", "missing"))):
        for lang_i, lang in enumerate(("en", "zh")):
            x = g * 2.6 + lang_i * 1.1
            xs.append((x + .2, f"{gl}\n{'英' if lang == 'en' else '中'}"))
            for k, (rows, lab, color) in enumerate(((nothink, "不思考", LIGHT), (think, "思考", INK))):
                y = rate(rows, need, lang)
                ax.bar(x + k * .42, y, width=.4, color=color, edgecolor=INK, lw=.8, label=lab if (g, lang_i) == (0, 0) else None)
                ax.text(x + k * .42, y + .02, f"{y:.0%}", ha="center", fontsize=12)
    ax.set_xticks([x for x, _ in xs], [l for _, l in xs], fontsize=13)
    ax.set_title("思考模式（Qwen3）")
    pct_axis(ax)
    ax.legend(loc="upper left")
    ax = axes[1]
    for i, (tag, name, _) in enumerate(MODELS):
        tool, text = load(RES / f"{tag}.jsonl"), load(RES / f"{tag}-textask.jsonl")
        for k, (rows, lab, color) in enumerate(((tool, "工具 ask_teacher", LIGHT), (text, "只能寫文字", INK))):
            y = rate(rows, "missing", None)
            ax.bar(i + (k - .5) * .38, y, width=.36, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
            ax.text(i + (k - .5) * .38, y + .02, f"{y:.0%}", ha="center", fontsize=12)
    ax.set_xticks(range(len(MODELS)), [n.replace(" ", "\n").replace("-", "\n") for _, n, _ in MODELS], fontsize=13)
    ax.set_title("求助的形式（缺條件題，英＋中）")
    pct_axis(ax, "")
    ax.legend(loc="upper center", bbox_to_anchor=(.5, -.17), ncol=2)
    save(fig, "s08_think_text.png")


# ---------------------------------------------------------------- 第 9 頁：TACT 低求助階梯（主結果）
def s09_ladder():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for ax, lang in zip(axes, ("en", "zh")):
        shade_action(ax)
        for tag, name, color in MODELS:
            rows = rf.panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing")
            ys, _ = rf.ladder_points(rows, lang)
            ax.plot(range(len(LV)), ys, color=color, marker="o", ms=7, lw=2.6 if tag != "granite-3.3-8b-instruct" else 2,
                    ls="-" if tag != "granite-3.3-8b-instruct" else "--", label=name)
        ladder_axes(ax)
        ax.set_title(("英文" if lang == "en" else "繁中") + "｜低求助 persona × 缺條件題")
        pct_axis(ax)
    axes[0].legend(loc="lower left", fontsize=13)
    axes[1].set_ylabel("")
    save(fig, "s09_ladder_low.png")


# ---------------------------------------------------------------- 第 10 頁：缺條件 vs 能力不足
def s10_ability():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for ax, (tag, name, color) in zip(axes, [MODELS[2], MODELS[3]]):
        shade_action(ax)
        miss = rf.panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing")
        abil = [r for r in load(RES / "step1" / f"{tag}-high.jsonl") if r["need"] == "ability" and r["op"] == "muldiv"
                and rf.level_of(r) in ("L0", "neutral")]
        abil += [r for r in load(RES / "step1_extra" / f"{tag}-low-ability.jsonl") if r["op"] == "muldiv"]
        for rows, lab, ls, c in ((miss, "缺條件題", "-", INK), (abil, "只學過加減的乘除題", "--", ACCENT2)):
            ys, _ = rf.ladder_points(rows, "zh")
            ax.plot(range(len(LV)), ys, ls=ls, color=c, marker="o", ms=7, lw=2.6, label=lab)
        ladder_axes(ax)
        ax.set_title(f"{name}｜繁中")
        pct_axis(ax)
    axes[0].legend(loc="lower left")
    axes[1].set_ylabel("")
    save(fig, "s10_ability.png")


# ---------------------------------------------------------------- 第 11 頁：工具名稱
def s11_toolname():
    names = [("ask_teacher", "ask_teacher（原版）", INK, "-"), ("ask_for_help", "ask_for_help（不提老師）", ACCENT2, "--"),
             ("raise_hand_neutral", "raise_hand（舉手問老師）", ACCENT, ":")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for ax, (tag, name, lang) in zip(axes, [("Qwen2.5-7B-Instruct", "Qwen2.5", "en"), ("Llama-3.1-8B-Instruct", "Llama-3.1", "zh")]):
        shade_action(ax)
        for tool, lab, c, ls in names:
            p = RES / "step1" / f"{tag}-low.jsonl" if tool == "ask_teacher" else RES / "step1_toolname" / f"{tag}-low-{tool}.jsonl"
            rows = rf.panel(load(p), "low", "missing")
            ys, _ = rf.ladder_points(rows, lang)
            ax.plot(range(len(LV)), ys, ls=ls, color=c, marker="o", ms=7, lw=2.6, label=lab)
        ladder_axes(ax)
        ax.set_title(f"{name}｜{'英文' if lang == 'en' else '繁中'}")
        pct_axis(ax, "呼叫求助工具的比例")
    axes[0].legend(loc="lower left", fontsize=13)
    axes[1].set_ylabel("")
    save(fig, "s11_toolname.png")


# ---------------------------------------------------------------- 第 12 頁：求助類型
def s12_types():
    asks = json.load(open(ROOT / "judge" / "asks_coded_all.json"))
    groups = [("gemini-3.5-flash-lite", "Gemini")] + [(t, n) for t, n, _ in MODELS]
    fig, ax = plt.subplots(figsize=(14, 6))
    for i, (m, ml) in enumerate(groups):
        for k, (lang, lab, color) in enumerate((("en", "英文", LIGHT), ("zh", "繁中", INK))):
            c = Counter(a["code"] for a in asks if a["model"] == m and a["lang"] == lang
                        and (a["step"] == "step0" or a["need"] != "missing"))
            v = c["EXEC"] / sum(c.values())
            ax.bar(i + (k - .5) * .38, v, width=.36, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
            ax.text(i + (k - .5) * .38, v + .02, f"{v:.0%}", ha="center", fontsize=13)
    ax.set_xticks(range(len(groups)), [n.replace(" ", "\n").replace("-", "\n") for _, n in groups], fontsize=14)
    pct_axis(ax, "執行性求助的比例（整題丟給老師）")
    ax.legend(loc="upper left")
    save(fig, "s12_types.png")


# ---------------------------------------------------------------- 第 13 頁：不問的時候做什麼
def s13_not_ask():
    models = [MODELS[3], MODELS[2], MODELS[1]]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, (key, title) in zip(axes, (("skip", "跳過率"), ("correct", "答對率"))):
        for i, (tag, name, _) in enumerate(models):
            rows = [r for r in load(RES / "step1_extra" / f"{tag}-low-ability.jsonl") if r["lang"] == "zh" and r["level"] in ("TAC", "TACT")]
            for j, (op, lab, color) in enumerate((("muldiv", "乘除題（不會的）", INK), ("addsub", "加減題（會的）", LIGHT))):
                rs = [r for r in rows if r["op"] == op]
                v = sum((r["final_action"] == "skip") if key == "skip" else bool(r["correct"]) for r in rs) / len(rs)
                ax.bar(i + (j - .5) * .38, v, width=.36, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
                ax.text(i + (j - .5) * .38, v + .02, f"{v:.0%}", ha="center", fontsize=13)
        ax.set_xticks(range(len(models)), [n for _, n, _ in models])
        ax.set_title(title)
        pct_axis(ax, "")
    axes[0].legend(loc="upper right")
    fig.suptitle("最高兩層低求助 persona、只學過加減、繁中", fontsize=16, color=GRAY)
    save(fig, "s13_not_ask.png")


# ---------------------------------------------------------------- 第 14 頁：說與做
def s14_say_do():
    cfgs = [("Llama-3.1-8B-Instruct", "Llama-3.1｜英文", "en"), ("Qwen3-8B-FP8", "Qwen3 思考｜英文", "en")]
    groups = [({"L0", "neutral"}, "無／中性", "white", "s"), ({"0", "T"}, "0、T（沒寫行動）", GRAY, "o"),
              ({"TA", "TAC", "TACT"}, "T+A 以上（寫到行動）", INK, "^")]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True, sharex=True)
    for ax, (tag, title, lang) in zip(axes, cfgs):
        sv = load(RES / "survey" / f"{tag}.jsonl")
        sc = defaultdict(lambda: defaultdict(list))
        for r in sv:
            if r["score"] is not None and r["lang"] == lang:
                sc[r["persona"]][r["scale"]].append(r["score"])
        mean = lambda v: sum(v) / len(v)
        avoid = {p: mean(v["avoid"]) - mean(v["adaptive"]) for p, v in sc.items() if v["avoid"] and v["adaptive"]}
        by = defaultdict(list)
        for r in rf.panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing"):
            if r["lang"] == lang:
                by[r["persona"]].append(r["asked"])
        for lvset, lab, color, mk in groups:
            pts = [(avoid[p], sum(a) / len(a)) for p, a in by.items()
                   if p in avoid and rf.level_of({"persona": p, "level": p.split("-")[1] if "-" in p else None}) in lvset]
            ax.scatter([x for x, _ in pts], [y for _, y in pts], s=130, c=color, edgecolors=INK, marker=mk, lw=1.2, label=lab, zorder=3)
        ax.set_title(title)
        ax.set_xlabel("問卷：越右 ＝ 說自己越迴避求助")
        pct_axis(ax, "實際求助率")
    axes[0].legend(loc="lower left", fontsize=13)
    axes[1].set_ylabel("")
    save(fig, "s14_say_do.png")


# ---------------------------------------------------------------- 第 15 頁：CAPS
def s15_caps():
    models = [("Llama-3.1-8B-Instruct", "Llama-3.1"), ("Qwen3-8B-FP8", "Qwen3 思考"), ("Qwen2.5-7B-Instruct", "Qwen2.5"),
              ("Qwen3-8B-FP8-nothink", "Qwen3 不思考")]
    ptypes = [("neutral", "中性", LIGHT), ("trait", "害羞（特質）", GRAY), ("process", "怕被看扁（歷程）", INK)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)
    for ax, lang in zip(axes, ("en", "zh")):
        for i, (tag, name) in enumerate(models):
            rows = rf.caps_channels(tag)
            for j, (pt, lab, color) in enumerate(ptypes):
                rs = [r for r in rows if r["ptype"] == pt and r["lang"] == lang and r["_c"] in ("public", "private")]
                v = sum(r["_c"] == "public" for r in rs) / len(rs)
                x = i + (j - 1) * .27
                ax.bar(x, v, width=.25, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
                ax.text(x, v + .02, f"{v:.0%}", ha="center", fontsize=11)
        ax.set_xticks(range(len(models)), [n.replace(" ", "\n") for _, n in models], fontsize=14)
        ax.set_title("英文" if lang == "en" else "繁中")
        pct_axis(ax, "選「全班面前舉手」的比例")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, bbox_to_anchor=(.5, 1.0))
    axes[1].set_ylabel("")
    fig.tight_layout(rect=(0, 0, 1, .9)); fig._laid = True
    save(fig, "s15_caps.png")


# ---------------------------------------------------------------- 第 16 頁：第三人稱
def s16_third():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    ax = axes[0]
    shade_action(ax)
    tag = "Qwen3-8B-FP8"
    for sub, suf, lab, ls, c in (("step1", "", "第一人稱：你……", "-", INK), ("step1_third", "-third", "第三人稱：這位學生……", "--", ACCENT2)):
        rows = rf.panel(load(RES / sub / f"{tag}-low{suf}.jsonl"), "low", "missing")
        ys, _ = rf.ladder_points(rows, "zh")
        ax.plot(range(len(LV)), ys, ls=ls, color=c, marker="o", ms=7, lw=2.6, label=lab)
    ladder_axes(ax)
    ax.set_title("Qwen3 思考｜繁中｜低求助")
    pct_axis(ax)
    ax.legend(loc="lower left", fontsize=13)
    ax = axes[1]
    models = [MODELS[3], MODELS[2], MODELS[0]]
    for i, (tag, name, _) in enumerate(models):
        for j, (sub, suf, lab, color) in enumerate((("step1", "", "第一人稱", INK), ("step1_third", "-third", "第三人稱", ACCENT2))):
            rows = [r for r in rf.panel(load(RES / sub / f"{tag}-high{suf}.jsonl"), "high", "ability", "muldiv")
                    if r["lang"] == "en" and rf.level_of(r) == "TACT"]
            v = sum(bool(r["correct"]) for r in rows) / len(rows)
            ax.bar(i + (j - .5) * .38, v, width=.36, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
            ax.text(i + (j - .5) * .38, v + .02, f"{v:.0%}", ha="center", fontsize=13)
    ax.set_xticks(range(len(models)), [n for _, n, _ in models])
    ax.set_title("能力外洩：「只學過加減」卻答對乘除題（英文）")
    pct_axis(ax, "答對率")
    ax.legend(loc="upper left")
    save(fig, "s16_third.png")


# ---------------------------------------------------------------- 高求助 persona × 只學過加減的乘除題（老師建議的方向）
def s09b_high_ability():
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), sharey=True)
    for ax, lang in zip(axes, ("en", "zh")):
        shade_action(ax)
        for tag, name, color in MODELS:
            rows = rf.panel(load(RES / "step1" / f"{tag}-high.jsonl"), "high", "ability", "muldiv")
            ys, _ = rf.ladder_points(rows, lang)
            ax.plot(range(len(LV)), ys, color=color, marker="o", ms=7, lw=2.6 if tag != "granite-3.3-8b-instruct" else 2,
                    ls="-" if tag != "granite-3.3-8b-instruct" else "--", label=name)
            print(lang, name, " ".join(f"{y:.0%}" for y in ys))
        ladder_axes(ax)
        ax.set_title(("英文" if lang == "en" else "繁中") + "｜高求助 persona × 只學過加減的乘除題")
        pct_axis(ax)
    axes[1].set_ylabel("")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, fontsize=14, bbox_to_anchor=(.5, 0))
    fig.tight_layout(rect=(0, .08, 1, 1)); fig._laid = True
    save(fig, "s09b_high_ability.png")


if __name__ == "__main__":
    import sys
    fs = (s07_baseline, s08_think_text, s09_ladder, s09b_high_ability, s10_ability, s11_toolname, s12_types,
          s13_not_ask, s14_say_do, s15_caps, s16_third)
    for f in fs:
        if len(sys.argv) == 1 or f.__name__ in sys.argv[1:]:
            f()
