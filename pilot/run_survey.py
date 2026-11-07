"""RQ2「說」：讓 Step 1 的每個 persona 填求助態度量表（Ryan & Pintrich, 1997 附錄的範例題，1–7 分）。

系統提示與 Step 1 相同（含 persona），但不給題目、不給工具；一次問一題，每題重複 --reps 次。
結果寫進 results/survey/<model>.jsonl，之後與 Step 1 的實際求助率比較。
"""
import argparse
import itertools
import json
import random
import re
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I 不會自動加入程式所在的資料夾
# 2026-11-02 修正（研究者決定選項 A）：問卷的系統提示拿掉工具說明，只保留角色句與 persona。
# 舊版沿用 Step 1 的系統提示（含「每一回合使用一個工具」），Llama 英文 95% 回答 ask_teacher 而不是分數。
# 舊版結果保留在 results/survey_v1_tools_in_system/。
SYSTEM = {"en": "You are a student doing math practice problems.", "zh": "你是一個正在做數學練習題的學生。"}


def _urlopen_retry(req, tries=3, timeout=1200):
    """本地 vLLM 呼叫：開啟思考時單次生成可能很久，逾時就重試，最後一次仍失敗才拋出。"""
    import time
    for i in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if i == tries - 1:
                raise
            time.sleep(30)

ROOT = Path(__file__).resolve().parent

# (代碼, 量表, 是否反向, English 原文, 繁中)
ITEMS = [
    ("AV1", "avoid", False, "If I need help to do a math problem I skip it.",
     "如果我需要別人幫忙才能做出一道數學題，我會直接跳過那一題。"),
    ("AV2", "avoid", False, "I don't ask for help in math, even if the work is too hard to solve on my own.",
     "就算數學作業難到我自己做不出來，我也不會開口求助。"),
    ("AD1", "adaptive", False, "If I get stuck on a math problem, I ask someone for help so I can keep working on it.",
     "數學題卡住的時候，我會找人幫忙，讓我能繼續做下去。"),
    ("AD2", "adaptive", False, "If I need help in math, I ask someone to give me hints or clues rather than the answer.",
     "數學需要幫忙時，我會請別人給我提示或線索，而不是直接給我答案。"),
    ("TT1", "threat_teacher", False, "I think the teacher might think I am dumb when I ask a question in math.",
     "我覺得在數學課問問題時，老師可能會覺得我很笨。"),
    ("TT2", "threat_teacher", False, "Teachers are more impressed if I complete my math work without asking anyone for help with it.",
     "如果我不靠任何人幫忙就完成數學作業，老師會對我更有好印象。"),
    ("TP1", "threat_peer", False, "I think other kids might think I am dumb when I ask a question in math.",
     "我覺得在數學課問問題時，其他同學可能會覺得我很笨。"),
    ("TP2", "threat_peer", False, "I worry about what other kids might think when I ask a question in math.",
     "在數學課問問題時，我會擔心其他同學怎麼看我。"),
    ("BE1", "benefit", False, "Asking questions in math makes the class more interesting for me.",
     "在數學課問問題，會讓我覺得上課更有趣。"),
    ("BE2", "benefit", False, "I think asking questions in math helps me learn.",
     "我覺得在數學課問問題能幫助我學習。"),
]
PROMPT = {
    "en": ("Rate how much you agree with the following statement, from 1 (strongly disagree) to 7 (strongly agree). "
           "Reply with a single number only.\nStatement: {item}"),
    "zh": "請評估你對下面這句話的同意程度，從 1（非常不同意）到 7（非常同意）。只回答一個數字。\n句子：{item}",
}


def ask(url, model, system, user, extra):
    body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 1.0, "max_tokens": 2048, **extra}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    text = json.load(_urlopen_retry(req))["choices"][0]["message"].get("content") or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()  # 去掉思考內容
    m = re.search(r"[1-7]", text)
    return (int(m.group()) if m else None), text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--no-think", action="store_true")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    personas = json.loads((ROOT / "personas" / "step1_personas.json").read_text())
    tag = args.model.split("/")[-1] + ("-nothink" if args.no_think else "")
    out = ROOT / "results" / "survey" / f"{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["key"] for l in out.open()} if out.exists() else set()
    jobs = [(p, it, lang, rep) for p, it, lang, rep in itertools.product(personas, ITEMS, ["en", "zh"], range(args.reps))
            if f"{p['id']}|{it[0]}|{lang}|{rep}" not in done]
    random.Random(0).shuffle(jobs)
    print(f"{len(jobs)} questions to ask ({len(done)} already done)", flush=True)

    url = args.base_url.rstrip("/") + "/chat/completions"
    extra = {"chat_template_kwargs": {"enable_thinking": False}} if args.no_think else {}
    lock = threading.Lock()

    def work(job):
        p, (code, scale, _rev, en, zh), lang, rep = job
        system = SYSTEM[lang] + ("\n" + p[lang] if p[lang] else "")  # persona 與 Step 1 相同；系統提示不含工具說明
        score, raw = ask(url, args.model, system, PROMPT[lang].format(item=zh if lang == "zh" else en), extra)
        record = {"key": f"{p['id']}|{code}|{lang}|{rep}", "model": tag, "persona": p["id"], "direction": p["direction"],
                  "level": p["level"], "variant": p["variant"], "item": code, "scale": scale, "lang": lang, "rep": rep,
                  "score": score, "raw": raw[:300]}
        with lock:
            with out.open("a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(work, jobs))
    print("finished", flush=True)


if __name__ == "__main__":
    main()
