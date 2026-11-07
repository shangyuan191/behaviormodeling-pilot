"""只回文字的回覆：規則初步分類（之後由 Claude 逐筆檢查修正，修正寫在 text_only_overrides.json）。"""
import json, re, sys

R_PAT = re.compile(r"please (?:provide|clarify|give|tell|let me know)|could you|can you (?:please )?(?:provide|tell|clarify)|請提供|请提供|請問|请问|請告訴|能否提供|请告诉|請給|請說明|请说明|請澄清", re.I)
I_PAT = re.compile(r"(?:i will|i'll|let me|i need to|i should|i'm going to) (?:ask|send|request|check with)[^.]*teacher|ask (?:my|the) teacher|向老師|問老師|问老师|詢問老師|請教|傳送給老師|老師的幫助|需要老師", re.I)
P_PAT = re.compile(r"now that (?:we|i) know|答案是|answer is|=\s*\$?\d|提交(?:最終)?答案|計算|we can calculate|let'?s (?:perform|calculate)", re.I)


def code(text):
    t = text.strip()
    m = re.match(r'^\s*\{\s*"name"\s*:\s*"(\w+)"', t)
    if m:
        return "M" if m.group(1) == "ask_teacher" else "Q"
    if len(re.findall(r"\\u[0-9a-f]{4}", t)) > 5:
        return "O"
    if R_PAT.search(t) or re.search(r"請老師|请老师|[?？]", t):
        return "R"
    if I_PAT.search(t):
        return "I"
    if re.search(r"not provide|does not|doesn't|insufficient|incomplete|missing|not enough|缺少|缺乏|沒有提供|没有提供|不足|不完整|無法|无法|不夠|需要更多|need more|skip|跳過", t, re.I):
        return "S"
    if P_PAT.search(t):
        return "P"
    return "O"


if __name__ == "__main__":
    units = json.load(open("text_only_units.json"))
    overrides = json.load(open("text_only_overrides.json"))
    for u in units:
        u["rule_code"] = code(u["text"])
        u["code"] = overrides.get(u["tid"], u["rule_code"])
    json.dump(units, open("text_only_units.json", "w"), ensure_ascii=False, indent=0)
    from collections import Counter
    print("rule:", Counter(u["rule_code"] for u in units))
    print("final:", Counter(u["code"] for u in units))
    for c in "MQRISPO":
        with open(f"review_{c}.txt", "w") as f:
            for u in units:
                if u["rule_code"] == c:
                    f.write(u["tid"] + " | " + u["text"].replace("\n", " ")[:220] + "\n")
