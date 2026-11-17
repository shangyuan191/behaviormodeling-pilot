"""投影片附錄用的「全部模型」版本數據圖。

正文的第 10、11、13、14、16 頁為了版面只挑 2–3 個模型；這支程式把同一張圖畫成 5 組開源設定全列的版本，
放在附錄備查，並在終端機印出每格數字，方便核對正文挑的模型是否具代表性。
計算方式與 slides_figures.py 完全相同（直接沿用它的函式與樣式）。
用法：~/miniforge3/envs/adl_hw3_py311/bin/python slides_appendix_figures.py
輸出：results/report/slides/appendix/A10_ability_all.png 等
"""
import matplotlib.pyplot as plt

import slides_figures as sf
from slides_figures import INK, GRAY, LIGHT, ACCENT, ACCENT2, LV, MODELS, RES, load, rf

OUT = sf.OUT / "appendix"
OUT.mkdir(parents=True, exist_ok=True)
LANGS = (("en", "英文"), ("zh", "繁中"))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", name)


def small_ladder_axes(ax, first_col, first_row, last_row, title):
    sf.ladder_axes(ax)
    ax.tick_params(axis="x", labelsize=11)
    if not last_row:
        ax.set_xticklabels([])
    sf.pct_axis(ax, "求助率" if first_col else "")
    if first_row:
        ax.set_title(title, fontsize=16, pad=26)


def fmt(ys):
    return " ".join("  — " if y is None else f"{y:4.0%}" for y in ys)


# ---------------------------------------------------------------- A10：缺條件題 vs 只學過加減的乘除題
def a10_ability():
    fig, axes = plt.subplots(2, 5, figsize=(22, 9), sharey=True)
    print("\n[A10] 低求助階梯｜實線＝缺條件題、虛線＝只學過加減的乘除題")
    for c, (tag, name, _) in enumerate(MODELS):
        miss = rf.panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing")
        abil = [r for r in load(RES / "step1" / f"{tag}-high.jsonl") if r["need"] == "ability" and r["op"] == "muldiv"
                and rf.level_of(r) in ("L0", "neutral")]
        abil += [r for r in load(RES / "step1_extra" / f"{tag}-low-ability.jsonl") if r["op"] == "muldiv"]
        for r_, (lang, lname) in enumerate(LANGS):
            ax = axes[r_, c]
            sf.shade_action(ax)
            for rows, lab, ls, col in ((miss, "缺條件題", "-", INK), (abil, "只學過加減的乘除題", "--", ACCENT2)):
                ys, _ = rf.ladder_points(rows, lang)
                ax.plot(range(len(LV)), ys, ls=ls, color=col, marker="o", ms=5, lw=2.2, label=lab)
                print(f"  {name:12s} {lname} {lab:10s} {fmt(ys)}")
            small_ladder_axes(ax, c == 0, r_ == 0, r_ == 1, name)
            if c == 0:
                ax.set_ylabel(f"{lname}\n求助率")
    axes[0, 0].legend(loc="lower left", fontsize=12)
    save(fig, "A10_ability_all.png")


# ---------------------------------------------------------------- A11：工具名稱
def a11_toolname():
    names = [("ask_teacher", "ask_teacher（原版）", INK, "-"), ("ask_for_help", "ask_for_help（不提老師）", ACCENT2, "--"),
             ("raise_hand_neutral", "raise_hand（舉手問老師）", ACCENT, ":")]
    fig, axes = plt.subplots(2, 5, figsize=(22, 9), sharey=True)
    print("\n[A11] 低求助 × 缺條件題｜三種求助工具名稱")
    for c, (tag, name, _) in enumerate(MODELS):
        for r_, (lang, lname) in enumerate(LANGS):
            ax = axes[r_, c]
            sf.shade_action(ax)
            for tool, lab, col, ls in names:
                p = RES / "step1" / f"{tag}-low.jsonl" if tool == "ask_teacher" else RES / "step1_toolname" / f"{tag}-low-{tool}.jsonl"
                ys, _ = rf.ladder_points(rf.panel(load(p), "low", "missing"), lang)
                ax.plot(range(len(LV)), ys, ls=ls, color=col, marker="o", ms=5, lw=2.2, label=lab)
                print(f"  {name:12s} {lname} {tool:18s} {fmt(ys)}")
            small_ladder_axes(ax, c == 0, r_ == 0, r_ == 1, name)
            if c == 0:
                ax.set_ylabel(f"{lname}\n呼叫求助工具的比例")
    axes[0, 0].legend(loc="lower left", fontsize=11)
    save(fig, "A11_toolname_all.png")


