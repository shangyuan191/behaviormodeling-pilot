# BehaviorModeling Pilot：persona 描述顆粒度與 LLM agent 的求助行為

用 LLM 扮演學生做數學題，讓它可以用工具「問老師」，依六個主題觀察 persona 的寫法如何影響求助：

1. **預設傾向：** 沒有 persona 時，模型原本會不會分辨該不該問；思考模式、求助做成工具或文字有沒有影響。
2. **persona 顆粒度：** persona 寫到哪一層（特質 → 態度 → 行動 → 情境 → 時間，TACT 相容性原則）才控制得了求助的 tool call；換題型、換工具名稱是否穩健。
3. **求助的品質：** 問的是線索（工具性）還是答案（執行性）；不問的時候在做什麼。
4. **說與做：** 量表上「說」的和實際「做」的是否一致。
5. **情境與管道：** 怕丟臉的 persona 會不會自己改成私下問（CAPS H8）。
6. **視角：** 第三人稱描述是否比較不受模型的「好學生」預設影響。

**完整結果與討論見 [`pilot/results/report/pilot_report_full.md`](pilot/results/report/pilot_report_full.md)**（中文，依上述主題分章，含所有圖表、限制與下一步提案）。這是 pilot 階段的結果：規模小（24 題 × 2 語言）、文字編碼由規則與 Claude 判定、尚未有第二位人工評分者，也還沒有和真實學生資料比較。

## 主要發現（摘要，細節與數字見報告）

1. 模型原本的求助傾向差異很大：Gemini、Qwen3 會分辨題目是否缺條件；Qwen2.5、Granite 連不需要問的題目也常問。
2. persona 要寫到「行動」才控制得了 tool call；只寫特質或對老師的態度幾乎沒有效果。低求助階梯在 Qwen3（思考開／關）、Llama-3.1、Qwen2.5 上，缺條件題與能力不足題都顯著下降、斷點相同；換成另外兩種工具名稱，方向仍不變。
3. persona 控制的是求助的「量」，不是「時機」：低求助 persona 讓模型連會做的題目也少問；只有 Qwen2.5 會把不會的題目跳過、會的照做。
4. 只寫到態度的 persona 會讓模型在量表上「說」自己很迴避求助，實際照樣求助。
5. 「怕被同學看扁」的 persona 沒提私下管道，模型卻會自己改成下課私下問（CAPS H8 的初步支持）。
6. 第三人稱描述比較不會被模型的「好學生」預設拉走。

## 目錄

```
pilot/
  items/            題目集（24 題，英文 + 繁中）與選題程式
  personas/         TACT persona（低／高求助各 5 層 × 3 種措辭）
  designs/          第三人稱 persona、實驗設計草稿
  templates/        Granite-3.3 的工具呼叫對話模板（修正版）
  run_pilot.py      無 persona 基線（程式代號 Step 0；Gemini API 或本機 vLLM）
  run_step1.py      TACT persona 階梯（程式代號 Step 1；--perspective third、--help-tool、--needs）
  run_survey.py     求助量表（說）
  run_caps.py       CAPS：公開 vs 私下求助
  judge/            求助類型編碼（工具性 vs 執行性）與只回文字的分類；含人工判定樣本與驗證集
  code_caps_text.py、code_step1_text.py   只回文字回覆的關鍵字編碼
  analyze*.py、report_figures*.py         彙整、統計檢定（persona 層次置換 + Holm）、作圖
  run_*.sh          實際使用的 GPU 排程腳本（伺服器環境專用，留作紀錄）
  results/          所有原始結果（每個 episode 一行 jsonl，含完整工具呼叫紀錄）、摘要 txt、報告與圖
notes/              相關論文的中文精讀筆記
```

## 重現

環境：Python 3.11、`vllm==0.25.1`、`openai`、`numpy`、`pandas`、`matplotlib`（見 `requirements.txt`）。實驗在單張 RTX 5090 上跑。

**1. 開 vLLM 伺服器**（實際使用的設定；`--max-model-len 8192 --max-num-seqs 8`）

| 模型 | 參數 |
| --- | --- |
| Qwen3-8B-FP8 | `--tool-call-parser hermes --enforce-eager`（不加 `--enforce-eager` 時，vLLM 0.25.1 常卡在 0 tok/s） |
| Llama-3.1-8B-Instruct | `--tool-call-parser llama3_json --quantization fp8` |
| Qwen2.5-7B-Instruct | `--tool-call-parser hermes --quantization fp8` |
| granite-3.3-8b-instruct | `--tool-call-parser granite --quantization fp8 --chat-template pilot/templates/granite33_tools.jinja` |

```bash
vllm serve Qwen/Qwen3-8B-FP8 --port 8011 --max-model-len 8192 --max-num-seqs 8 \
  --enable-auto-tool-choice --tool-call-parser hermes --enforce-eager
```

**2. 跑實驗**（在 `pilot/` 底下；中斷後重跑會接續，不會重複）

```bash
URL=http://localhost:8011/v1
python -I run_pilot.py  --model Qwen/Qwen3-8B-FP8 --base-url $URL --no-think --reps 5          # Step 0
python -I run_step1.py  --model Qwen/Qwen3-8B-FP8 --base-url $URL --no-think --direction low --reps 3
python -I run_step1.py  ... --perspective third                                                 # 第三人稱
python -I run_step1.py  ... --direction low --help-tool ask_for_help                            # 工具名稱檢查
python -I run_survey.py --model Qwen/Qwen3-8B-FP8 --base-url $URL --no-think --reps 3
python -I run_caps.py   --model Qwen/Qwen3-8B-FP8 --base-url $URL --no-think --reps 3
```

`--no-think` 關閉 Qwen3 的思考模式。Gemini（Step 0）：在 repo 根目錄建立 `.env`，內容為 `GEMINI_API_KEY=<你的金鑰>`，再執行 `python -I run_pilot.py --reps 3`。

**3. 分析**

```bash
python judge/code_asks.py          # 求助內容分類（工具性 vs 執行性）
(cd judge && python code_text_only.py)   # 須在 judge/ 內執行；Step 1 只回文字的分類（人工修正在 judge/text_only_overrides.json）
python judge/apply_text_codes.py   # 合併成「有效求助率」
python code_caps_text.py && python code_step1_text.py         # CAPS／工具名稱檢查的文字編碼
python analyze_round2.py > results/round2_summary.txt
python analyze_stats.py  > results/stats_summary.txt
python analyze_toolname.py > results/toolname_summary.txt
python analyze_lowability.py > results/lowability_summary.txt        # 低求助 × 只學過加減（報告 6.3、7.2）
python analyze_stats_lowability.py > results/stats_lowability.txt
python report_figures.py && python report_figures_round2.py
```

## 資料來源與授權

- 題目改寫自 [UMWP](https://github.com/Yuki-Asuuna/UMWP)（Sun et al., LREC-COLING 2024）「缺關鍵資訊」類配對題，原始資料為 CC BY-SA 4.0；`pilot/items/` 依同一授權釋出，繁中版為本研究翻譯。UMWP 等原始資料集不收錄於本 repo，`build_candidates.py` 需先自行下載 UMWP。
- `results/` 中的回覆由各模型產生，使用時請遵守各模型的授權條款（Llama 3.1 Community License、Gemini API 條款等）。
- `notes/` 為論文閱讀筆記，論文本身不收錄。
