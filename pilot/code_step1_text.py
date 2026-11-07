"""Step 1「只回文字」回覆的編碼：工具名稱檢查用（2026-11-07）。

問題：把 ask_teacher 改名成 ask_for_help／raise_hand 後，Qwen3 關閉思考第一步只回文字的比例上升
（繁中 32% → 52–56%），工具呼叫率可能低估了求助。這裡用和 code_caps_text.py 相同的關鍵字規則，
把三種工具名稱（含原版 ask_teacher）的文字回覆都編碼，讓三者可以公平比較。

類別（優先順序由上而下，先符合者勝）：
  tool_in_text  文字裡寫出工具名稱（格式錯誤的工具呼叫），依名稱歸到 help/skip/answer
  intent        文字說要求助：問老師／舉手／下課問／「I will ask for help」「我請求協助」（含猶豫「可以問老師嗎？」）
  skip          說要跳過
  request_info  直接向對話對象要缺少的資訊（「能告訴我…嗎？」），沒提老師
  answer        自己假設數字或給出答案
  state_missing 只陳述題目缺資訊，沒有向任何人要、也沒說要做什麼
  other         以上皆非
求助的三種算法：
  嚴格＝呼叫求助工具（原本的數字）
  ＋說求助＝嚴格 ＋ 文字說要求助（intent，含 tool_in_text 的求助工具）
  寬鬆＝＋說求助 ＋ request_info（直接要資訊）
輸出：results/step1_toolname_coded/<模型>-<工具>.jsonl、review_sample.csv；摘要印到 stdout。
用法：~/miniforge3/bin/python3 -I code_step1_text.py > results/toolname_text_summary.txt
"""
import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

from analyze_toolname import COLS, LEVELS, col_of, load, trend

ROOT = Path(__file__).resolve().parent / "results"
MODELS = [("Qwen3-8B-FP8-nothink", "Qwen3 關閉思考"), ("Llama-3.1-8B-Instruct", "Llama-3.1")]
TOOLS = [("ask_teacher", "ask_teacher（原版）"), ("ask_for_help", "ask_for_help（不提老師）"),
         ("raise_hand_neutral", "raise_hand（中性說明）")]

NAMES = r"(ask_teacher|ask_for_help|raise_hand|submit_answer|skip)"
CALL_RE = re.compile(r'"name"\s*:\s*"' + NAMES + '"|\\b' + NAMES + r"\s*\(")
TOOL_RE = re.compile(r"\b" + NAMES + r"\b")
TOOL_MAP = {"ask_teacher": "help", "ask_for_help": "help", "raise_hand": "help", "submit_answer": "answer", "skip": "skip"}
RULES = [
    ("intent", r"(ask|request|seek)( for)? (help|assistance|clarification)|i need help|need (your )?help"
               r"|請老師|请老师|老師幫|老师帮|請求協助|请求协助|尋求協助|寻求协助|需要幫助|需要帮助|需要協助|需要协助"
               r"|ask (the|my|a|your) teacher|teacher for (clarification|help|more)|with (the|my) teacher|consult (the|my) teacher"
                r"|raise (my|your|a|the)? ?hand|raising (my )?hand|after class|my teacher"
                r"|問老師|问老师|請教老師|请教老师|詢問老師|询问老师|向老師|向老师|找老師|找老师|舉手|举手|下課|課後|课后"),
    ("skip", r"\bskip\b|跳過|跳过|略過|略过|先不做|move on"),
    ("request_info", r"\?|？|please (provide|tell|let me know|specify|clarify)|could you|can you|請告訴|请告诉|請提供|请提供"
                     r"|請問|请问|請說明|请说明|告訴我|告诉我"),
    ("answer", r"answer is|assum|let'?s say|答案是|答案為|假設|假设|\\boxed"),
    ("state_missing", r"not enough|insufficient|missing|need (more|to know)|does not (provide|specify|give|mention)"
                      r"|doesn'?t (provide|specify|mention)|without (this|that|additional|more)|not possible"
                      r"|cannot determine|can'?t determine|不足|不夠|不够|缺少|需要更多|需要知道|沒有提供|没有提供"
                      r"|沒有給|没有给|無法|无法|不知道|並未|并未|未提供"),
]