# ---------------------------------------------------------------- A13：不問的時候做什麼
def a13_not_ask():
    fig, axes = plt.subplots(2, 2, figsize=(18, 10), sharey=True)
    print("\n[A13] 最高兩層低求助 persona、只學過加減｜跳過率、答對率（乘除／加減）")
    for r_, (lang, lname) in enumerate(LANGS):
        for k, (key, title) in enumerate((("skip", "跳過率"), ("correct", "答對率"))):
            ax = axes[r_, k]
            for i, (tag, name, _) in enumerate(MODELS):
                rows = [r for r in load(RES / "step1_extra" / f"{tag}-low-ability.jsonl")
                        if r["lang"] == lang and r["level"] in ("TAC", "TACT")]
                vals = []
                for j, (op, lab, color) in enumerate((("muldiv", "乘除題（不會的）", INK), ("addsub", "加減題（會的）", LIGHT))):
                    rs = [r for r in rows if r["op"] == op]
                    v = sum((r["final_action"] == "skip") if key == "skip" else bool(r["correct"]) for r in rs) / len(rs)
                    vals.append(v)
                    ax.bar(i + (j - .5) * .38, v, width=.36, color=color, edgecolor=INK, lw=.8,
                           label=lab if i == 0 else None)
                    ax.text(i + (j - .5) * .38, v + .02, f"{v:.0%}", ha="center", fontsize=12)
                print(f"  {lname} {title} {name:12s} 乘除 {vals[0]:4.0%}  加減 {vals[1]:4.0%}")
            ax.set_xticks(range(len(MODELS)), [n.replace(" ", "\n") for _, n, _ in MODELS], fontsize=14)
            ax.set_title(f"{lname}｜{title}", pad=12)
            sf.pct_axis(ax, "")
    axes[0, 0].legend(loc="upper right")
    save(fig, "A13_not_ask_all.png")


# ---------------------------------------------------------------- A14：說與做
def a14_say_do():
    from collections import defaultdict
    groups = [({"L0", "neutral"}, "無／中性", "white", "s"), ({"0", "T"}, "0、T（沒寫行動）", GRAY, "o"),
              ({"TA", "TAC", "TACT"}, "T+A 以上（寫到行動）", INK, "^")]
    fig, axes = plt.subplots(2, 5, figsize=(22, 9), sharey=True, sharex=True)
    print("\n[A14] 說與做｜每組 persona 的（問卷迴避分數平均, 實際求助率平均）")
    for c, (tag, name, _) in enumerate(MODELS):
        sv = load(RES / "survey" / f"{tag}.jsonl")
        beh = rf.panel(load(RES / "step1" / f"{tag}-low.jsonl"), "low", "missing")
        for r_, (lang, lname) in enumerate(LANGS):
            ax = axes[r_, c]
            sc = defaultdict(lambda: defaultdict(list))
            for r in sv:
                if r["score"] is not None and r["lang"] == lang:
                    sc[r["persona"]][r["scale"]].append(r["score"])
            mean = lambda v: sum(v) / len(v)
            avoid = {p: mean(v["avoid"]) - mean(v["adaptive"]) for p, v in sc.items() if v["avoid"] and v["adaptive"]}
            by = defaultdict(list)
            for r in beh:
                if r["lang"] == lang:
                    by[r["persona"]].append(r["asked"])
            summary = []
            for lvset, lab, color, mk in groups:
                pts = [(avoid[p], sum(a) / len(a)) for p, a in by.items()
                       if p in avoid and rf.level_of({"persona": p, "level": p.split("-")[1] if "-" in p else None}) in lvset]
                ax.scatter([x for x, _ in pts], [y for _, y in pts], s=70, c=color, edgecolors=INK, marker=mk, lw=1,
                           label=lab, zorder=3)
                if pts:
                    summary.append(f"{lab[:6]}({mean([x for x, _ in pts]):+.1f}, {mean([y for _, y in pts]):.0%})")
            print(f"  {name:12s} {lname} n_persona={len(avoid):2d}  " + "  ".join(summary))
            sf.pct_axis(ax, f"{lname}\n實際求助率" if c == 0 else "")
            if r_ == 0:
                ax.set_title(name, fontsize=16, pad=12)
            if r_ == 1:
                ax.set_xlabel("問卷迴避分數（越右越迴避）", fontsize=12)
    axes[0, 0].legend(loc="lower left", fontsize=11)
    save(fig, "A14_say_do_all.png")


