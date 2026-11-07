"""第二輪分析（2026-11-02）：開啟思考的 Step 1、第三人稱、量表（說 vs 做）、CAPS、Breeze2。

用法：~/miniforge3/bin/python3 -I analyze_round2.py > results/round2_summary.txt
所有比例都附 Wilson 95% 信賴區間的半寬（±）。
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "results"
LEVELS = ["L0", "neutral", "0", "T", "TA", "TAC", "TACT"]
PANELS = [("low", "missing", None, "低求助｜缺條件題"),
          ("high", "ability", "muldiv", "高求助｜只學過加減・乘除題"),
          ("high", "complete", None, "高求助｜一般題")]


def load(path):
    return [json.loads(l) for l in open(path)] if path.exists() else []


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def rate(rs, key="asked"):
    n, k = len(rs), sum(bool(r[key]) for r in rs)
    if not n:
        return "  —  "
    lo, hi = wilson(k, n)
    return f"{k / n:4.0%}±{(hi - lo) / 2 * 100:2.0f}"


def level_of(r):
    lv = r.get("level")
    if lv is None:
        lv = "L0" if r["persona"] == "L0" else "neutral" if r["persona"].startswith("N") else r["persona"].split("-")[1]
    return "neutral" if r["persona"].startswith("N") else lv


def panel_rows(rows, direction, need, op):
    return [r for r in rows if r["need"] == need and (op is None or r["op"] == op)
            and (r["persona"] in ("L0",) or r["persona"].startswith("N") or r["persona"][0] == direction[0].upper())]


def step1(tag, perspective="first"):
    d = ROOT / ("step1" if perspective == "first" else "step1_third")
    suf = "" if perspective == "first" else "-third"
    return {dr: load(d / f"{tag}-{dr}{suf}.jsonl") for dr in ("high", "low")}


def ladder(title, data, extra=None):
    print(f"\n### {title}")
    print("面板                         語言 | " + " | ".join(f"{l:^8s}" for l in LEVELS))
    for direction, need, op, ptitle in PANELS:
        rows = panel_rows(data[direction], direction, need, op)
        for lang in ("en", "zh"):
            cells = [rate([r for r in rows if r["lang"] == lang and level_of(r) == lv]) for lv in LEVELS]
            print(f"{ptitle:24s} {lang} | " + " | ".join(f"{c:^8s}" for c in cells))
    if extra:
        extra(data)


def say_do_gap(data):  # 「說要問卻沒呼叫工具」：最後是純文字回覆的比例（缺條件題）
    rows = panel_rows(data["low"], "low", "missing", None)
    for lang in ("en", "zh"):
        rs = [dict(r, _text=r["final_action"] == "text") for r in rows if r["lang"] == lang]
        cells = [rate([r for r in rs if level_of(r) == lv], key="_text") for lv in LEVELS]
        print(f"{'  └ 缺條件題：最後只回文字':22s} {lang} | " + " | ".join(f"{c:^8s}" for c in cells))


def ability_correct(data):  # 能力外洩：只學過加減的乘除題，答對率（越高越外洩）
    rows = panel_rows(data["high"], "high", "ability", "muldiv")
    for lang in ("en", "zh"):
        cells = [rate([r for r in rows if r["lang"] == lang and level_of(r) == lv], key="correct") for lv in LEVELS]
        print(f"{'  └ 乘除題答對率（能力外洩）':20s} {lang} | " + " | ".join(f"{c:^8s}" for c in cells))


def both_extras(data):
    say_do_gap(data)
    ability_correct(data)


# ---------------------------------------------------------------- 量表

def pearson(x, y):
    n = len(x)
    if n < 3:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else float("nan")


def ranks(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2
        i = j + 1
    return r


def spearman(x, y):
    return pearson(ranks(x), ranks(y))


def survey(tag, step1_tag):
    rows = load(ROOT / "survey" / f"{tag}.jsonl")
    if not rows:
        return
    s1 = step1(step1_tag)
    print(f"\n### 量表：{tag}（行為對照 Step 1 的 {step1_tag}）")
    # persona × lang 的各量表平均
    sc = defaultdict(lambda: defaultdict(list))
    bad = defaultdict(int)
    for r in rows:
        if r["score"] is None:  # 回覆不是 1–7 的數字
            bad[r["lang"]] += 1
            continue
        sc[(r["persona"], r["lang"])][r["scale"]].append(r["score"])
    for lang in ("en", "zh"):
        n = sum(r["lang"] == lang for r in rows)
        print(f"  無法解析的回覆 {lang}: {bad[lang]}/{n}")
    mean = lambda v: sum(v) / len(v) if v else float("nan")
    avoid = {k: mean(v["avoid"]) - mean(v["adaptive"]) for k, v in sc.items()}  # 越高越迴避
    # 依方向 × 層級列出迴避分數
    print("方向 語言 | " + " | ".join(f"{l:^7s}" for l in LEVELS) + "   （AV−AD，範圍 −6～+6，越高越迴避）")
    for dr in ("low", "high"):
        for lang in ("en", "zh"):
            cells = []
            for lv in LEVELS:
                ks = [k for k in avoid if k[1] == lang and (
                    (lv == "L0" and k[0] == "L0") or (lv == "neutral" and k[0].startswith("N")) or
                    ("-" in k[0] and k[0][0] == dr[0].upper() and k[0].split("-")[1] == lv))]
                cells.append(f"{mean([avoid[k] for k in ks]):+5.1f}" if ks else "  —  ")
            print(f"{dr:4s} {lang}   | " + " | ".join(f"{c:^7s}" for c in cells))
    # 說 vs 做：每個 persona 的迴避分數 vs 它在主要面板的實際求助率
    print("說 vs 做（每個 persona 一個點；r＝Pearson，ρ＝Spearman；預期為負：越迴避越少問）")
    for dr, need, op, ptitle in PANELS[:2]:
        prow = panel_rows(s1[dr], dr, need, op)
        for lang in ("en", "zh"):
            xs, ys = [], []
            for (p, lg), a in avoid.items():
                if lg != lang:
                    continue
                if not (p == "L0" or p.startswith("N") or p[0] == dr[0].upper()):
                    continue
                rs = [r for r in prow if r["persona"] == p and r["lang"] == lang]
                if rs:
                    xs.append(a); ys.append(sum(r["asked"] for r in rs) / len(rs))
            print(f"  {ptitle:22s} {lang}: n={len(xs):2d}  r={pearson(xs, ys):+.2f}  ρ={spearman(xs, ys):+.2f}")
    # 其他量表在 L0 的基線（模型本身的「自我報告」）
    base = {lang: {s: mean(sc[("L0", lang)][s]) for s in ("avoid", "adaptive", "threat_teacher", "threat_peer", "benefit")}
            for lang in ("en", "zh")}
    for lang in ("en", "zh"):
        print(f"  L0 基線 {lang}: " + "  ".join(f"{s}={v:.1f}" for s, v in base[lang].items()))


# ---------------------------------------------------------------- CAPS

def caps(tag):
    rows = load(ROOT / "caps" / f"{tag}.jsonl")
    if not rows:
        return
    print(f"\n### CAPS 公開／私下：{tag}（缺條件題）")
    print("persona 類型 語言 |  有求助   |  公開占比  | 舉手  | 下課問 | 跳過  | 只回文字")
    for pt in ("none", "neutral", "trait", "process", "ifthen", "reverse"):
        for lang in ("en", "zh"):
            rs = [r for r in rows if r["ptype"] == pt and r["lang"] == lang]
            asked = [r for r in rs if r["public"] or r["private"]]
            pub = [dict(r, _p=r["public"] and not r["private"]) for r in asked]
            ff = lambda a: f"{sum(r['first_action'] == a for r in rs) / len(rs):4.0%}"
            print(f"{pt:9s} {lang}     | {rate([dict(r, _a=bool(r['public'] or r['private'])) for r in rs], '_a'):^9s} | "
                  f"{rate(pub, '_p'):^9s} | {ff('raise_hand'):5s} | {ff('ask_after_class'):6s} | {ff('skip'):5s} | {ff('text')}")


def caps_recoded(tag):
    """把「只回文字」的回覆依 code_caps_text.py 的編碼併回去（11/3）。
    嚴格＝說要問老師（公開／私下／沒說管道／猶豫管道）；寬鬆＝再加上直接向對話對象要資訊。
    公開占比只用管道明確的回合（公開 vs 私下）。"""
    rows = load(ROOT / "caps" / f"{tag}.jsonl")
    codes = {c["key"]: c["code"] for c in load(ROOT / "caps_coded" / f"{tag}.jsonl")}
    if not rows or not codes:
        return
    def chan(r):
        if r["first_action"] != "text":
            return "public" if r["public"] and not r["private"] else "private" if r["private"] else r["first_action"]
        return codes.get(r["key"], "other")
    print(f"\n### CAPS 編碼後：{tag}（只回文字的回覆依內容歸類）")
    print("persona 類型 語言 | 嚴格求助  | 寬鬆求助  | 公開占比  | 公開 私下 沒說管道 猶豫 要資訊 只說缺 跳過 其他")
    for pt in ("none", "neutral", "trait", "process", "ifthen", "reverse"):
        for lang in ("en", "zh"):
            rs = [dict(r, _c=chan(r)) for r in rows if r["ptype"] == pt and r["lang"] == lang]
            strict = [dict(r, _a=r["_c"] in ("public", "private", "ask_teacher", "undecided")) for r in rs]
            loose = [dict(r, _a=r["_c"] in ("public", "private", "ask_teacher", "undecided", "request_info")) for r in rs]
            known = [dict(r, _p=r["_c"] == "public") for r in rs if r["_c"] in ("public", "private")]
            n = len(rs)
            cnt = lambda *ks: f"{sum(r['_c'] in ks for r in rs) / n:4.0%}"
            print(f"{pt:9s} {lang}     | {rate(strict, '_a'):^9s} | {rate(loose, '_a'):^9s} | {rate(known, '_p'):^9s} | "
                  f"{cnt('public')} {cnt('private')} {cnt('ask_teacher')}     {cnt('undecided')} {cnt('request_info')}   "
                  f"{cnt('state_missing')}   {cnt('skip')} {cnt('other', 'answer', 'submit_answer')}")


# ---------------------------------------------------------------- Step 0（Breeze2）

def step0(tag):
    rows = load(ROOT / f"{tag}.jsonl")
    if not rows:
        return
    print(f"\n### Step 0：{tag}（無 persona）")
    print("語言 題型   需求     | 求助率    | 第一步分布")
    for lang in ("en", "zh"):
        for op in ("addsub", "muldiv"):
            for need in ("complete", "missing", "ability"):
                rs = [r for r in rows if r["lang"] == lang and r["op"] == op and r["need"] == need]
                if not rs:
                    continue
                dist = defaultdict(int)
                for r in rs:
                    dist[r["first_action"]] += 1
                print(f"{lang}   {op:6s} {need:8s} | {rate(rs):9s} | " +
                      " ".join(f"{a}={c}" for a, c in sorted(dist.items(), key=lambda x: -x[1])))
    txt = [r for r in rows if r["first_action"] == "text"]
    print(f"  第一步不是工具呼叫的比例：{len(txt) / len(rows):.0%}（{len(txt)}/{len(rows)}）")


def main():
    print("# 第二輪分析摘要\n\n## 1. Step 1 階梯（第一人稱）")
    for tag, title in [("Qwen3-8B-FP8-nothink", "Qwen3-8B 關閉思考"), ("Qwen3-8B-FP8", "Qwen3-8B 開啟思考"),
                       ("Llama-3.1-8B-Instruct", "Llama-3.1-8B"), ("Llama-Breeze2-8B-Instruct", "Breeze2-8B"),
                       ("Qwen2.5-7B-Instruct", "Qwen2.5-7B"), ("granite-3.3-8b-instruct", "Granite-3.3-8B")]:
        d = step1(tag)
        if d["low"] or d["high"]:
            ladder(title, d, both_extras)
    print("\n## 2. 第三人稱預測（與第一人稱並列）")
    for tag, title in [("Qwen3-8B-FP8-nothink", "Qwen3-8B 關閉思考"), ("Qwen3-8B-FP8", "Qwen3-8B 開啟思考"), ("Llama-3.1-8B-Instruct", "Llama-3.1-8B"),
                       ("Llama-Breeze2-8B-Instruct", "Breeze2-8B"), ("Qwen2.5-7B-Instruct", "Qwen2.5-7B"), ("granite-3.3-8b-instruct", "Granite-3.3-8B")]:
        d3 = step1(tag, "third")
        if d3["low"] or d3["high"]:
            ladder(f"{title}｜第三人稱", d3, ability_correct)
    print("\n## 3. 量表：說 vs 做")
    survey("Qwen3-8B-FP8-nothink", "Qwen3-8B-FP8-nothink")
    survey("Qwen3-8B-FP8", "Qwen3-8B-FP8")
    for t in ("Llama-3.1-8B-Instruct", "Llama-Breeze2-8B-Instruct", "Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct"):
        survey(t, t)
    print("\n## 4. CAPS")
    caps("Qwen3-8B-FP8-nothink")
    caps("Qwen3-8B-FP8")
    for t in ("Llama-3.1-8B-Instruct", "Llama-Breeze2-8B-Instruct", "Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct"):
        caps(t)
    for t in ("Qwen3-8B-FP8-nothink", "Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct"):
        caps_recoded(t)
    print("\n## 5. Step 0")
    for tag in ("Qwen3-8B-FP8-nothink", "Llama-3.1-8B-Instruct", "Llama-Breeze2-8B-Instruct", "Qwen2.5-7B-Instruct", "granite-3.3-8b-instruct"):
        step0(tag)


if __name__ == "__main__":
    main()
