"""統計檢定（2026-11-03）：(1) persona 階梯的趨勢檢定；(2) 相容性原則（量表與行為在哪些層級一致）。

用法：~/miniforge3/envs/adl_hw3_py311/bin/python -I analyze_stats.py > results/stats_summary.txt
（這台機器的 base python 沒有 numpy；用 vLLM 環境裡的 numpy，不另外安裝套件）

(1) 階梯趨勢
  - 只用有層級的 persona：0、T、TA、TAC、TACT（各 3 種措辭，共 15 個 persona）。L0 與中性不進入檢定。
  - 統計量：Spearman ρ（層級序號 0–4 vs 每個 persona 的求助率，15 個點）。
  - p 值：persona 層次的置換檢定（打亂 15 個 persona 的層級標籤 20,000 次，雙尾）。
    操弄是在 persona 文字層次，所以把同一 persona 的所有回答視為一個單位，不假設回答彼此獨立。
  - 效果量：邏輯斯迴歸 asked ~ 層級序號 的斜率，換成「每升一層的勝算比」OR（>1 越問越多）。
  - 全部檢定一起做 Holm 校正。
(2) 相容性原則（設計稿 A：T＋A 以上的 persona，量表與行為比較一致）
  - 每個層級：Δ說＝迴避分數（AV−AD）相對於中性 persona 的變化；Δ做＝求助率相對於中性的變化。
  - 「一致」＝說與做往同一個方向變（迴避分數升高、求助率下降，或反之）。
  - 另外分「前段」（L0、中性、0、T）與「後段」（TA、TAC、TACT）各算 persona 層次的 Pearson r，
    但每段只有 9–10 個點且後段的行為變異較大，r 的差異也受全距限制影響，僅供參考。
"""
import json
import math
import random
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent / "results"
LEVELS = ["0", "T", "TA", "TAC", "TACT"]
ALL_LEVELS = ["L0", "neutral"] + LEVELS
MODELS = [("Qwen3-8B-FP8-nothink", "Qwen3 關閉思考"), ("Qwen3-8B-FP8", "Qwen3 開啟思考"),
          ("Llama-3.1-8B-Instruct", "Llama-3.1"), ("Qwen2.5-7B-Instruct", "Qwen2.5"),
          ("granite-3.3-8b-instruct", "Granite-3.3")]
PANELS = [("low", "missing", None, "低求助×缺條件"), ("high", "ability", "muldiv", "高求助×只學加減的乘除題"),
          ("high", "complete", None, "高求助×一般題")]
N_PERM = 20000


def load(p):
    return [json.loads(l) for l in open(p)] if p.exists() else []


def level_of(r):
    if r["persona"] == "L0":
        return "L0"
    if r["persona"].startswith("N"):
        return "neutral"
    return r.get("level") or r["persona"].split("-")[1]


def spearman(x, y):
    def rk(v):
        v = np.asarray(v, float)
        order = v.argsort()
        r = np.empty(len(v))
        i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
                j += 1
            r[order[i:j + 1]] = (i + j) / 2
            i = j + 1
        return r
    a, b = rk(x), rk(y)
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def logit_slope(x, y):
    """單一預測變數的邏輯斯迴歸（牛頓法），回傳斜率；完全分離時回傳 ±inf。"""
    X = np.column_stack([np.ones(len(x)), x]).astype(float)
    y = np.asarray(y, float)
    if y.min() == y.max():
        return float("nan")
    b = np.zeros(2)
    for _ in range(50):
        p = 1 / (1 + np.exp(-np.clip(X @ b, -30, 30)))
        g = X.T @ (y - p)
        H = X.T @ (X * (p * (1 - p))[:, None])
        try:
            step = np.linalg.solve(H + 1e-9 * np.eye(2), g)
        except np.linalg.LinAlgError:
            break
        b += step
        if abs(b[1]) > 20:
            return math.copysign(float("inf"), b[1])
        if np.abs(step).max() < 1e-8:
            break
    return float(b[1])


