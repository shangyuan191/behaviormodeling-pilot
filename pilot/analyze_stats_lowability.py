"""統計檢定（2026-11-14）：11/13 補跑「低求助 persona × 只學過加減」題。

用法：~/miniforge3/envs/adl_hw3_py311/bin/python -I analyze_stats_lowability.py > results/stats_lowability.txt

方法沿用 analyze_stats.py（persona 層次置換檢定＋Holm），但自成一個檢定家族，
不改動主報告既有的 p_Holm（那些數字仍以 analyze_stats.py 為準）。

(1) 求助率的階梯趨勢：乘除題（應問）與加減題（對照）分開，5 組設定 × 2 種語言 × 2 種題目 = 20 個檢定。
    預期：乘除題 ρ<0。加減題若也 ρ<0，代表 persona 是「全面少問」，不是只在該問的題目少問。
(2) 跳過率的階梯趨勢（最後動作是 skip）：只看乘除題，10 個檢定。預期 ρ>0 表示「不會又不問 → 跳過」。
(3) 是否分辨會與不會：在 TAC、TACT 兩層（6 個 persona），比較乘除題與加減題的跳過率差。
    置換方式：以題目為單位，打亂 24 題的乘除／加減標籤（所有 persona 一起打亂，保留同題重複之間的相關），
    20,000 次，雙尾。
    10 個檢定（5 組設定 × 2 種語言）。
三個部分合併做一次 Holm 校正（共 40 個檢定）。
"""
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_stats import LEVELS, MODELS, N_PERM, holm, level_of, load, trend_test  # noqa: E402

ROOT = Path(__file__).resolve().parent / "results"


def rows_for(tag):
    return [r for r in load(ROOT / "step1_extra" / f"{tag}-low-ability.jsonl") if level_of(r) in LEVELS]


def skip_diff_test(rows, rnd):
    """rows：同一模型×語言、TAC／TACT 層級的回答。回傳 (乘除跳過率, 加減跳過率, p)。"""
    unit = defaultdict(list)  # (persona, item) -> [skip...]
    op_of = {}
    for r in rows:
        unit[(r["persona"], r["item"])].append(r["final_action"] == "skip")
        op_of[r["item"]] = r["op"]
    personas = sorted({p for p, _ in unit})
    items = sorted(op_of)
    # 每個 persona × 題目的跳過率
    M = np.array([[np.mean(unit[(p, it)]) if (p, it) in unit else np.nan for it in items] for p in personas])
    is_md = np.array([op_of[it] == "muldiv" for it in items])

    def stat(mask):
        return np.nanmean(M[:, mask]) - np.nanmean(M[:, ~mask])
    obs = stat(is_md)
    nrng = np.random.default_rng(rnd.randrange(2**32))
    # 題目標籤在所有 persona 間一起打亂（題目是單位）
    perm = np.array([stat(nrng.permutation(is_md)) for _ in range(N_PERM)])
    p = (int((np.abs(perm) >= abs(obs) - 1e-12).sum()) + 1) / (N_PERM + 1)
    return float(np.nanmean(M[:, is_md])), float(np.nanmean(M[:, ~is_md])), p


def main():
    rnd = random.Random(0)
    tests = []
    for tag, name in MODELS:
        rows = rows_for(tag)
        if not rows:
            continue
        for lang in ("en", "zh"):
            for op, olabel in (("muldiv", "乘除（應問）"), ("addsub", "加減（對照）")):
                rs = [dict(r, _lv=level_of(r)) for r in rows if r["lang"] == lang and r["op"] == op]
                rho, p, orr, n = trend_test(rs, rnd)
                tests.append(dict(part=1, name=name, lang=lang, label=f"求助率｜{olabel}", rho=rho, orr=orr, p=p,
                                  expect=-1 if op == "muldiv" else 0))
            rs = [dict(r, _lv=level_of(r), asked=r["final_action"] == "skip") for r in rows
                  if r["lang"] == lang and r["op"] == "muldiv"]
            rho, p, orr, n = trend_test(rs, rnd)
            tests.append(dict(part=2, name=name, lang=lang, label="跳過率｜乘除", rho=rho, orr=orr, p=p, expect=1))
            rs = [r for r in rows if r["lang"] == lang and level_of(r) in ("TAC", "TACT")]
            md, asb, p = skip_diff_test(rs, rnd)
            tests.append(dict(part=3, name=name, lang=lang, label="TAC/TACT 跳過率：乘除 vs 加減",
                              md=md, asb=asb, p=p, expect=1))
    valid = [t for t in tests if not math.isnan(t["p"])]
    for t, a in zip(valid, holm([t["p"] for t in valid])):
        t["ph"] = a

    def star(ph):
        return "***" if ph < .001 else "**" if ph < .01 else "*" if ph < .05 else ""

    print("# 統計檢定：低求助 persona × 只學過加減（11/13 補跑）\n")
    print("方法同 analyze_stats.py：persona 層次置換檢定（20,000 次，雙尾）；本檔 40 個檢定自成一個 Holm 家族。")
    print("ρ＝層級（0–4）與 persona 比率的 Spearman 相關；OR＝每升一層的勝算比。\n")
    titles = {1: "## 1. 求助率的階梯趨勢（預期乘除題 ρ<0；加減題若也 ρ<0 ＝全面少問）",
              2: "## 2. 乘除題跳過率的階梯趨勢（預期 ρ>0：不會又不問 → 跳過）",
              3: "## 3. 分辨會與不會：TAC／TACT 層，乘除題跳過率 − 加減題跳過率（以題目為單位置換）"}
    for part in (1, 2, 3):
        print("\n" + titles[part])
        if part == 3:
            print("模型             語言 | 乘除跳過 | 加減跳過 |  差   |   p     | p_Holm  | 判讀")
        else:
            print("模型             語言 | 面板                 |   ρ    |   OR   |   p     | p_Holm  | 判讀")
        for t in tests:
            if t["part"] != part:
                continue
            if math.isnan(t["p"]):
                print(f"{t['name']:14s} {t['lang']}   | {t.get('label', ''):18s} | 全部相同，無法檢定")
                continue
            ph = t["ph"]
            if part == 3:
                d = t["md"] - t["asb"]
                v = ("乘除較常跳過" if d > 0 else "加減較常跳過") + star(ph) if ph < .05 else "不顯著"
                print(f"{t['name']:14s} {t['lang']}   | {t['md']:7.0%}  | {t['asb']:7.0%}  | {d:+.0%} | {t['p']:.4f}  | {ph:.4f}  | {v}")
            else:
                sign = "下降" if t["rho"] < 0 else "上升"
                v = f"顯著{sign}{star(ph)}" if ph < .05 else "不顯著"
                print(f"{t['name']:14s} {t['lang']}   | {t['label']:18s} | {t['rho']:+.2f}  | {t['orr']:6.2f} | {t['p']:.4f}  | {ph:.4f}  | {v}")
    print("\n註：每組只有 15 個 persona（第 3 部分為 6 個 persona × 24 題），檢定力有限；不顯著不代表沒有效果。")
    print("    L0 與中性對照不進入檢定（與 analyze_stats.py 相同）。")


if __name__ == "__main__":
    main()
