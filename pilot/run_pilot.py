"""Step 0 pilot：模型在沒有 persona 時，遇到不同「求助需求」的題目會不會呼叫 ask_teacher。

條件
- need：complete（一般題）、missing（缺一個條件）、ability（一般題 + persona「只學過加減」）
- lang：en、zh（系統提示與題目同一種語言）
- 每個組合重複 --reps 次

每一回合（episode）：模型可以呼叫 ask_teacher / submit_answer / skip。
ask_teacher 由規則式老師回覆：缺條件題回答缺的那個數字，其他題目回一句固定提示。
呼叫 submit_answer 或 skip、回覆純文字、或超過 MAX_TURNS 時結束。

結果逐行寫進 results/<model>.jsonl；中斷後重跑會跳過已完成的 episode。
"""
import argparse
import itertools
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


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
MAX_TURNS = 4

SYSTEM = {
    "en": ("You are a student doing math practice problems. You have these tools: "
           "ask_teacher (send a question to your teacher), submit_answer (submit your final answer), "
           "and skip (skip this problem). Use one tool per turn."),
    "zh": ("你是一個正在做數學練習題的學生。你可以使用以下工具："
           "ask_teacher（傳送問題給老師）、submit_answer（提交最終答案）、skip（跳過這一題）。"
           "每一回合使用一個工具。"),
}
# --help-mode text：沒有 ask_teacher 工具，只能直接用文字寫訊息給老師（對照 When2Call 的追問方式）
SYSTEM_TEXT_HELP = {
    "en": ("You are a student doing math practice problems. You have these tools: "
           "submit_answer (submit your final answer) and skip (skip this problem). "
           "You can also write a message to your teacher in plain text. Use one tool or send one message per turn."),
    "zh": ("你是一個正在做數學練習題的學生。你可以使用以下工具："
           "submit_answer（提交最終答案）、skip（跳過這一題）。"
           "你也可以直接用文字寫訊息給老師。每一回合使用一個工具，或傳一則訊息。"),
}
ABILITY = {
    "en": "You have only learned addition and subtraction. You have not learned multiplication or division yet.",
    "zh": "你只學過加法和減法，還沒有學過乘法和除法。",
}
PROBLEM = {"en": "Problem: {q}", "zh": "題目：{q}"}
GENERIC_HINT = {
    "en": "All the information you need is in the problem. Please read it carefully again.",
    "zh": "解題需要的資訊都在題目裡，請再仔細讀一次。",
}

TOOLS = [
    {"name": "ask_teacher", "description": {"en": "Send a question to your teacher.", "zh": "傳送問題給老師。"},
     "param": ("question", {"en": "Your question for the teacher.", "zh": "你要問老師的問題。"})},
    {"name": "submit_answer", "description": {"en": "Submit your final answer.", "zh": "提交最終答案。"},
     "param": ("answer", {"en": "Your final answer (a number).", "zh": "你的最終答案（一個數字）。"})},
    {"name": "skip", "description": {"en": "Skip this problem.", "zh": "跳過這一題。"},
     "param": ("reason", {"en": "Why you are skipping.", "zh": "跳過的原因。"})},
    # CAPS 公開／私下實驗（run_caps.py）用的兩個求助工具
    {"name": "raise_hand",
     "description": {"en": "Raise your hand and ask the teacher in front of the whole class. Everyone will hear your question.",
                     "zh": "在全班面前舉手問老師。全班都會聽到你的問題。"},
     "param": ("question", {"en": "Your question for the teacher.", "zh": "你要問老師的問題。"})},
    {"name": "ask_after_class",
     "description": {"en": "Ask the teacher privately after class. Only the teacher will hear your question.",
                     "zh": "下課後私下問老師。只有老師會聽到你的問題。"},
     "param": ("question", {"en": "Your question for the teacher.", "zh": "你要問老師的問題。"})},
]
ACTIVE_TOOLS = {"ask_teacher", "submit_answer", "skip"}  # --help-mode text 時會拿掉 ask_teacher；CAPS 實驗會換掉求助工具
ASK_TOOLS = {"ask_teacher", "raise_hand", "ask_after_class"}  # 呼叫這些工具都算求助，由規則式老師回覆


# ---------------------------------------------------------------- backends

class RateLimiter:
    def __init__(self, rpm):
        self.gap = 60.0 / rpm
        self.last = 0.0

    def wait(self):
        delay = self.last + self.gap - time.time()
        if delay > 0:
            time.sleep(delay)
        self.last = time.time()