def trend_test(rows, rnd):
    """rows：同一模型×面板×語言、只含 0–TACT 層級的回答。"""
    by = defaultdict(list)
    for r in rows:
        by[r["persona"]].append(r["asked"])
    pids = sorted(by)
    lv = {}
    for r in rows:
        lv[r["persona"]] = LEVELS.index(r["_lv"])
    x = np.array([lv[p] for p in pids], float)
    y = np.array([np.mean(by[p]) for p in pids])
    rho = spearman(x, y)
    if math.isnan(rho):
        return rho, float("nan"), float("nan"), len(pids)
    # 置換：x 的排名在打亂後只是換位置，所以先算好排名，再用 numpy 一次算 20,000 個相關
    rx = np.argsort(np.argsort(x, kind="stable"), kind="stable").astype(float)
    for lvl in set(x):  # 同層級的平均排名
        rx[x == lvl] = rx[x == lvl].mean()
    ry = np.argsort(np.argsort(y, kind="stable"), kind="stable").astype(float)
    for v in set(y):
        ry[y == v] = ry[y == v].mean()
    nrng = np.random.default_rng(rnd.randrange(2**32))
    perms = np.array([nrng.permutation(rx) for _ in range(N_PERM)])
    pc = perms - perms.mean(1, keepdims=True)
    yc = ry - ry.mean()
    r_perm = (pc @ yc) / (np.sqrt((pc ** 2).sum(1)) * np.sqrt((yc ** 2).sum()))
    p = (int((np.abs(r_perm) >= abs(rho) - 1e-12).sum()) + 1) / (N_PERM + 1)
    slope = logit_slope([LEVELS.index(r["_lv"]) for r in rows], [r["asked"] for r in rows])
    return rho, p, math.exp(slope) if math.isfinite(slope) else (float("inf") if slope > 0 else 0.0), len(pids)


def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i])
    adj = [0.0] * len(ps)
    m = len(ps)
    run = 0.0
    for k, i in enumerate(idx):
        run = max(run, min(1.0, (m - k) * ps[i]))
        adj[i] = run
    return adj


def part1():
    print("# 統計檢定摘要\n\n## 1. persona 階梯的趨勢檢定（0 → T → TA → TAC → TACT）")
    print("ρ＝層級與 persona 求助率的 Spearman 相關（15 個 persona）；OR＝每升一層的勝算比；")
    print("p＝persona 層次置換檢定（雙尾，20,000 次）；p_Holm＝全部檢定一起做 Holm 校正。")
    print("預期方向：低求助 ρ<0（OR<1），高求助 ρ>0（OR>1）。\n")
    rnd = random.Random(0)
    out = []
    for persp, sub, suf in (("第一人稱", "step1", ""), ("第三人稱", "step1_third", "-third")):
        for tag, name in MODELS:
            for direction, need, op, ptitle in PANELS:
                rows = load(ROOT / sub / f"{tag}-{direction}{suf}.jsonl")
                if not rows:
                    continue
                for lang in ("en", "zh"):
                    rs = []
                    for r in rows:
                        lvl = level_of(r)
                        if (lvl in LEVELS and r["persona"][0] == direction[0].upper() and r["need"] == need
                                and (op is None or r["op"] == op) and r["lang"] == lang):
                            rs.append(dict(r, _lv=lvl))
                    if not rs:
                        continue
                    rho, p, orr, n = trend_test(rs, rnd)
                    expect = -1 if direction == "low" else 1
                    out.append(dict(persp=persp, name=name, panel=ptitle, lang=lang, rho=rho, p=p, orr=orr,
                                    n=n, N=len(rs), ok=(not math.isnan(rho)) and rho * expect > 0))
    valid = [o for o in out if not math.isnan(o["p"])]
    for o, a in zip(valid, holm([o["p"] for o in valid])):
        o["ph"] = a
    cur = None
    for o in out:
        if (o["persp"], o["name"]) != cur:
            cur = (o["persp"], o["name"])
            print(f"\n### {o['persp']}｜{o['name']}")
            print("面板                      語言 |   ρ    |   OR   |   p     | p_Holm  | 判讀")
        if math.isnan(o["rho"]):
            print(f"{o['panel']:22s} {o['lang']}   |   —    |   —    |   —     |   —     | 全部相同，無法檢定")
            continue
        star = "***" if o["ph"] < .001 else "**" if o["ph"] < .01 else "*" if o["ph"] < .05 else ""
        verdict = ("符合預期" if o["ok"] else "方向相反") + star if o["ph"] < .05 else "不顯著"
        print(f"{o['panel']:22s} {o['lang']}   | {o['rho']:+.2f}  | {o['orr']:6.2f} | {o['p']:.4f}  | {o['ph']:.4f}  | {verdict}")
    sig = sum(o.get("ph", 1) < .05 and o["ok"] for o in out)
    print(f"\n共 {len(out)} 個檢定，{sig} 個在 Holm 校正後顯著且方向符合預期。")
    print("註：每組只有 15 個 persona，置換檢定的最小可能 p 約 1/20001，但檢定力有限；")
    print("    高求助面板若基線已接近 100%（如 Qwen2.5 英文、Granite），沒有上升空間，不顯著不代表 persona 無效。")


