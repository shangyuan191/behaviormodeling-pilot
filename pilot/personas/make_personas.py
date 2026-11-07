"""Step 1 persona 階梯（第二版）→ personas/step1_personas.json 與 step1_personas.md。

修改原則（相對於初稿）：
- 0 要素層只留純粹的特質詞，不寫行為。
- T 層拿掉「數學」，只寫對老師的態度。
- T＋A 層拿掉「有問題的時候」這類條件句。
- 情境統一寫成「不會的題目」，同層 3 句只換說法、不換意思；不用「只要…就」「就算…也」，強度一致。
- 高求助與低求助兩個階梯逐句對稱。
- 中性對照改成沒有人格聯想的事實。
"""
import json
from pathlib import Path

HIGH = {
    "0": [("你個性外向。", "You are outgoing."),
          ("你個性活潑。", "You are lively."),
          ("你個性開朗。", "You are cheerful.")],
    "T": [("你很喜歡你的老師。", "You really like your teacher."),
          ("你覺得老師很親切。", "You think your teacher is kind."),
          ("你很信任你的老師。", "You trust your teacher a lot.")],
    "TA": [("你常常問老師問題。", "You often ask your teacher questions."),
           ("你很習慣向老師提問。", "You are used to asking your teacher questions."),
           ("你很常向老師發問。", "You frequently ask your teacher questions.")],
    "TAC": [("做數學練習遇到不會的題目時，你會問老師。",
             "When you come across a problem you can't solve in math practice, you ask your teacher."),
            ("寫數學題碰到不會寫的題目時，你會向老師提問。",
             "When you run into a math problem you can't do, you ask your teacher about it."),
            ("數學練習中有題目不會做的時候，你會去問老師。",
             "When there is a problem you can't do in math practice, you go and ask your teacher.")],
    "TACT": [("在這次數學練習中，遇到不會的題目時，你會問老師。",
              "In this math practice, when you come across a problem you can't solve, you ask your teacher."),
             ("這次寫數學題時，碰到不會寫的題目，你會向老師提問。",
              "This time, when you run into a math problem you can't do, you ask your teacher about it."),
             ("這一次的數學練習裡，有題目不會做的時候，你會去問老師。",
              "In this round of math practice, when there is a problem you can't do, you go and ask your teacher.")],
}
LOW = {
    "0": [("你個性害羞。", "You are shy."),
          ("你個性內向。", "You are introverted."),
          ("你個性文靜。", "You are quiet by nature.")],
    "T": [("你很怕你的老師。", "You are afraid of your teacher."),
          ("你覺得老師很嚴格。", "You think your teacher is strict."),
          ("你和老師不太熟。", "You are not close to your teacher.")],
    "TA": [("你很少問老師問題。", "You rarely ask your teacher questions."),
           ("你不習慣向老師提問。", "You are not used to asking your teacher questions."),
           ("你幾乎不向老師發問。", "You almost never ask your teacher questions.")],
    "TAC": [("做數學練習遇到不會的題目時，你不會問老師。",
             "When you come across a problem you can't solve in math practice, you don't ask your teacher."),
            ("寫數學題碰到不會寫的題目時，你不會向老師提問。",
             "When you run into a math problem you can't do, you don't ask your teacher about it."),
            ("數學練習中有題目不會做的時候，你不會去問老師。",
             "When there is a problem you can't do in math practice, you don't go and ask your teacher.")],
    "TACT": [("在這次數學練習中，遇到不會的題目時，你不會問老師。",
              "In this math practice, when you come across a problem you can't solve, you don't ask your teacher."),
             ("這次寫數學題時，碰到不會寫的題目，你不會向老師提問。",
              "This time, when you run into a math problem you can't do, you don't ask your teacher about it."),
             ("這一次的數學練習裡，有題目不會做的時候，你不會去問老師。",
              "In this round of math practice, when there is a problem you can't do, you don't go and ask your teacher.")],
}
NEUTRAL = [("你的生日在三月。", "Your birthday is in March."),
           ("你的座號是 12 號。", "Your seat number in class is 12."),
           ("你每天搭公車上學。", "You take the bus to school every day.")]

LEVEL_LABEL = {"0": "0 要素", "T": "T", "TA": "T＋A", "TAC": "T＋A＋C", "TACT": "T＋A＋C＋T"}


def build():
    personas = [{"id": "L0", "direction": "none", "level": "L0", "variant": 0, "zh": "", "en": ""}]
    personas += [{"id": f"N{i + 1}", "direction": "neutral", "level": "neutral", "variant": i + 1, "zh": zh, "en": en}
                 for i, (zh, en) in enumerate(NEUTRAL)]
    for direction, ladder in (("high", HIGH), ("low", LOW)):
        for level, rows in ladder.items():
            personas += [{"id": f"{direction[0].upper()}-{level}-{i + 1}", "direction": direction, "level": level,
                          "variant": i + 1, "zh": zh, "en": en} for i, (zh, en) in enumerate(rows)]
    return personas


def to_markdown(personas):
    lines = ["# Step 1 persona 階梯（第二版）", "",
             "由 `make_personas.py` 產生。修改原則見該檔開頭的說明。", ""]
    sections = [("A. 高求助階梯（用在一般題、只學過加減的題目）", "high"),
                ("B. 低求助階梯（用在缺條件題）", "low"), ("C. 對照組（兩個階梯共用）", None)]
    for title, direction in sections:
        lines += [f"## {title}", "", "| 編號 | 層級 | 繁中 | English |", "| --- | --- | --- | --- |"]
        rows = [p for p in personas if p["direction"] == direction] if direction else \
            [p for p in personas if p["direction"] in ("none", "neutral")]
        for p in rows:
            level = LEVEL_LABEL.get(p["level"], "無 persona" if p["level"] == "L0" else "中性")
            lines.append(f"| {p['id']} | {level} | {p['zh'] or '（不加）'} | {p['en'] or '(none)'} |")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    here = Path(__file__).parent
    personas = build()
    (here / "step1_personas.json").write_text(json.dumps(personas, ensure_ascii=False, indent=1))
    (here / "step1_personas.md").write_text(to_markdown(personas))
    print(len(personas), "personas")
