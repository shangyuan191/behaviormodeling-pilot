# 下一輪實驗設計草稿（請審閱措辭）

## A. RQ2「說」：求助態度量表

**做法：** 用和 Step 1 完全相同的系統提示與 persona（不給題目、不給工具），一次問一題，請模型回答 1–7 的同意程度。每題問 3 次取平均。之後把每個 persona 的量表分數，和它在 Step 1 的實際求助率（已經有資料）做相關，看「說」能不能預測「做」。

**題目來源：** Ryan & Pintrich（1997）附錄公開的範例題（每個量表只公開 2 題，完整題目未公開）。英文照原文；繁中是我的翻譯初稿，**請你修改**。

| 代碼 | 量表 | English（原文） | 繁中（翻譯初稿） |
| --- | --- | --- | --- |
| AV1 | 求助迴避 | If I need help to do a math problem I skip it. | 如果我需要別人幫忙才能做出一道數學題，我會直接跳過那一題。 |
| AV2 | 求助迴避 | I don't ask for help in math, even if the work is too hard to solve on my own. | 就算數學作業難到我自己做不出來，我也不會開口求助。 |
| AD1 | 適應性求助 | If I get stuck on a math problem, I ask someone for help so I can keep working on it. | 數學題卡住的時候，我會找人幫忙，讓我能繼續做下去。 |
| AD2 | 適應性求助（工具性） | If I need help in math, I ask someone to give me hints or clues rather than the answer. | 數學需要幫忙時，我會請別人給我提示或線索，而不是直接給我答案。 |
| TT1 | 來自老師的威脅感 | I think the teacher might think I am dumb when I ask a question in math. | 我覺得在數學課問問題時，老師可能會覺得我很笨。 |
| TT2 | 來自老師的威脅感 | Teachers are more impressed if I complete my math work without asking anyone for help with it. | 如果我不靠任何人幫忙就完成數學作業，老師會對我更有好印象。 |
| TP1 | 來自同學的威脅感 | I think other kids might think I am dumb when I ask a question in math. | 我覺得在數學課問問題時，其他同學可能會覺得我很笨。 |
| TP2 | 來自同學的威脅感 | I worry about what other kids might think when I ask a question in math. | 在數學課問問題時，我會擔心其他同學怎麼看我。 |
| BE1 | 求助的好處 | Asking questions in math makes the class more interesting for me. | 在數學課問問題，會讓我覺得上課更有趣。 |
| BE2 | 求助的好處 | I think asking questions in math helps me learn. | 我覺得在數學課問問題能幫助我學習。 |

**提問格式：**

- English：`Rate how much you agree with the following statement, from 1 (strongly disagree) to 7 (strongly agree). Reply with a single number only.\nStatement: <item>`
- 繁中：`請評估你對下面這句話的同意程度，從 1（非常不同意）到 7（非常同意）。只回答一個數字。\n句子：<item>`

**主要分析：** 求助迴避分數（AV − AD 的平均）vs Step 1 的實際求助率，分模型、分語言算相關。預期依精讀 01：persona 會明顯改變量表分數，但量表分數對行為的預測力有限；依相容性原則，T＋A 以上的 persona 量表與行為會比較一致。

---

## B. CAPS 公開／私下情境

**做法：** 把 `ask_teacher` 拆成兩個工具，其他不變。用缺條件題（客觀上需要問），看不同 persona 選擇公開還是私下。

| 工具 | English 說明 | 繁中說明 |
| --- | --- | --- |
| `raise_hand` | Raise your hand and ask the teacher in front of the whole class. Everyone will hear your question. | 在全班面前舉手問老師。全班都會聽到你的問題。 |
| `message_teacher` | Send the teacher a private message. Only the teacher will see it. | 私下傳訊息給老師。只有老師看得到。 |
| `submit_answer`、`skip` | 同 Step 1 | 同 Step 1 |

**persona（每類 2 種措辭，請修改）：**

| 類型 | 繁中 | English | 預測（CAPS） |
| --- | --- | --- | --- |
| 無 persona | （不加） | (none) | 基線 |
| 中性 | 你的生日在三月。 | Your birthday is in March. | ≈ 基線 |
| 特質-1 | 你個性害羞。 | You are shy. | 兩種都少問？ |
| 特質-2 | 你個性內向。 | You are introverted. | 同上 |
| 歷程（理論 3 的 H8）-1 | 你覺得在班上問問題代表自己不夠聰明，你最在意的是不要被同學看扁。 | You think asking questions in class means you're not smart enough, and what you care about most is not being looked down on by your classmates. | 公開少、私下照問 |
| 歷程-2 | 想到要在全班面前開口，你就會很緊張；你很怕同學覺得你很笨。 | Speaking up in front of the whole class makes you very nervous; you are afraid your classmates will think you are dumb. | 公開少、私下照問 |
| if–then-1 | 在全班面前，你不敢問老師問題；但私下的時候，你會傳訊息問老師。 | In front of the whole class you don't dare to ask the teacher questions, but in private you send the teacher a message. | 公開少、私下多 |
| if–then-2 | 你只在沒有其他同學看到的時候才會問老師問題。 | You only ask the teacher questions when no other classmates can see. | 公開少、私下多 |
| 反向 if–then（對照） | 你喜歡在全班面前舉手發問，但不習慣私下傳訊息給老師。 | You like raising your hand to ask questions in front of the class, but you are not used to messaging the teacher privately. | 公開多、私下少 |

**主要指標：** 公開比例＝raise_hand ÷（raise_hand＋message_teacher）；以及 H8 的關鍵比較：歷程型 persona（沒提到私下管道）會不會自己推出「改用私訊」。

---

## C. 第三人稱預測（HACHIMI-II）

**做法：** 系統提示改成「預測一位學生會怎麼做」，persona 改成第三人稱，題目與工具不變。用 Step 1 的兩個階梯（低求助 × 缺條件題、高求助 × 只學過加減），和第一人稱的結果直接比較。

**系統提示（第三人稱版）：**

- English：`You will predict what a student does next in math practice. Here is a description of the student: <persona>. Use the tools to show what this student would do: ask_teacher (the student sends a question to the teacher), submit_answer (the student submits a final answer), or skip (the student skips the problem). Use one tool per turn.`
- 繁中：`你要預測一位學生在數學練習中的下一步。這位學生的描述如下：<persona>。請用工具表示這位學生會做的事：ask_teacher（學生傳送問題給老師）、submit_answer（學生提交最終答案）、skip（學生跳過這一題）。每一回合使用一個工具。`

**persona 轉換規則：** 繁中把「你」改成「這位學生」、「你的老師」改成「自己的老師」；英文改用 "This student …"，之後用 "they"。完整對照表見 `designs/third_person.json`（英文人工改寫）。例子：

| 第一人稱 | 第三人稱 |
| --- | --- |
| 你很怕你的老師。 | 這位學生很怕自己的老師。 |
| 做數學練習遇到不會的題目時，你不會問老師。 | 做數學練習遇到不會的題目時，這位學生不會問老師。 |
| You rarely ask your teacher questions. | This student rarely asks their teacher questions. |
| When you come across a problem you can't solve in math practice, you don't ask your teacher. | When this student comes across a problem they can't solve in math practice, they don't ask their teacher. |

**預期（HACHIMI-II）：** 第三人稱預測比較不會被模型自己的「好學生」預設拉走，所以 0 要素與 T 層的效果可能比第一人稱大；能力外洩也可能減少（「只學過加減」的學生被預測為答錯或求助）。
