"""投影片用的示意圖與「截圖框」（白底黑字）。對話、問句、數字都取自實際資料（見各函式註解）。
輸出到 results/report/slides/d*.png。用法：~/miniforge3/envs/adl_hw3_py311/bin/python slides_diagrams.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "results" / "report" / "slides"
OUT.mkdir(parents=True, exist_ok=True)
INK, GRAY, LIGHT, PALE, ACCENT, RED = "#111111", "#8a8a8a", "#d9d9d9", "#f3f3f3", "#1f4e9c", "#c0392b"
plt.rcParams.update({"font.family": ["DejaVu Sans", "Droid Sans Fallback"], "font.size": 17, "text.color": INK,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})


def canvas(w=14, h=7.2):
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, text="", fc="white", ec=INK, lw=1.6, fs=17, color=INK, ha="center", va="center",
        r=0.12, weight="normal", dashed=False, pad=0.25):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw,
                                ls="--" if dashed else "-"))
    if text:
        tx = x + w / 2 if ha == "center" else x + pad
        ty = y + h / 2 if va == "center" else y + h - pad
        ax.text(tx, ty, text, ha=ha, va=va, fontsize=fs, color=color, weight=weight, linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, color=INK, lw=2, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=22, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}"))


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", name)


# 第 1 頁：封面插圖
def d01_cover():
    fig, ax = canvas(14, 6)
    box(ax, 0.8, 1.6, 3.6, 2.8, "LLM 學生\n＋ persona", fc=PALE, fs=22, weight="bold")
    box(ax, 5.4, 3.3, 3.6, 1.4, "題目：小菲把一些鉛筆\n平均排成 3 排……", fs=15)
    arrow(ax, 5.4, 4.0, 4.5, 3.4)
    box(ax, 5.4, 1.1, 3.6, 1.4, "ask_teacher\n問老師？", fc=INK, color="white", fs=19, weight="bold")
    arrow(ax, 4.5, 2.6, 5.35, 1.8)
    box(ax, 10.1, 1.1, 3.1, 1.4, "老師", fs=20)
    arrow(ax, 9.05, 1.8, 10.05, 1.8, style="<|-|>")
    ax.text(7.2, 0.4, "persona 寫多細，才控制得了它問不問？", ha="center", fontsize=20, color=GRAY)
    save(fig, "d01_cover.png")


# 第 2 頁：研究問題（Qwen3 不思考、英文、缺條件題：L0 77.8%、0 要素 76.9%、TACT 3.7%）
def d02_hook():
    fig, ax = canvas(14, 6.2)
    rows = [("（沒有人設）", 0.78), ("You are shy.\n你個性害羞。", 0.77),
            ("In this math practice, when you come across a problem\nyou can't solve, you don't ask your teacher.\n在這次數學練習中，遇到不會的題目時，你不會問老師。", 0.04)]
    for i, (txt, v) in enumerate(rows):
        y = 4.6 - i * 1.85
        box(ax, 0.4, y - 0.15, 6.4, 1.5, txt, fs=14 if i == 2 else 17, ha="left", fc=PALE if i == 2 else "white")
        ax.add_patch(plt.Rectangle((7.3, y + 0.2), 5.6 * v, 0.8, fc=INK if i < 2 else RED, ec=INK))
        ax.add_patch(plt.Rectangle((7.3, y + 0.2), 5.6, 0.8, fc="none", ec=LIGHT, lw=1))
        ax.text(7.4 + 5.6 * v + 0.1, y + 0.6, f"{v:.0%}", va="center", fontsize=24, weight="bold", color=INK if i < 2 else RED)
    ax.text(10.1, 5.95, "會問老師的比例", ha="center", fontsize=16, color=GRAY)
    ax.text(0.4, 0.2, "Qwen3-8B（不思考）・英文・缺條件題（少一個數字）", fontsize=14, color=GRAY)
    save(fig, "d02_hook.png")


# 第 3 頁：一個回合（實際回合：Qwen3-8B-FP8-nothink，key M05|missing|zh|4）
def d03_episode():
    fig, ax = canvas(14, 7.6)
    steps = [("題目", PALE), ("模型", PALE), ("ask_teacher", INK), ("規則式老師", "white"), ("submit_answer\n或 skip", "white")]
    for i, (t, fc) in enumerate(steps):
        x = 0.3 + i * 2.75
        box(ax, x, 6.1, 2.25, 1.1, t, fc=fc, color="white" if fc == INK else INK, fs=16, weight="bold")
        if i < len(steps) - 1:
            arrow(ax, x + 2.28, 6.65, x + 2.72, 6.65)
    arrow(ax, 9.1, 6.05, 3.9, 6.05, rad=-0.25, color=GRAY, lw=1.5)
    ax.text(6.5, 5.05, "最多 4 步", ha="center", fontsize=14, color=GRAY)
    chat = [("SYSTEM", "你是一個正在做數學練習題的學生。你可以使用以下工具：ask_teacher、submit_answer、skip。", "white", True),
            ("題目", "小菲把一些鉛筆平均排成 3 排。每一排有幾枝鉛筆？", "white", False),
            ("模型 → ask_teacher", "……沒有說明總共有多少枝鉛筆。請問是否需要更多的資訊才能解答這道題目？", PALE, False),
            ("老師（規則）", "小菲有 12 枝鉛筆。", "white", False),
            ("模型 → submit_answer", "4 ✓", PALE, False)]
    for i, (who, txt, fc, dashed) in enumerate(chat):
        y = 4.3 - i * 0.98
        box(ax, 0.3, y, 13.4, 0.82, "", fc=fc, dashed=dashed, lw=1.2)
        ax.text(0.55, y + 0.41, who, va="center", fontsize=13, color=GRAY, weight="bold")
        ax.text(3.6, y + 0.41, txt, va="center", fontsize=15)
    save(fig, "d03_episode.png")


# 第 4 頁：三種題目（M05）
def d04_items():
    fig, ax = canvas(14, 6.4)
    cards = [("一般題", "小菲把 12 枝鉛筆\n平均排成 3 排。\n每一排有幾枝鉛筆？", "不用問", "white", INK),
             ("缺條件題", "小菲把「一些」鉛筆\n平均排成 3 排。\n每一排有幾枝鉛筆？", "該問（老師給「12 枝」）", PALE, RED),
             ("只學過加減", "系統提示多一句：\n「你只學過加法和減法」\n＋同一題（要用除法）", "該問（加減題是對照）", PALE, RED)]
    for i, (title, body, verdict, fc, vc) in enumerate(cards):
        x = 0.4 + i * 4.55
        box(ax, x, 1.2, 4.2, 4.7, "", fc=fc)
        ax.text(x + 2.1, 5.35, title, ha="center", fontsize=22, weight="bold")
        ax.text(x + 2.1, 3.4, body, ha="center", va="center", fontsize=17, linespacing=1.7)
        ax.text(x + 2.1, 1.65, verdict, ha="center", fontsize=16, weight="bold", color=vc)
    ax.text(7, 0.45, "24 題（加減、乘除各 12）× 英／中，來自 UMWP（LREC-COLING 2024）", ha="center", fontsize=14, color=GRAY)
    save(fig, "d04_items.png")


# 第 5 頁：TACT 階梯
def d05_tact():
    fig, ax = canvas(14, 7.4)
    steps = [("0 要素", "你個性害羞。"), ("T 對象", "你很怕你的老師。"), ("T＋A 行動", "你很少問老師問題。"),
             ("T＋A＋C 情境", "做數學練習遇到不會的題目時，你不會問老師。"), ("T＋A＋C＋T 時間", "在這次數學練習中，遇到不會的題目時，你不會問老師。")]
    for i, (lv, ex) in enumerate(steps):
        x, y = 0.4 + i * 0.55, 0.5 + i * 1.25
        act = i >= 2
        box(ax, x, y, 13.1 - i * 0.55, 1.05, "", fc=INK if act else PALE, lw=1.2)
        ax.text(x + 0.3, y + 0.52, lv, va="center", fontsize=17, weight="bold", color="white" if act else INK)
        ax.text(4.9, y + 0.52, ex, va="center", fontsize=16, color="white" if act else INK)
    ax.text(13.5, 0.15, "每層 3 種措辭；對照：無 persona、中性（「你的生日在三月」）", ha="right", fontsize=13, color=GRAY)
    ax.text(13.5, 6.95, "黑底＝寫到「行動」", ha="right", fontsize=14, color=GRAY)
    save(fig, "d05_tact.png")


# 第 6 頁：實驗總覽矩陣
def d06_matrix():
    cols = ["Gemini", "Qwen3\n思考", "Qwen3\n不思考", "Llama\n3.1", "Qwen\n2.5", "Granite\n3.3"]
    rows = [("一 預設傾向：無 persona 基線", [1, 1, 1, 1, 1, 1]),
            ("一 求助形式：文字求助版", [0, 1, 1, 1, 1, 1]),
            ("二 TACT 階梯", [0, 1, 1, 1, 1, 1]),
            ("二 低求助 × 能力題", [0, 1, 1, 1, 1, 1]),
            ("二 工具名稱檢查", [0, 1, 1, 1, 1, 1]),
            ("三 求助類型編碼", [1, 1, 1, 1, 1, 1]),
            ("四 求助量表（說）", [0, 1, 1, 1, 1, 1]),
            ("五 CAPS 公開／私下", [0, 1, 1, 1, 1, 1]),
            ("六 第三人稱", [0, 1, 1, 1, 1, 1])]
    fig, ax = canvas(14, 8.3)
    x0, cw, rh, top = 5.6, 1.35, 0.72, 7.3
    for j, c in enumerate(cols):
        ax.text(x0 + j * cw + cw / 2, top + 0.45, c, ha="center", va="center", fontsize=14, weight="bold")
    for i, (name, marks) in enumerate(rows):
        y = top - (i + 1) * rh
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((0.3, y), x0 + len(cols) * cw - 0.3, rh, fc=PALE, ec="none"))
        ax.text(0.5, y + rh / 2, name, va="center", fontsize=16)
        for j, m in enumerate(marks):
            if m:
                ax.add_patch(plt.Circle((x0 + j * cw + cw / 2, y + rh / 2), 0.17, fc=INK))
    ax.text(0.5, 0.35, "共約 13.5 萬個回合 ＋ 1 萬筆問卷作答；開源模型用 vLLM、FP8、temperature 1.0", fontsize=14, color=GRAY)
    save(fig, "d06_matrix.png")


# 第 12 頁：問句範例（judge/asks_coded.json：A11|missing|zh|0 INFO；M05|ability|zh|0 EXEC，皆 Llama-3.1）
def d12_examples():
    fig, ax = canvas(14, 4.6)
    box(ax, 0.4, 2.45, 13.2, 1.7, "", fc="white")
    ax.text(0.7, 3.7, "工具性：問缺少的資訊", fontsize=16, weight="bold")
    ax.text(0.7, 2.95, "「阿保原本有多少本書？」", fontsize=20)
    box(ax, 0.4, 0.4, 13.2, 1.7, "", fc=PALE)
    ax.text(0.7, 1.65, "執行性：整題原封不動丟給老師", fontsize=16, weight="bold")
    ax.text(0.7, 0.9, "「小菲把 12 枝鉛筆平均排成 3 排。每一排有幾枝鉛筆？」", fontsize=20)
    ax.text(13.4, 3.7, "Llama・繁中", ha="right", fontsize=13, color=GRAY)
    save(fig, "d12_examples.png")


# 第 15 頁：CAPS 的兩個求助工具
def d15_tools():
    fig, ax = canvas(14, 4.2)
    box(ax, 0.4, 0.5, 6.3, 3.2, "", fc=INK)
    ax.text(3.55, 2.7, "raise_hand", ha="center", fontsize=24, weight="bold", color="white")
    ax.text(3.55, 1.5, "在全班面前舉手問老師\n（全班都會聽到）", ha="center", va="center", fontsize=17, color="white")
    box(ax, 7.3, 0.5, 6.3, 3.2, "", fc=PALE)
    ax.text(10.45, 2.7, "ask_after_class", ha="center", fontsize=24, weight="bold")
    ax.text(10.45, 1.5, "下課後私下問老師\n（只有老師聽到）", ha="center", va="center", fontsize=17)
    save(fig, "d15_tools.png")


# 第 16 頁：第一人稱 vs 第三人稱的系統提示
def d16_prompts():
    fig, ax = canvas(14, 4.6)
    box(ax, 0.4, 0.5, 6.4, 3.6, "", dashed=True)
    ax.text(0.7, 3.6, "第一人稱（扮演）", fontsize=16, weight="bold", color=GRAY)
    ax.text(0.7, 2.2, "你是一個正在做數學練習題的學生。\n……\n你很怕你的老師。", va="center", fontsize=18, linespacing=1.7)
    box(ax, 7.2, 0.5, 6.4, 3.6, "", dashed=True, ec=RED)
    ax.text(7.5, 3.6, "第三人稱（預測）", fontsize=16, weight="bold", color=RED)
    ax.text(7.5, 2.2, "你要預測一位學生在數學練習中的\n下一步。這位學生的描述如下：\n這位學生很怕自己的老師。", va="center",
            fontsize=18, linespacing=1.7)
    save(fig, "d16_prompts.png")


# 第 17 頁：各模型總覽（✓ ✗ △）
def d17_models():
    cols = ["會分辨\n該不該問", "persona\n控制得了", "不問時\n會分辨會不會", "一句話"]
    rows = [("Gemini", "✓", "—", "—", "最像理想學生（只測基線）"),
            ("Qwen3 思考", "✓", "✓", "✗", "壓得最乾淨，但本來就會算"),
            ("Qwen3 不思考", "✓", "✓", "✗", "常只回文字"),
            ("Llama-3.1", "△", "✓", "✗", "繁中常把整題丟給老師"),
            ("Qwen2.5", "✗", "✓", "✓", "不會的跳過、會的照做"),
            ("Granite-3.3", "✗", "✗", "—", "什麼都問，推不動")]
    fig, ax = canvas(14, 6.6)
    xs, top, rh = [3.6, 5.6, 7.6], 5.3, 0.72
    for x, c in zip(xs, cols):
        ax.text(x, top + 0.45, c, ha="center", va="center", fontsize=14, weight="bold")
    ax.text(9.0, top + 0.45, cols[3], va="center", fontsize=14, weight="bold")
    for i, (m, *marks, note) in enumerate(rows):
        y = top - (i + 1) * rh
        if i % 2 == 0:
            ax.add_patch(plt.Rectangle((0.3, y), 13.4, rh, fc=PALE, ec="none"))
        ax.text(0.5, y + rh / 2, m, va="center", fontsize=17, weight="bold")
        for x, mk in zip(xs, marks):
            ax.text(x, y + rh / 2, mk, ha="center", va="center", fontsize=24,
                    color={"✓": INK, "✗": RED, "△": GRAY}.get(mk, GRAY), weight="bold")
        ax.text(9.0, y + rh / 2, note, va="center", fontsize=15)
    ax.text(0.5, 0.3, "△＝英文常不問、繁中連一般題也問", fontsize=13, color=GRAY)
    save(fig, "d17_models.png")


# 第 19 頁：限制
def d19_limits():
    fig, ax = canvas(14, 4.4)
    items = [("規模小", "24 題、每層 3 種措辭"), ("編碼由 Claude 判定", "還沒有第二位評分者"),
             ("還沒有真實學生資料", "只能說「能不能控制」，\n不能說「像不像學生」"), ("T＋A 以上\n接近直接下指令？", "最大的質疑")]
    for i, (t, s) in enumerate(items):
        x = 0.3 + i * 3.45
        box(ax, x, 0.5, 3.2, 3.4, "", fc=PALE)
        ax.text(x + 1.6, 2.85, t, ha="center", va="center", fontsize=18, weight="bold")
        ax.text(x + 1.6, 1.3, s, ha="center", va="center", fontsize=14, color=GRAY)
    save(fig, "d19_limits.png")


# 第 20 頁：下一步時間軸
def d20_next():
    fig, ax = canvas(14, 3.4)
    steps = [("Gemini\n完整實驗", "需付費 API"), ("台灣在地模型", "如 TAIDE"), ("人工信度", "第二位評分者"),
             ("混合效果模型", "只需 CPU"), ("真實學生資料", "需倫理審查")]
    ax.plot([0.9, 13.1], [1.5, 1.5], color=INK, lw=2)
    for i, (t, s) in enumerate(steps):
        x = 1.0 + i * 3.0
        ax.add_patch(plt.Circle((x, 1.5), 0.22, fc=INK if i == 0 else "white", ec=INK, lw=2, zorder=3))
        ax.text(x, 2.0, t, ha="center", va="bottom", fontsize=16, weight="bold")
        ax.text(x, 0.95, s, ha="center", va="top", fontsize=14, color=GRAY)
    save(fig, "d20_next.png")


# 附錄 A1：完整系統提示與工具（run_pilot.py 第 40–85 行）
def dA1_prompt():
    fig, ax = canvas(14, 6.6)
    box(ax, 0.3, 3.6, 13.4, 2.7, "", dashed=True)
    ax.text(0.6, 5.9, "SYSTEM（繁中）", fontsize=14, color=GRAY, weight="bold")
    ax.text(0.6, 4.75, "你是一個正在做數學練習題的學生。你可以使用以下工具：ask_teacher（傳送問題給老師）、\n"
                       "submit_answer（提交最終答案）、skip（跳過這一題）。每一回合使用一個工具。\n"
                       "＋ persona（一句）＋「你只學過加法和減法……」（只有能力題）", va="center", fontsize=15, linespacing=1.8)
    tools = [("ask_teacher(question)", "傳送問題給老師"), ("submit_answer(answer)", "提交最終答案（一個數字）"),
             ("skip(reason)", "跳過這一題")]
    for i, (t, d) in enumerate(tools):
        x = 0.3 + i * 4.5
        box(ax, x, 1.4, 4.3, 1.8, "", fc=PALE)
        ax.text(x + 2.15, 2.6, t, ha="center", fontsize=15, weight="bold", family="DejaVu Sans Mono")
        ax.text(x + 2.15, 1.85, d, ha="center", fontsize=14)
    ax.text(0.3, 0.6, "只說明有哪些工具，不說什麼時候該用（避免像 UMWP 的 Instruction 條件拉高發問率）", fontsize=14, color=GRAY)
    save(fig, "dA1_prompt.png")


if __name__ == "__main__":
    for f in (d01_cover, d02_hook, d03_episode, d04_items, d05_tact, d06_matrix, d12_examples, d15_tools,
              d16_prompts, d17_models, d19_limits, d20_next, dA1_prompt):
        f()
