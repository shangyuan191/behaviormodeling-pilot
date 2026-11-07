"""CAPS 公開／私下實驗：把 ask_teacher 拆成 raise_hand（全班面前）與 ask_after_class（下課私下），
看不同 persona 在缺條件題上選擇公開還是私下求助（理論 3 的 H8）。

結果寫進 results/caps/<model>.jsonl，可中斷後接續。
"""
import argparse
import itertools
import json
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I 不會自動加入程式所在的資料夾
import run_pilot
from run_pilot import OpenAICompatible, run_episode

ROOT = Path(__file__).resolve().parent

CAPS_SYSTEM = {
    "en": ("You are a student doing math practice problems in class. You have these tools: "
           "raise_hand (ask the teacher in front of the whole class), ask_after_class (ask the teacher privately after class), "
           "submit_answer (submit your final answer), and skip (skip this problem). Use one tool per turn."),
    "zh": ("你是一個正在課堂上做數學練習題的學生。你可以使用以下工具："
           "raise_hand（在全班面前舉手問老師）、ask_after_class（下課後私下問老師）、"
           "submit_answer（提交最終答案）、skip（跳過這一題）。每一回合使用一個工具。"),
}

# (id, 類型, 繁中, English)
CAPS_PERSONAS = [
    ("C-L0", "none", "", ""),
    ("C-N1", "neutral", "你的生日在三月。", "Your birthday is in March."),
    ("C-TRAIT-1", "trait", "你個性害羞。", "You are shy."),
    ("C-TRAIT-2", "trait", "你個性內向。", "You are introverted."),
    ("C-PROC-1", "process", "你覺得在班上問問題代表自己不夠聰明，你最在意的是不要被同學看扁。",
     "You think asking questions in class means you're not smart enough, and what you care about most is not being looked down on by your classmates."),
    ("C-PROC-2", "process", "想到要在全班面前開口，你就會很緊張；你很怕同學覺得你很笨。",
     "Speaking up in front of the whole class makes you very nervous; you are afraid your classmates will think you are dumb."),
    ("C-IFTHEN-1", "ifthen", "在全班面前，你不敢問老師問題；但下課後，你會私下去問老師。",
     "In front of the whole class you don't dare to ask the teacher questions, but after class you go and ask the teacher privately."),
    ("C-IFTHEN-2", "ifthen", "你只在沒有其他同學看到的時候才會問老師問題。",
     "You only ask the teacher questions when no other classmates can see."),
    ("C-REVERSE", "reverse", "你喜歡在全班面前舉手發問，但不習慣下課後私下去問老師。",
     "You like raising your hand to ask questions in front of the class, but you are not used to asking the teacher privately after class."),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    run_pilot.ACTIVE_TOOLS.clear()
    run_pilot.ACTIVE_TOOLS.update({"raise_hand", "ask_after_class", "submit_answer", "skip"})
    items = json.loads((ROOT / "items" / "pilot_items.json").read_text())
    tag = args.model.split("/")[-1] + ("-nothink" if args.no_think else "")
    out = ROOT / "results" / "caps" / f"{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["key"] for l in out.open()} if out.exists() else set()

    jobs = [(p, it, lang, rep) for p, it, lang, rep in itertools.product(CAPS_PERSONAS, items, ["en", "zh"], range(args.reps))
            if f"{p[0]}|{it['id']}|missing|{lang}|{rep}" not in done]
    random.Random(0).shuffle(jobs)
    print(f"{len(jobs)} episodes to run ({len(done)} already done)", flush=True)

    extra = {"chat_template_kwargs": {"enable_thinking": False}} if args.no_think else {}
    backend = OpenAICompatible(args.model, args.base_url, extra)
    lock = threading.Lock()

    def work(job):
        (pid, ptype, zh, en), it, lang, rep = job
        persona = zh if lang == "zh" else en
        result = run_episode(backend, it, "missing", lang, "tool", persona, base=CAPS_SYSTEM)
        tools = [a["tool"] for a in result["actions"]]
        record = {"key": f"{pid}|{it['id']}|missing|{lang}|{rep}", "model": tag, "persona": pid, "ptype": ptype,
                  "item": it["id"], "op": it["op"], "need": "missing", "lang": lang, "rep": rep,
                  "public": "raise_hand" in tools, "private": "ask_after_class" in tools, **result}
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, jobs))
    print("finished", flush=True)


if __name__ == "__main__":
    main()
