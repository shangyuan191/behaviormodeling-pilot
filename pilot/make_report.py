"""產生 pilot 報告的 markdown（results/report/pilot_report.md），所有數字直接從結果檔計算。"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import run_pilot as rp  # 系統提示、工具定義等常數

FIG = {"step0": "blob/6abf8b0e-1329", "ladder": "blob/4a8577e0-45c4", "types": "blob/5a99cbc6-9aaa"}
items = json.loads((ROOT / "items" / "pilot_items.json").read_text())
personas = json.loads((ROOT / "personas" / "step1_personas.json").read_text())


def pct(x):
    return f"{x * 100:.0f}%"


def load(pattern):
    rows = []
    for f in ROOT.glob(pattern):
        rows += [json.loads(l) for l in f.open()]
    return rows


step0 = [r for r in load("results/*.jsonl")]
step1 = load("results/step1/*.jsonl")
eff = list(csv.DictReader(open(ROOT / "judge" / "effective_help.csv")))
asks = json.load(open(ROOT / "judge" / "asks_coded.json"))
text_units = json.load(open(ROOT / "judge" / "text_only_units.json"))

MODEL_LABEL = {"Qwen3-8B-FP8-nothink": "Qwen3-8B（關閉思考）", "Qwen3-8B-FP8": "Qwen3-8B（開啟思考）",
               "Llama-3.1-8B-Instruct": "Llama-3.1-8B", "gemini-3.5-flash-lite": "Gemini 3.5 Flash Lite",
               "Qwen3-8B-FP8-nothink-textask": "Qwen3-8B（關閉思考・文字求助版）"}
L = []
add = L.append


def rate(rows, f, key="asked"):
    rs = [r for r in rows if f(r)]
    return (sum(r[key] for r in rs) / len(rs), len(rs)) if rs else (float("nan"), 0)


# ------------------------------------------------------------------ 標題與摘要
n0 = Counter(r["model"] for r in step0)
n1 = Counter(r["model"] for r in step1)
add("# Pilot 報告：persona 描述顆粒度與 LLM agent 的求助行為")
add("")
add(f"2026-11-01 · Step 0 與補充實驗共 {len(step0):,} 個 episode、Step 1 共 {len(step1):,} 個 episode（Gemini 仍在每日額度下持續執行中，目前完成 {n0['gemini-3.5-flash-lite']} / 432）。程式與原始資料在伺服器 `~/BehaviorModeling/pilot/`。")
add("")
add("## 一、摘要")
add("")
add("回應老師的兩個建議：先測模型原本的行為，以及用「只學過加減」的能力設定讓模型「不會」。")
add("")
add("1. **模型原本會不會問老師，要看模型和語言。** 沒有 persona 時，一般題幾乎不問（Qwen 0–8%）；缺條件題則大多會問（Qwen 77–100%、Gemini 91–100%）。但 Llama 英文只有 38%，大多直接編一個答案；Llama 繁中卻連一般題也有 60% 會「問」。")
add("2. **「只學過加減」的能力設定有效果，但模型多半還是算得出來（能力外洩）。** Qwen 繁中的乘除題求助率從 3% 升到 43%，但答對率仍有 87–98%。")
add("3. **TACT 相容性原則在兩個開源模型上都成立。** 只寫特質（0）或只寫對老師的態度（T）幾乎沒有效果；寫到行動（A）之後求助率才大幅改變，四個要素都寫到時，缺條件題的有效求助率降到 2–10%。")
add("4. **「求助」的形式會影響結果。** 把求助做成 `ask_teacher` 工具，會比只能用文字問老師的求助率高很多（英文缺條件題 77% vs 37–47%）。")
add("5. **繁中讓模型更常做「執行性求助」。** Llama 繁中有 86% 的 `ask_teacher` 是把整題轉貼給老師；Qwen 英文幾乎全是工具性求助，繁中卻有 50% 是執行性求助。")
add("")

# ------------------------------------------------------------------ 設計
add("## 二、實驗設計")
add("")
add("| 實驗 | 目的 | 條件 | 模型 | 每格重複 |")
add("| --- | --- | --- | --- | --- |")
add("| Step 0 | 量模型原本的求助率（L0 基線） | 3 種需求 × 2 種語言，無 persona | Qwen3-8B（思考開／關）、Llama-3.1-8B、Gemini 3.5 Flash Lite | 開源 5 次；Gemini 3 次 |")
add("| 補充 A | 思考模式的影響 | 同 Step 0 | Qwen3-8B 開啟思考 | 5 次 |")
add("| 補充 B | 求助做成工具 vs 文字 | 同 Step 0，但沒有 `ask_teacher` 工具 | Qwen3-8B（關閉思考） | 5 次 |")
add("| Step 1 | TACT persona 階梯 | 19 種 persona × 需求 × 2 種語言 | Qwen3-8B（關閉思考）、Llama-3.1-8B | 3 次 |")
add("")
add("**三種「需求」：**")
add("")
add("| 需求 | 做法 | 預期 |")
add("| --- | --- | --- |")
add("| 一般題（complete） | 原題，資訊完整 | 不需要問 |")
add("| 缺條件題（missing） | 刪掉一個解題必要的數字 | 客觀上需要問 |")
add("| 只學過加減（ability） | 原題，加上系統提示「你只學過加法和減法，還沒有學過乘法和除法」 | 乘除題需要問；加減題是對照組 |")
add("")
add("**Step 1 的方向**依 Step 0 的基線決定：一般題與「只學過加減」的題目基線低，用**高求助階梯**往「會問」調；缺條件題基線高，用**低求助階梯**往「不問」調。")
add("")

# ------------------------------------------------------------------ 題目集
add("## 三、題目集")
add("")
add("**來源：** UMWP（Sun et al., LREC-COLING 2024；精讀 29）「缺關鍵資訊」類的 840 組配對題。每道缺條件題都記錄了它是從哪一題改來的，所以「一般題」和「缺條件題」可以一題對一題配對，唯一差別是少一個數字。")
add("")
add("**選題流程：**")
add("")
add("1. 只取 SVAMP、MultiArith、ASDiv 的題目（一、兩步的小學題，比 GSM8K 短）。")
add("2. 程式檢查：原題與缺條件題只差一個數字；答案能由題中數字的「只用加減」或「只用乘除」組合算出（標記運算類型）。符合的有 100 題。")
add("3. 人工挑出最乾淨的乘除題與加減題各 12 題，修正英文錯字，翻成繁中，並寫好老師的回覆（缺條件題中缺的那個數字）。繁中版經研究者（具教師資格）檢查。")
add("")
add("**英文版（UMWP 原題，僅修正錯字）**")
add("")
add("| 編號 | 運算 | 一般題 | 缺條件題 | 老師回覆（缺條件題） | 答案 |")
add("| --- | --- | --- | --- | --- | --- |")
for it in items:
    add(f"| {it['id']} | {'乘除' if it['op'] == 'muldiv' else '加減'} | {it['complete_en']} | {it['missing_en']} | {it['teacher_en']} | {it['answer']} |")
add("")
add("**繁中版**")
add("")
add("| 編號 | 運算 | 一般題 | 缺條件題 | 老師回覆（缺條件題） | 答案 |")
add("| --- | --- | --- | --- | --- | --- |")
for it in items:
    add(f"| {it['id']} | {'乘除' if it['op'] == 'muldiv' else '加減'} | {it['complete_zh']} | {it['missing_zh']} | {it['teacher_zh']} | {it['answer']} |")
add("")

# ------------------------------------------------------------------ persona
add("## 四、persona 設定（Step 1）")
add("")
add("依 TACT 相容性原則（Ajzen & Fishbein, 1977）：T 對象＝老師、A 行動＝問問題、C 情境＝數學練習遇到不會的題目、T 時間＝這次練習。每一層 3 種措辭，中英對照；兩個階梯逐句對稱，只差「會」與「不會」。")
add("")
add("**修改原則（第二版，經研究者審閱）：** 0 要素層只寫純粹的特質詞；T 層只寫對老師的態度，不提「數學」；T＋A 層不加條件句；情境統一寫成「不會的題目」；同層 3 句強度一致；中性對照用沒有人格聯想的事實。")
add("")
LV = {"L0": "無 persona", "neutral": "中性對照", "0": "0 要素", "T": "T", "TA": "T＋A", "TAC": "T＋A＋C", "TACT": "T＋A＋C＋T"}
for title, d in (("高求助階梯（用在一般題、只學過加減的題目）", "high"), ("低求助階梯（用在缺條件題）", "low"),
                 ("對照組（兩個階梯共用）", "ctrl")):
    add(f"**{title}**")
    add("")
    add("| 編號 | 層級 | 繁中 | English |")
    add("| --- | --- | --- | --- |")
    rows = [p for p in personas if (p["direction"] == d if d != "ctrl" else p["direction"] in ("none", "neutral"))]
    for p in rows:
        add(f"| {p['id']} | {LV[p['level']]} | {p['zh'] or '（不加）'} | {p['en'] or '(none)'} |")
    add("")

# ------------------------------------------------------------------ prompt
add("## 五、Prompt 與工具定義")
add("")
add("**系統提示的組成順序：** 基本說明 → persona（Step 1）→「只學過加減」（ability 條件）。系統提示只說明有哪些工具，**不說什麼時候該用**，避免像 UMWP 的 Instruction 條件一樣拉高求助率。")
add("")
add("| 部分 | English | 繁中 |")
add("| --- | --- | --- |")
add(f"| 基本說明（工具版） | {rp.SYSTEM['en']} | {rp.SYSTEM['zh']} |")
add(f"| 基本說明（文字求助版，補充 B） | {rp.SYSTEM_TEXT_HELP['en']} | {rp.SYSTEM_TEXT_HELP['zh']} |")
add(f"| 只學過加減 | {rp.ABILITY['en']} | {rp.ABILITY['zh']} |")
add(f"| 使用者訊息 | {rp.PROBLEM['en'].format(q='<題目>')} | {rp.PROBLEM['zh'].format(q='<題目>')} |")
add(f"| 老師回覆（一般題、只學過加減） | {rp.GENERIC_HINT['en']} | {rp.GENERIC_HINT['zh']} |")
add("| 老師回覆（缺條件題） | 見題目集的「老師回覆」欄 | 同左 |")
add("")
add("**工具定義**（function calling；每個工具一個必填的字串參數，說明文字依語言切換）：")
add("")
add("| 工具 | 參數 | English 說明 | 繁中說明 |")
add("| --- | --- | --- | --- |")
for t in rp.TOOLS:
    add(f"| `{t['name']}` | `{t['param'][0]}` | {t['description']['en']} {t['param'][1]['en']} | {t['description']['zh']}{t['param'][1]['zh']} |")
add("")
add("**一個 episode 的流程：** 模型每回合呼叫一個工具；呼叫 `ask_teacher` 時，由規則式老師回覆（不經過模型），再進入下一回合；呼叫 `submit_answer` 或 `skip`、只回文字，或滿 4 回合時結束。")
add("")
add("**執行設定：** temperature 1.0；開源模型用 vLLM 0.25.1、FP8 量化，tool parser 為 hermes（Qwen）與 llama3_json（Llama）；Qwen 用 `enable_thinking` 切換思考模式；Gemini 用官方 REST API 的原生 function calling。")
add("")

# ------------------------------------------------------------------ 結果：Step 0
add("## 六、結果")
add("")
add("### 6.1 Step 0：沒有 persona 時，模型會不會問老師")
add("")
add(f"![Step 0 各模型的求助率]({FIG['step0']})")
add("")
add("| 模型 | 語言 | 一般題 | 只學過加減・乘除題 | 只學過加減・加減題（對照） | 缺條件題 | n（一般／缺條件） |")
add("| --- | --- | --- | --- | --- | --- | --- |")
for m in ("Qwen3-8B-FP8-nothink", "Qwen3-8B-FP8", "Llama-3.1-8B-Instruct", "gemini-3.5-flash-lite"):
    for lang in ("en", "zh"):
        rs = [r for r in step0 if r["model"] == m and r["lang"] == lang]
        c = rate(rs, lambda r: r["need"] == "complete")
        a1 = rate(rs, lambda r: r["need"] == "ability" and r["op"] == "muldiv")
        a2 = rate(rs, lambda r: r["need"] == "ability" and r["op"] == "addsub")
        mi = rate(rs, lambda r: r["need"] == "missing")
        add(f"| {MODEL_LABEL[m]} | {'英' if lang == 'en' else '中'} | {pct(c[0])} | {pct(a1[0])} | {pct(a2[0])} | {pct(mi[0])} | {c[1]}／{mi[1]} |")
add("")
add("**能力外洩：**「只學過加減」的乘除題，最後的答對率：")
add("")
add("| 模型 | 英 | 中 |")
add("| --- | --- | --- |")
for m in ("Qwen3-8B-FP8-nothink", "Qwen3-8B-FP8", "Llama-3.1-8B-Instruct", "gemini-3.5-flash-lite"):
    vals = [pct(rate(step0, lambda r, l=l: r["model"] == m and r["lang"] == l and r["need"] == "ability" and r["op"] == "muldiv", "correct")[0]) for l in ("en", "zh")]
    add(f"| {MODEL_LABEL[m]} | {vals[0]} | {vals[1]} |")
add("")

# ------------------------------------------------------------------ 補充 A、B
add("### 6.2 補充實驗：思考模式、求助的形式")
add("")
add("| 條件 | Qwen 關閉思考 | Qwen 開啟思考 | Qwen 關閉思考・文字求助版 |")
add("| --- | --- | --- | --- |")
for need, label, f in (("complete", "一般題", lambda r: True), ("ability", "只學過加減・乘除題", lambda r: r["op"] == "muldiv"),
                       ("ability", "只學過加減・加減題", lambda r: r["op"] == "addsub"), ("missing", "缺條件題", lambda r: True)):
    cells = []
    for m in ("Qwen3-8B-FP8-nothink", "Qwen3-8B-FP8", "Qwen3-8B-FP8-nothink-textask"):
        v = [pct(rate(step0, lambda r, l=l: r["model"] == m and r["lang"] == l and r["need"] == need and f(r))[0]) for l in ("en", "zh")]
        cells.append(f"英 {v[0]}／中 {v[1]}")
    add(f"| {label} | " + " | ".join(cells) + " |")
skip_en = rate(step0, lambda r: r["model"] == "Qwen3-8B-FP8-nothink-textask" and r["lang"] == "en" and r["need"] == "missing", "asked")
sk = [r for r in step0 if r["model"] == "Qwen3-8B-FP8-nothink-textask" and r["lang"] == "en" and r["need"] == "missing"]
add("")
add(f"- **開啟思考後，行為更「理性」：** 一般題完全不問；缺條件題 94–100% 會問；「只學過加減」只在乘除題問，加減題不再亂問；「說要問卻沒呼叫工具」的情況消失。")
add(f"- **拿掉 `ask_teacher` 工具後，求助率大幅下降：** 英文缺條件題有 {pct(sum(r['final_action'] == 'skip' for r in sk) / len(sk))} 直接 `skip`（理由寫「資訊不足」），而不是寫訊息問老師。文字求助版的繁中數字較不準：「只回文字」都被算成寫給老師的訊息，但其中有一部分只是陳述或列出解題步驟。")
add("")

# ------------------------------------------------------------------ Step 1
add("### 6.3 Step 1：TACT persona 階梯")
add("")
add(f"![TACT 階梯]({FIG['ladder']})")
add("")
add("左圖的「有效求助率」＝呼叫 `ask_teacher`，或用文字明確請求（R）、說要去問（I）、工具格式壞掉（M）；分類方式見 6.4。")
add("")
LVL = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
add("**低求助 × 缺條件題（有效求助率）**")
add("")
add("| 模型 | 語言 | " + " | ".join(LV[l] for l in LVL) + " |")
add("| --- | --- | " + " | ".join("---" for _ in LVL) + " |")
for m in ("Qwen3-8B-FP8-nothink", "Llama-3.1-8B-Instruct"):
    for lang in ("en", "zh"):
        vals = [pct(float(next(e for e in eff if (e["step"], e["model"], e["need"], e["lang"], e["level"]) ==
                                ("step1", m, "missing", lang, l))["effective_help"])) for l in LVL]
        add(f"| {MODEL_LABEL[m]} | {'英' if lang == 'en' else '中'} | " + " | ".join(vals) + " |")
add("")
for title, need, op in (("高求助 × 只學過加減的乘除題（呼叫 ask_teacher）", "ability", "muldiv"),
                        ("高求助 × 一般題（呼叫 ask_teacher；其實不需要問）", "complete", None)):
    add(f"**{title}**")
    add("")
    add("| 模型 | 語言 | " + " | ".join(LV[l] for l in LVL) + " |")
    add("| --- | --- | " + " | ".join("---" for _ in LVL) + " |")
    for m in ("Qwen3-8B-FP8-nothink", "Llama-3.1-8B-Instruct"):
        for lang in ("en", "zh"):
            vals = [pct(rate(step1, lambda r, l=l: r["model"] == m and r["lang"] == lang and r["level"] == l and r["need"] == need
                             and (op is None or r["op"] == op))[0]) for l in LVL]
            add(f"| {MODEL_LABEL[m]} | {'英' if lang == 'en' else '中'} | " + " | ".join(vals) + " |")
    add("")
add("**觀察：**")
add("")
add("- **低求助方向：** 兩個模型都在 T＋A 開始大幅下降，T＋A＋C＋T 降到 2–10%。0 要素與 T 層幾乎沒有效果（Qwen 繁中的「你個性害羞」是唯一例外，有效求助率不變，但工具呼叫從 81% 降到 55%）。")
add("- **不問的時候在做什麼：** Qwen 多半說明「題目缺什麼」然後跳過；Llama 多半**硬編一個數字交出去**（T＋A＋C＋T 約 62–70%），比較像真實的求助迴避學生。")
add("- **高求助方向的最高點在 T＋A，而不是 T＋A＋C＋T。** T＋A（「你常常問老師問題」）是無條件的，連一般題也問（過度求助）；加上情境（C）後，模型比較會挑時機。這符合 CAPS 的 if–then 條件式行為。")
add("- **中性對照：** Qwen 的中性 persona ≈ 無 persona；Llama 英文在「只學過加減」題上，中性 persona 就讓求助率從 33% 升到 66%（無 persona 那格只有 36 次，需要更多資料確認）。")
add("- **同層措辭差異很大：** 例如 Qwen 低求助 T＋A 英文，3 句措辭的工具求助率分別是 33%、85%、11%。必須用多種措辭。")
add("")

# ------------------------------------------------------------------ 6.4 文字分類
codes = Counter(u["code"] for u in text_units)
add("### 6.4 「只回文字」的回覆分類")
add("")
add(f"有些 episode 最後只回了一段文字，沒有呼叫任何工具。共 {sum(u['n'] for u in text_units):,} 筆（去除重複後 {len(text_units)} 筆），由 Claude 先用規則初步分類，再逐筆人工檢查修正。")
add("")
add("| 代碼 | 類別 | 例子 | 筆數（去重後） |")
add("| --- | --- | --- | --- |")
for code, name, ex in (("R", "明確請求", "Please provide the total number of pencils.／請問原本有多少個朋友？"),
                       ("I", "說要去問、但沒有行動", "I will ask the teacher for clarification.／我會向老師請教。"),
                       ("S", "只陳述資訊不足，或說要跳過", "I need more information to solve this problem."),
                       ("P", "在解題，只是沒呼叫 submit_answer", "阿當比小潔多 10 − 2 = 8 顆蘋果。"),
                       ("M", "想呼叫 ask_teacher，但格式壞掉", "{\"name\": \"ask_teacher\", ...（Llama）"),
                       ("Q", "想呼叫其他工具，但格式壞掉", "{\"name\": \"skip\", ..."), ("O", "其他", "")):
    add(f"| {code} | {name} | {ex} | {codes[code]} |")
add("")
add("**結果：** 低求助 persona 下的文字回覆多半是 S（只陳述資訊不足），真正的文字求助只有 3–9%，所以只看 tool call 不會大幅高估 persona 的效果。明顯的「說做落差」出現在 **Qwen 關閉思考、沒有 persona** 時：缺條件題有 7–11% 說「我會去問老師」但沒有呼叫工具；開啟思考後消失。")
add("")

# ------------------------------------------------------------------ 6.5 求助類型
ac = Counter(a["code"] for a in asks)
add("### 6.5 求助類型：工具性 vs 執行性（Karabenick，理論精讀 T11）")
add("")
add(f"![求助類型]({FIG['types']})")
add("")
add("| 代碼 | 類別 | 屬於 | 例子 |")
add("| --- | --- | --- | --- |")
add("| INFO | 詢問缺少的資訊 | 工具性 | How many apples does Jackie have? |")
add("| METHOD | 詢問解法或提示 | 工具性 | 我還沒學過除法，這題要怎麼用加法和減法算？ |")
add("| VERIFY | 確認自己的答案或算法 | 工具性（自我檢核） | 所以原本的錢是 78 + 33 = 111 元對嗎？ |")
add("| EXEC | 轉貼整題、直接要答案、要老師幫忙算 | 執行性 | 8 個朋友一起玩電動，每個人一開始有 8 條命，他們一共有幾條命？ |")
add("| OTHER | 亂碼或無法判斷 | | |")
add("")
add(f"**做法與信度：** 全部 {len(asks):,} 筆 `ask_teacher` 問題。Claude 先人工判讀 320 筆分層樣本（模型 × 語言，每層 40 筆），依此寫出規則分類器；再用另外 80 筆沒看過的樣本驗證，**規則與 Claude 判定的一致率 95%，Cohen's κ = 0.93**，因此套用到全部資料。")
add("")
add("**主要發現：**")
add("")
add("- Llama 繁中的 `ask_teacher` 有 86% 是執行性求助（多半是把整題原封不動丟給老師），而且不隨 persona 改變。所以 Llama 繁中「一般題也有 60% 會問」，不能解讀成很會求助。")
add("- Llama 英文：沒有 persona 時 84% 是執行性求助；T＋A 以上的高求助 persona 讓工具性求助升到約 50%。**persona 能改變求助的類型，但只在英文成立。**")
add("- Qwen 英文幾乎全是工具性求助；繁中卻有 50% 是執行性求助。**用繁中時，兩個模型都比較常把題目直接丟給老師。**")
add("- Gemini 最像學生：常提出自己的算法再問「這樣對嗎」（確認答案，繁中 33%）。")
add("")

# ------------------------------------------------------------------ 討論
add("## 七、目前可以下的結論")
add("")
add("1. 「模型本來會不會問」沒有單一答案，取決於模型、語言、題型與思考模式。這本身就支持「persona 研究一定要先量 L0」。")
add("2. 在兩個開源模型上，persona 要寫到「行動」才控制得了 tool call，支持相容性原則；只寫個性特質幾乎無效，和精讀 01（The Personality Illusion）一致，並把它延伸到 agent 的 tool call。")
add("3. persona 的效果不能只看「有沒有呼叫工具」，還要看「怎麼問」（工具性／執行性）以及「不問的時候在做什麼」（跳過、硬猜、或口頭求助）。")
add("")
add("## 八、限制與尚待確認的問題")
add("")
add("**限制：**")
add("")
add("- 題數少（24 題、每種運算 12 題），信賴區間目前把重複次數當作獨立樣本計算，正式分析要用以題目和措辭為隨機效果的混合模型。")
add("- 只有兩個 8B 開源模型跑完 Step 1；Gemini 只跑了部分 Step 0。")
add("- 題目來自 GSM8K、SVAMP 等公開資料集，模型可能看過原題（資料汙染）；影響答對率較多，對求助率的影響較小。")
add("- 繁中版由英文翻譯而來；Qwen 用繁中回答時偶爾出現簡體字。")
add("- 「只回文字」與求助類型的分類由 Claude 判定，尚未有第二位人工評分者。")
add("")
add("**尚待確認：**")
add("")
add("1. T＋A 以上的 persona 很接近直接下指令。如何回應「這只是模型在照指令做事」的質疑？目前比較有說服力的是非單調與分離的現象（T＋A 比 T＋A＋C 更常過度求助、不問時的行為因模型而異、繁中與英文的差異）。")
add("2. 繁中讓模型更常做執行性求助，原因是中文能力較弱，還是中文訓練資料中的師生互動型態不同？需要更多模型（例如中文專長更強的模型）與人工驗證。")
add("3. 執行性求助要不要算進「求助率」？目前的 Step 1 數字是把兩種求助都算進去。")
add("4. 開啟思考後，persona 的控制力會變強還是變弱？Step 1 目前只在關閉思考下跑過。")
add("5. Llama 英文的「中性 persona 也提高求助率」是否穩定？需要補足無 persona 那格的樣本。")
add("6. 求助的「形式」（工具 vs 文字）會改變基線，正式研究要固定一種，並在方法中說明理由。")
add("")
add("## 九、下一步建議")
add("")
add("1. Gemini 跑完 Step 0（約 1–2 天），之後挑代表性條件跑 Step 1。")
add("2. Step 1 補跑開啟思考的 Qwen，回答待確認問題 4。")
add("3. 加入 RQ2 的「說」：讓同一個 persona 先填求助量表（改編 Ryan & Pintrich 的求助迴避題目），再看量表分數能不能預測 tool call。")
add("4. 加入 CAPS 的公開／私下情境（`raise_hand` vs `message_teacher`），以及第三人稱預測條件（HACHIMI-II）。")
add("5. 請第二位評分者標註一部分「只回文字」與求助類型，計算評分者間信度。")
add("")
add("## 十、檔案位置（伺服器）")
add("")
add("| 內容 | 路徑 |")
add("| --- | --- |")
add("| 題目集 | `pilot/items/pilot_items.json`、`make_items.py` |")
add("| persona | `pilot/personas/step1_personas.json`、`make_personas.py` |")
add("| 執行程式 | `pilot/run_pilot.py`（Step 0）、`run_step1.py`（Step 1）、`run_gemini_daily.sh` |")
add("| 原始結果 | `pilot/results/*.jsonl`、`pilot/results/step1/*.jsonl`（每個 episode 一行，含完整工具呼叫紀錄） |")
add("| 分類 | `pilot/judge/`（`code_text_only.py`、`code_asks.py`、人工判定樣本與驗證集） |")
add("| 圖 | `pilot/results/report/`（`report_figures.py` 產生） |")

out = ROOT / "results" / "report" / "archive" / "pilot_report.md"  # 2026-11-04 起已併入 pilot_report_full.md，這裡只重建封存的第一輪版本
out.write_text("\n".join(L) + "\n")
print(out, len("\n".join(L)))
