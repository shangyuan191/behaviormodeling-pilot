# Pilot Step 0：模型原本會不會問老師？

目的：在沒有任何「個性」persona 的情況下，量模型遇到三種「需要求助」的情境時，呼叫 `ask_teacher` 的比例（L0 基線）。這回應教授的建議：先測模型原本的行為，再決定 persona 要往哪個方向調。

## 設計

| 因子 | 水準 |
| --- | --- |
| 需求來源 `need` | `complete` 一般題；`missing` 少一個關鍵數字；`ability` 一般題 + 系統提示「你只學過加法和減法」 |
| 運算 `op` | `addsub` 只需加減（12 題）；`muldiv` 需要乘除（12 題） |
| 語言 `lang` | `en`、`zh`（系統提示與題目同一種語言） |
| 模型 | Gemini 3.5 Flash Lite（API）、Qwen3-8B、Llama-3.1-8B（本機 vLLM） |

- 題目：UMWP「缺關鍵資訊」類的配對題（精讀 29），見 `items/pilot_items.json`；人工檢查用 `items/REVIEW.md`。
- `ability × addsub` 是對照組：只會加減的學生做加減題，理論上不需要求助。
- 工具：`ask_teacher(question)`、`submit_answer(answer)`、`skip(reason)`。系統提示只說明工具是什麼，不說什麼時候該用（避免像 UMWP 的 Instruction 條件一樣拉高求助率）。
- 老師是規則式的：缺條件題回答缺的那個數字，其他題目回「解題需要的資訊都在題目裡，請再仔細讀一次」。
- 每一回合最多 4 步；呼叫 `submit_answer`、`skip` 或只回文字就結束。

## 執行

```bash
# Gemini（每分鐘 12 次、每天最多 480 次，中斷後重跑會接續）
~/miniforge3/bin/python3 -I run_pilot.py --reps 3

# 本機模型（先用 vLLM 開伺服器，見下方）
~/miniforge3/bin/python3 -I run_pilot.py --model Qwen/Qwen3-8B-FP8 --base-url http://localhost:8011/v1 --no-think --reps 5

# 彙整與作圖
~/miniforge3/envs/adl_hw3_py311/bin/python analyze.py
```

結果：`results/<模型>.jsonl`（每個 episode 一行，含完整的工具呼叫紀錄）、`results/summary.csv`、`results/ask_rate.png`。