def code(text):
    t = text.lower()
    m = CALL_RE.search(t) or TOOL_RE.search(t)
    if m:
        name = next(g for g in m.groups() if g)
        return "tool_in_text", TOOL_MAP[name], m.group(0)
    for name, pat in RULES:
        m = re.search(pat, t)
        if m:
            return name, name, m.group(0)
    return "other", "other", ""


def path_of(tag, tool):
    return (ROOT / "step1" / f"{tag}-low.jsonl" if tool == "ask_teacher"
            else ROOT / "step1_toolname" / f"{tag}-low-{tool}.jsonl")


def first_text(r):
    return next((a["text"] for a in r["actions"] if a.get("text")), "") if r["first_action"] == "text" else ""


def pct(rs, key):
    return f"{sum(r[key] for r in rs) / len(rs):4.0%}" if rs else "  — "


def main():
    out_dir = ROOT / "step1_toolname_coded"
    out_dir.mkdir(exist_ok=True)
    sample, rnd = [], random.Random(0)
    print("# 工具名稱檢查：「只回文字」回覆的編碼（低求助階梯 × 缺條件題，第一人稱）\n")
    print("嚴格＝呼叫求助工具；＋說求助＝再加上文字說要求助（問老師、舉手、ask for help、請求協助，或寫出求助工具名稱）；")
    print("寬鬆＝再加上直接向對話對象要缺少的資訊。ρ、p 同 analyze_toolname.py（persona 層次置換，未校正）。\n")
    for tag, mname in MODELS:
        print(f"## {mname}\n")
        for tool, tname in TOOLS:
            rows = [r for r in load(path_of(tag, tool)) if r["need"] == "missing"]
            if not rows:
                continue
            coded = []
            for r in rows:
                txt = first_text(r)
                c = code(txt)[1] if txt else None
                r["_code"] = c
                r["_strict"] = r["asked"]
                r["_intent"] = r["asked"] or c in ("help", "intent")
                r["_broad"] = r["_intent"] or c == "request_info"
                if txt:
                    coded.append({"key": r["key"], "model": tag, "help_tool": tool, "lang": r["lang"],
                                  "level": col_of(r), "rule": code(txt)[0], "code": c, "hit": code(txt)[2], "text": txt})
            with open(out_dir / f"{tag}-{tool}.jsonl", "w") as f:
                for c in coded:
                    f.write(json.dumps(c, ensure_ascii=False) + "\n")
            by = {}
            for c in coded:
                by.setdefault((c["lang"], c["code"]), []).append(c)
            for v in by.values():
                sample += rnd.sample(v, min(3, len(v)))
            print(f"### {tname}")
            for lang in ("en", "zh"):
                rl = [r for r in rows if r["lang"] == lang]
                txt = [r for r in rl if r["_code"]]
                dist = Counter(r["_code"] for r in txt)
                print(f"{lang}：只回文字 {len(txt)}/{len(rl)}（{len(txt) / len(rl):.0%}）→ "
                      + "、".join(f"{k} {v}" for k, v in dist.most_common()))
            print(f"\n{'算法':6s} 語言 | " + " | ".join(f"{c:^7s}" for c in COLS) + " |   ρ   |   p")
            for key, lab in (("_strict", "嚴格"), ("_intent", "＋說求助"), ("_broad", "寬鬆")):
                for lang in ("en", "zh"):
                    rl = [r for r in rows if r["lang"] == lang]
                    cells = [pct([r for r in rl if col_of(r) == c], key) for c in COLS]
                    t = trend([dict(r, asked=r[key]) for r in rows], lang)
                    print(f"{lab:6s} {lang}   | " + " | ".join(f"{c:^7s}" for c in cells)
                          + (f" | {t[0]:+.2f} | {t[1]:.4f}" if t else " |  —   |  —"))
            print()
    with open(out_dir / "review_sample.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "help_tool", "key", "lang", "level", "code", "hit", "human_code", "text"])
        for c in sample:
            w.writerow([c["model"], c["help_tool"], c["key"], c["lang"], c["level"], c["code"], c["hit"], "", c["text"]])
    print(f"人工檢查樣本：{len(sample)} 則 → results/step1_toolname_coded/review_sample.csv")


if __name__ == "__main__":
    main()