def part2():
    print("\n\n## 2. 相容性原則：說（量表）與做（行為）在哪些層級一致")
    print("Δ說＝迴避分數（AV−AD）減中性 persona；Δ做＝求助率減中性 persona（百分點）。")
    print("一致＝兩者反向變化（越說迴避、越少問）；✓＝一致，✗＝不一致，·＝變化太小（|Δ說|<0.5 或 |Δ做|<10 點）。\n")
    for tag, name in MODELS:
        sv = load(ROOT / "survey" / f"{tag}.jsonl")
        if not sv:
            continue
        sc = defaultdict(lambda: defaultdict(list))
        for r in sv:
            if r["score"] is not None:
                sc[(r["persona"], r["lang"])][r["scale"]].append(r["score"])
        m = lambda v: sum(v) / len(v) if v else float("nan")
        avoid = {k: m(v["avoid"]) - m(v["adaptive"]) for k, v in sc.items()}
        print(f"### {name}")
        for direction, need, op, ptitle in PANELS[:2]:
            rows = load(ROOT / "step1" / f"{tag}-{direction}.jsonl")
            for lang in ("en", "zh"):
                pts = {}
                for r in rows:
                    if r["lang"] != lang or r["need"] != need or (op and r["op"] != op):
                        continue
                    lvl = level_of(r)
                    if lvl in LEVELS and r["persona"][0] != direction[0].upper():
                        continue
                    pts.setdefault(r["persona"], [lvl, []])[1].append(r["asked"])
                lv_say, lv_do = defaultdict(list), defaultdict(list)
                xy = []
                for pid, (lvl, a) in pts.items():
                    if (pid, lang) not in avoid or math.isnan(avoid[(pid, lang)]):
                        continue
                    lv_say[lvl].append(avoid[(pid, lang)])
                    lv_do[lvl].append(sum(a) / len(a))
                    xy.append((lvl, avoid[(pid, lang)], sum(a) / len(a)))
                if not lv_say.get("neutral"):
                    continue
                s0, d0 = m(lv_say["neutral"]), m(lv_do["neutral"])
                cells = []
                for lvl in ["L0"] + LEVELS:
                    if not lv_say.get(lvl):
                        cells.append("   —    ")
                        continue
                    ds, dd = m(lv_say[lvl]) - s0, (m(lv_do[lvl]) - d0) * 100
                    mark = "·" if abs(ds) < .5 or abs(dd) < 10 else ("✓" if ds * dd < 0 else "✗")
                    cells.append(f"{ds:+.1f}/{dd:+3.0f}{mark}")

                def pr(grp):
                    pts_ = [(a, b) for l, a, b in xy if l in grp]
                    if len(pts_) < 4:
                        return float("nan"), len(pts_)
                    a, b = np.array(pts_).T
                    if a.std() == 0 or b.std() == 0:
                        return float("nan"), len(pts_)
                    return float(np.corrcoef(a, b)[0, 1]), len(pts_)
                r1, n1 = pr({"L0", "neutral", "0", "T"})
                r2, n2 = pr({"TA", "TAC", "TACT"})
                if lang == "en":
                    print(f"  {ptitle}（每格：Δ說/Δ做）")
                    print("    語言 |   " + "   |   ".join(f"{l:^6s}" for l in ["L0"] + LEVELS) + "   | 前段 r (n) | 後段 r (n)")
                print(f"    {lang}   | " + " | ".join(cells) + f" | {r1:+.2f} ({n1:2d})  | {r2:+.2f} ({n2:2d})")
        print()


if __name__ == "__main__":
    part1()
    part2()