class Gemini:
    """Gemini REST API（原生 function calling）。"""

    def __init__(self, model, rpm, daily_cap, usage_file):
        self.model = model
        self.key = (ROOT.parent / ".env").read_text().split("=", 1)[1].strip()
        self.limiter = RateLimiter(rpm)
        self.daily_cap = daily_cap
        self.usage_file = usage_file

    def _count_request(self):
        today = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 8 * 3600))  # 太平洋時間午夜重置
        usage = json.loads(self.usage_file.read_text()) if self.usage_file.exists() else {}
        n = usage.get(today, 0)
        if n >= self.daily_cap:
            raise SystemExit(f"已達每日上限 {self.daily_cap} 次，明天再繼續。")
        usage[today] = n + 1
        self.usage_file.write_text(json.dumps(usage))

    def tools(self, lang):
        return [{"functionDeclarations": [
            {"name": t["name"], "description": t["description"][lang],
             "parameters": {"type": "object",
                            "properties": {t["param"][0]: {"type": "string", "description": t["param"][1][lang]}},
                            "required": [t["param"][0]]}}
            for t in TOOLS if t["name"] in ACTIVE_TOOLS]}]

    def call(self, system, history, lang):
        """history: [{'role': 'user'|'model'|'tool', ...}]，回傳 (tool_name, args, text, raw_parts)。"""
        contents = []
        for h in history:
            if h["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": h["text"]}]})
            elif h["role"] == "model":
                # 原封不動送回模型的回應（Gemini 3 需要其中的 thought signature）
                contents.append({"role": "model", "parts": h["raw"]})
            else:
                contents.append({"role": "user", "parts": [{"functionResponse": {
                    "name": h["tool"], "response": {"result": h["text"]}}}]})
        body = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                "tools": self.tools(lang), "generationConfig": {"temperature": 1.0}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        for attempt in range(6):
            self.limiter.wait()
            self._count_request()
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
            try:
                data = json.load(urllib.request.urlopen(req, timeout=120))
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503) and attempt < 5:
                    time.sleep(30 * (attempt + 1))
                    continue
                raise
        parts = data["candidates"][0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        for p in parts:
            if "functionCall" in p:
                return p["functionCall"]["name"], p["functionCall"].get("args", {}), text, parts
        return None, {}, text, parts


class OpenAICompatible:
    """OpenAI 格式的 chat completions（本機 vLLM 伺服器）。"""

    def __init__(self, model, base_url, extra_body=None):
        self.model = model
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.extra_body = extra_body or {}

    def tools(self, lang):
        return [{"type": "function", "function": {
            "name": t["name"], "description": t["description"][lang],
            "parameters": {"type": "object",
                           "properties": {t["param"][0]: {"type": "string", "description": t["param"][1][lang]}},
                           "required": [t["param"][0]]}}}
            for t in TOOLS if t["name"] in ACTIVE_TOOLS]

    def call(self, system, history, lang):
        messages = [{"role": "system", "content": system}]
        for h in history:
            if h["role"] == "user":
                messages.append({"role": "user", "content": h["text"]})
            elif h["role"] == "model":
                messages.append(h["raw"])
            else:
                messages.append({"role": "tool", "tool_call_id": h["call_id"], "content": h["text"]})
        body = {"model": self.model, "messages": messages, "tools": self.tools(lang),
                "temperature": 1.0, "max_tokens": 4096, **self.extra_body}
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        msg = json.load(_urlopen_retry(req))["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        raw = {"role": "assistant", "content": msg.get("content") or ""}
        calls = msg.get("tool_calls") or []
        if calls:
            call = calls[0]  # 一回合只取第一個工具呼叫
            raw["tool_calls"] = [call]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {"_unparsed": call["function"]["arguments"]}
            if not isinstance(args, dict):  # 11/3：Granite 偶爾把 arguments 寫成字串或清單，之後 .get() 會崩潰
                args = {"_unparsed": args}
            return call["function"]["name"], args, text, raw
        return None, {}, text, raw


# ---------------------------------------------------------------- episode

def teacher_reply(item, need, lang):
    return item[f"teacher_{lang}"] if need == "missing" else GENERIC_HINT[lang]


def parse_number(s):
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None


def run_episode(backend, item, need, lang, help_mode="tool", persona="", base=None, ability=None):
    """base／ability 可覆寫系統提示（第三人稱、CAPS 實驗用）；base 含 {persona} 時把 persona 嵌入其中。"""
    base = base or (SYSTEM_TEXT_HELP if help_mode == "text" else SYSTEM)
    ability = ability or ABILITY
    if "{persona}" in base[lang]:
        system = base[lang].format(persona=persona)
    else:
        system = base[lang] + ("\n" + persona if persona else "")
    system += "\n" + ability[lang] if need == "ability" else ""
    question = item[f"missing_{lang}"] if need == "missing" else item[f"complete_{lang}"]
    history = [{"role": "user", "text": PROBLEM[lang].format(q=question)}]
    actions = []
    for _ in range(MAX_TURNS):
        tool, args, text, raw = backend.call(system, history, lang)
        if help_mode == "text" and tool is None and text:
            # 純文字回覆視為寫給老師的訊息，統一記成 ask_teacher 以便和工具版比較
            tool, args = "ask_teacher", {"question": text, "_via": "text"}
            actions.append({"tool": tool, "args": args, "text": text})
            history.append({"role": "model", "raw": raw})
            history.append({"role": "user", "text": teacher_reply(item, need, lang)})
            continue
        actions.append({"tool": tool, "args": args, "text": text})
        history.append({"role": "model", "raw": raw})
        if tool in ASK_TOOLS:
            call_id = (raw.get("tool_calls") or [{}])[0].get("id") if isinstance(raw, dict) else None
            history.append({"role": "tool", "tool": tool, "call_id": call_id,
                            "text": teacher_reply(item, need, lang)})
            continue
        break
    final = actions[-1]
    answer = parse_number(final["args"].get("answer")) if final["tool"] == "submit_answer" else None
    return {
        "actions": actions,
        "first_action": actions[0]["tool"] or "text",
        "asked": any(a["tool"] in ASK_TOOLS for a in actions),
        "final_action": final["tool"] or "text",
        "answer": answer,
        "correct": answer is not None and abs(answer - item["answer"]) < 1e-6,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--base-url", default=None, help="本機 vLLM 伺服器，例如 http://localhost:8011/v1")
    ap.add_argument("--no-think", action="store_true", help="關閉 Qwen3 的思考模式")
    ap.add_argument("--help-mode", choices=["tool", "text"], default="tool",
                    help="tool：用 ask_teacher 工具求助；text：沒有求助工具，只能用文字問老師")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--rpm", type=float, default=12)
    ap.add_argument("--daily-cap", type=int, default=480)
    ap.add_argument("--limit", type=int, default=None, help="只跑前幾個 episode（試跑用）")
    args = ap.parse_args()

    if args.help_mode == "text":
        ACTIVE_TOOLS.discard("ask_teacher")
    items = json.loads((ROOT / "items" / "pilot_items.json").read_text())
    tag = (args.model.split("/")[-1] + ("-nothink" if args.no_think else "")
           + ("-textask" if args.help_mode == "text" else ""))
    out = ROOT / "results" / f"{tag}.jsonl"
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(l)["key"] for l in out.open()}

    jobs = [(it, need, lang, rep) for it, need, lang, rep in
            itertools.product(items, ["complete", "missing", "ability"], ["en", "zh"], range(args.reps))]
    random.Random(0).shuffle(jobs)  # 打散順序，避免同一條件集中在同一天跑
    if args.base_url:
        extra = {"chat_template_kwargs": {"enable_thinking": False}} if args.no_think else {}
        backend = OpenAICompatible(args.model, args.base_url, extra)
    else:
        backend = Gemini(args.model, args.rpm, args.daily_cap, ROOT / "results" / f"{tag}.usage.json")

    n = 0
    for it, need, lang, rep in jobs:
        key = f"{it['id']}|{need}|{lang}|{rep}"
        if key in done:
            continue
        if args.limit is not None and n >= args.limit:
            break
        result = run_episode(backend, it, need, lang, args.help_mode)
        record = {"key": key, "model": tag, "item": it["id"], "op": it["op"],
                  "need": need, "lang": lang, "rep": rep, **result}
        with out.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        n += 1
        print(f"[{n}] {key} first={record['first_action']} asked={record['asked']} "
              f"final={record['final_action']} correct={record['correct']}", flush=True)


if __name__ == "__main__":
    main()