# ---------------------------------------------------------------- A16：第三人稱
def a16_third():
    fig, axes = plt.subplots(2, 5, figsize=(22, 9), sharey=True)
    print("\n[A16a] 低求助 × 缺條件題｜第一人稱（實線）vs 第三人稱（虛線）")
    for c, (tag, name, _) in enumerate(MODELS):
        for r_, (lang, lname) in enumerate(LANGS):
            ax = axes[r_, c]
            sf.shade_action(ax)
            for sub, suf, lab, ls, col in (("step1", "", "第一人稱：你……", "-", INK),
                                            ("step1_third", "-third", "第三人稱：這位學生……", "--", ACCENT2)):
                ys, _ = rf.ladder_points(rf.panel(load(RES / sub / f"{tag}-low{suf}.jsonl"), "low", "missing"), lang)
                ax.plot(range(len(LV)), ys, ls=ls, color=col, marker="o", ms=5, lw=2.2, label=lab)
                print(f"  {name:12s} {lname} {lab[:4]} {fmt(ys)}")
            small_ladder_axes(ax, c == 0, r_ == 0, r_ == 1, name)
            if c == 0:
                ax.set_ylabel(f"{lname}\n求助率")
    axes[0, 0].legend(loc="lower left", fontsize=11)
    save(fig, "A16a_third_ladder_all.png")

    fig, axes = plt.subplots(1, 2, figsize=(18, 6.2), sharey=True)
    print("\n[A16b] 能力外洩｜高求助 TACT persona、只學過加減的乘除題答對率（第一 / 第三人稱）")
    for ax, (lang, lname) in zip(axes, LANGS):
        for i, (tag, name, _) in enumerate(MODELS):
            vals = []
            for j, (sub, suf, lab, color) in enumerate((("step1", "", "第一人稱", INK), ("step1_third", "-third", "第三人稱", ACCENT2))):
                rows = [r for r in rf.panel(load(RES / sub / f"{tag}-high{suf}.jsonl"), "high", "ability", "muldiv")
                        if r["lang"] == lang and rf.level_of(r) == "TACT"]
                v = sum(bool(r["correct"]) for r in rows) / len(rows)
                vals.append(v)
                ax.bar(i + (j - .5) * .38, v, width=.36, color=color, edgecolor=INK, lw=.8, label=lab if i == 0 else None)
                ax.text(i + (j - .5) * .38, v + .02, f"{v:.0%}", ha="center", fontsize=12)
            print(f"  {lname} {name:12s} 第一 {vals[0]:4.0%}  第三 {vals[1]:4.0%}")
        ax.set_xticks(range(len(MODELS)), [n.replace(" ", "\n") for _, n, _ in MODELS], fontsize=14)
        ax.set_title(f"能力外洩｜{lname}", pad=12)
        sf.pct_axis(ax, "答對率" if lang == "en" else "")
    axes[0].legend(loc="upper left")
    save(fig, "A16b_third_leak_all.png")


if __name__ == "__main__":
    for f in (a10_ability, a11_toolname, a13_not_ask, a14_say_do, a16_third):
        f()
