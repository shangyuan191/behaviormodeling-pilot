"""Step 1：TACT persona 階梯對求助行為的影響（本機 vLLM 模型）。

--direction high：L0、中性對照、高求助階梯 × 一般題與「只學過加減」題
--direction low ：L0、中性對照、低求助階梯 × 缺條件題
--perspective third：第三人稱預測（HACHIMI-II）：系統提示改成「預測這位學生會怎麼做」，persona 用 designs/third_person.json
persona 放在系統提示中，位於工具說明之後、「只學過加減」之前。

結果寫進 results/step1/<model>-<direction>.jsonl，可中斷後接續；用多執行緒同時送出請求以加快速度。
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

# --help-tool（11/4 工具名稱穩健性檢查）：把 ask_teacher 換成別的名稱／說明，其餘提示與 persona 不變。
# ask_for_help 不提老師；raise_hand 用中性說明（不提「全班都會聽到」，和 CAPS 版不同）。
HELP_TOOLS = {
    "ask_teacher": None,
    "ask_for_help": {"desc": {"en": "Ask for help with this problem.", "zh": "請求協助解這一題。"},
                     "sys": {"en": "ask_for_help (ask for help)", "zh": "ask_for_help（請求協助）"}},
    "raise_hand_neutral": {"name": "raise_hand",
                           "desc": {"en": "Raise your hand to ask the teacher a question.", "zh": "舉手問老師問題。"},
                           "sys": {"en": "raise_hand (raise your hand to ask the teacher)", "zh": "raise_hand（舉手問老師）"}},
}

THIRD_BASE = {
    "en": ("You will predict what a student does next in math practice. Here is a description of the student: {persona} "
           "Use the tools to show what this student would do: ask_teacher (the student sends a question to the teacher), "
           "submit_answer (the student submits a final answer), or skip (the student skips the problem). Use one tool per turn."),
    "zh": ("你要預測一位學生在數學練習中的下一步。這位學生的描述如下：{persona}"
           "請用工具表示這位學生會做的事：ask_teacher（學生傳送問題給老師）、submit_answer（學生提交最終答案）、"
           "skip（學生跳過這一題）。每一回合使用一個工具。"),
}
THIRD_ABILITY = {
    "en": "This student has only learned addition and subtraction, and has not learned multiplication or division yet.",
    "zh": "這位學生只學過加法和減法，還沒有學過乘法和除法。",
}
THIRD_NONE = {"en": "(no description)", "zh": "（沒有描述）"}

ROOT = Path(__file__).resolve().parent
NEEDS = {"high": ["complete", "ability"], "low": ["missing"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--direction", choices=["high", "low"], required=True)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--perspective", choices=["first", "third"], default="first")
    ap.add_argument("--help-tool", choices=list(HELP_TOOLS), default="ask_teacher")
    ap.add_argument("--personas", help="只跑這些 persona id（逗號分隔），例如補 L0 的樣本")
    ap.add_argument("--rep-start", type=int, default=0, help="rep 編號從這裡開始（補樣本時避免和既有 key 重複）")
    ap.add_argument("--out", help="覆寫輸出檔路徑")
    args = ap.parse_args()

    first_base = None
    ht = HELP_TOOLS[args.help_tool]
    if ht:
        assert args.perspective == "first", "工具名稱檢查只做第一人稱"
        name = ht.get("name", args.help_tool)
        run_pilot.TOOLS[:] = [t for t in run_pilot.TOOLS if t["name"] != name] + [
            {"name": name, "description": ht["desc"],
             "param": ("question", {"en": "Your question.", "zh": "你的問題。"})}]
        run_pilot.ACTIVE_TOOLS.clear()
        run_pilot.ACTIVE_TOOLS.update({name, "submit_answer", "skip"})
        run_pilot.ASK_TOOLS.add(name)
        old = {"en": "ask_teacher (send a question to your teacher)", "zh": "ask_teacher（傳送問題給老師）"}
        first_base = {}
        for lang in ("en", "zh"):
            assert run_pilot.SYSTEM[lang].count(old[lang]) == 1
            first_base[lang] = run_pilot.SYSTEM[lang].replace(old[lang], ht["sys"][lang])

    items = json.loads((ROOT / "items" / "pilot_items.json").read_text())
    personas = [p for p in json.loads((ROOT / "personas" / "step1_personas.json").read_text())
                if p["direction"] in ("none", "neutral", args.direction)]
    if args.personas:
        keep = set(args.personas.split(","))
        personas = [p for p in personas if p["id"] in keep]
        assert personas, "找不到指定的 persona"
    if args.perspective == "third":  # 換成第三人稱的 persona 文字（編號與層級不變）
        third = {p["id"]: p for p in json.loads((ROOT / "designs" / "third_person.json").read_text())}
        for p in personas:
            p["zh"], p["en"] = third[p["id"]]["zh"], third[p["id"]]["en"]
    tag = args.model.split("/")[-1] + ("-nothink" if args.no_think else "")
    suffix = "-third" if args.perspective == "third" else ""
    out = ROOT / "results" / ("step1_third" if args.perspective == "third" else "step1") / f"{tag}-{args.direction}{suffix}.jsonl"
    if ht:
        out = ROOT / "results" / "step1_toolname" / f"{tag}-{args.direction}-{args.help_tool}.jsonl"
    if args.out:
        out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["key"] for l in out.open()} if out.exists() else set()

    jobs = [(p, it, need, lang, rep) for p, it, need, lang, rep in itertools.product(
        personas, items, NEEDS[args.direction], ["en", "zh"], range(args.rep_start, args.reps))
        if f"{p['id']}|{it['id']}|{need}|{lang}|{rep}" not in done]
    random.Random(0).shuffle(jobs)
    print(f"{len(personas)} personas, {len(jobs)} episodes to run ({len(done)} already done)", flush=True)

    extra = {"chat_template_kwargs": {"enable_thinking": False}} if args.no_think else {}
    backend = OpenAICompatible(args.model, args.base_url, extra)
    lock = threading.Lock()
    counter = [0]

    def work(job):
        p, it, need, lang, rep = job
        if args.perspective == "third":
            result = run_episode(backend, it, need, lang, "tool", p[lang] or THIRD_NONE[lang],
                                 base=THIRD_BASE, ability=THIRD_ABILITY)
        else:
            result = run_episode(backend, it, need, lang, "tool", p[lang], base=first_base)
        record = {"key": f"{p['id']}|{it['id']}|{need}|{lang}|{rep}", "model": tag,
                  "persona": p["id"], "direction": p["direction"], "level": p["level"], "variant": p["variant"],
                  "item": it["id"], "op": it["op"], "need": need, "lang": lang, "rep": rep,
                  "perspective": args.perspective, "help_tool": args.help_tool, **result}
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            counter[0] += 1
            if counter[0] % 200 == 0:
                print(f"{counter[0]}/{len(jobs)} done", flush=True)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, jobs))
    print("finished", flush=True)


if __name__ == "__main__":
    main()
