"""開跑前的檢查：用 6 題缺條件題確認模型的工具呼叫能被 vLLM 正確解析。

至少 3 題的第一步是解析成功的工具呼叫才算通過（exit code 0），否則印出模型實際的回覆並回傳 1。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I 不會自動加入程式所在的資料夾
from run_pilot import OpenAICompatible, run_episode

ROOT = Path(__file__).resolve().parent


def main(model, base_url):
    items = {it["id"]: it for it in json.loads((ROOT / "items" / "pilot_items.json").read_text())}
    backend = OpenAICompatible(model, base_url)
    ok = 0
    for item_id in ("M05", "A04", "M09"):
        for lang in ("en", "zh"):
            first = run_episode(backend, items[item_id], "missing", lang)["actions"][0]
            parsed = first["tool"] is not None
            ok += parsed
            print(f"{item_id} {lang} tool={first['tool']} text={first['text'][:120]!r}", flush=True)
    print(f"parsed tool calls: {ok}/6")
    return 0 if ok >= 3 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
