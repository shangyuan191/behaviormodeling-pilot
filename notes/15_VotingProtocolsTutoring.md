# 15 Voting Protocols for Role-Constrained Multi-Agent Tutoring

Qiu & Gill（康乃爾、史丹佛）· ICML 2026 · [arXiv 2606.08030](https://arxiv.org/abs/2606.08030) · 本機檔案 `15_VotingProtocolsTutoring_2026.pdf`

## 一句話重點

這篇的主題是「多個 AI 家教怎麼投票決定要給學生哪一句回應」，**跟我們有關的只有它的模擬學生設計**：6 種學生 persona，每種同時用「5 個 0–1 的數值」和「一段文字描述」來定義，其中包含一位「求助迴避型」學生。

## 它在問什麼

四個各有專長的家教 agent（鷹架、迷思概念、動機、後設認知）各自提出回應，再用不同投票規則（多數決、排序、累積、認可投票）選出一個給學生。投票規則會不會影響最後選出的教學策略和學生的學習成效？

## 怎麼做（只摘跟我們有關的部分）

**6 種模擬學生 persona**，每種都有 5 個數值（先備知識、自信、毅力、挫折敏感度、**求助傾向**）加上一段文字。例如附錄中的「求助迴避型」：

> help seeking = 0.1。An insecure learner who avoids requesting help due to fear of looking incapable. May provide brief, guarded responses, hide uncertainty, and continue with shaky reasoning rather than ask clarifying questions. Unlike overconfident students, they do not reject help because they feel right; they avoid help because they feel exposed.

以及「依賴提示型」：help seeking = 1.0，「一卡住就立刻要提示，把思考丟給家教」。

在 SciQ（科學問答）與 HumanEval（程式）上，40 題 × 6 種 persona × 5 種條件，共 1,200 次模擬互動。

## 發現了什麼

- 投票規則會改變最後選出的教學策略，不同 persona 受影響的程度也不同。
- 作者明說：**「目標不是宣稱這些 persona 具有心理真實性」**，只是用來製造學生之間的差異。

## 跟我們的關係

**這是一個「persona 被拿來用、但從沒被驗證」的典型例子，正好凸顯我們題目的價值。** 他們假設「help seeking = 0.1」的學生真的會少求助，但完全沒檢查。如果 persona 對求助行為的控制力其實很弱（The Personality Illusion 的發現），那所有建立在模擬學生上的教學系統研究都要打折扣。這可以寫進我們的動機段落：**「教育 AI 研究大量依賴 persona 定義模擬學生，但沒人驗證 persona 是否真的控制了行為。」**

**可以借用的設計：**

- **「數值」作為一種 persona 寫法**：「help seeking = 0.1」是一種很特別的顆粒度：完全抽象，但直接對準行為。可以加成一個條件，看它和「文字描述」哪個控制力強。
- **求助迴避的文字描述寫得很好**：「因為怕看起來無能而不求助」、「跟過度自信的學生不同：他們不是覺得自己對，而是覺得自己被暴露」，這和 Ryan & Pintrich 的「威脅感」完全一致，可以參考它的寫法來寫我們的 persona。
- **區分兩種「低求助」**：「過度自信所以不問」和「怕丟臉所以不問」在行為上可能相同，但原因不同。我們的 persona 設計可以把這兩者分開，看 agent 能不能表現出差別，例如怕丟臉型在「私下」管道會問，過度自信型則都不問（呼應理論分頁的 CAPS 設計）。

**要注意的地方：**

- **數值前後不一致**：正文表 1 寫「求助迴避型」的先備知識 0.5、自信 0.7；附錄全文卻寫 0.4、0.3。引用時要注意以附錄的實際 prompt 為準。
- 不是心理學或教育學研究，persona 只是工具。
