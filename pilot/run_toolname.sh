#!/bin/zsh
# 2026-11-03：Qwen3 開啟思考補跑 CAPS 與第三人稱（先 CAPS，再第三人稱低求助、高求助）。
#  - 每個模型只開一次伺服器就把所有實驗跑完（換模型時才可能被別人搶走 GPU）
#  - 記憶體需求降到 12.5 GB（和最早成功跑過的 0.40×32 GB 設定相當），比較容易等到空檔
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
PY=~/miniforge3/bin/python3
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID
PORT=8022
URL=http://localhost:$PORT/v1
NEED_MB=${NEED_MB:-12500}
LOG=logs_toolname.txt
VLOG=logs_vllm_toolname.txt
SERVER=""

say() { echo "[$(date '+%F %T')] $*" | tee -a $LOG; }

pick_gpu() {  # 剩餘記憶體最多、且 >= NEED_MB+1000 的 GPU；印出 "index total_mb"
  nvidia-smi --query-gpu=index,memory.free,memory.total --format=csv,noheader,nounits | sort -t, -k2 -nr | \
    awk -F', ' -v need=$((NEED_MB + 1000)) '$2 >= need {print $1, $3; exit}'
}

stop_server() {
  [ -n "$SERVER" ] && kill $SERVER 2>/dev/null
  for i in {1..30}; do kill -0 $SERVER 2>/dev/null || break; sleep 2; done
  [ -n "$SERVER" ] && kill -9 $SERVER 2>/dev/null
  pkill -f "vllm serve .*--port $PORT" 2>/dev/null; sleep 10
  SERVER=""
}

VLM_CHAIN_A=2619903  # VLM 專案 overnight_queue.sh 的 A 串（LLaVA → Qwen3-VL-8B → InternVL）
wait_next() {  # 研究者 11/2 決定：VLM A 串還在時每 2 分鐘才搶一次 GPU（讓 VLM 先跑），但每 5 秒確認 A 串是否結束；
  # A 串一結束就立刻回去檢查 GPU（最多晚約 5 秒），之後每 10 秒檢查一次，避免空檔被別人搶走
  if kill -0 $VLM_CHAIN_A 2>/dev/null; then
    for i in {1..24}; do sleep 5; kill -0 $VLM_CHAIN_A 2>/dev/null || { say "VLM A 串已結束，改為每 10 秒檢查 GPU"; return; }; done
  else
    sleep 10
  fi
}

serve() {  # serve <model-path> <served-name> <tool-parser> [額外參數...]
  SERVE_ARGS=("$@")  # 給看門狗重啟用
  local model=$1 name=$2 parser=$3; shift 3
  local attempt=0 fails=0
  while [ $fails -lt 3 ] && [ $attempt -lt 40 ]; do  # 記憶體被搶走的失敗不算在 3 次內（但總共最多 40 次）；其他錯誤最多 3 次
    attempt=$((attempt + 1))
    local g=""
    until [ -n "$g" ]; do g=$(pick_gpu); [ -z "$g" ] && wait_next; done
    local gpu=${g% *} total=${g#* }
    local util=$(python3 -c "print(round($NEED_MB/$total, 3))")
    say "啟動 $name（GPU $gpu，util $util，第 $attempt 次）"
    CUDA_VISIBLE_DEVICES=$gpu $E/bin/vllm serve $model --served-model-name $name --port $PORT \
      --gpu-memory-utilization $util --max-model-len 8192 --max-num-seqs 8 \
      --enable-auto-tool-choice --tool-call-parser $parser "$@" > $VLOG 2>&1 &
    SERVER=$!
    for i in {1..240}; do  # 最多等 20 分鐘
      curl -sf localhost:$PORT/health >/dev/null && { say "$name 就緒"; return 0; }
      kill -0 $SERVER 2>/dev/null || break
      sleep 5
    done
    say "$name 啟動失敗：$(grep -E 'Error' $VLOG | tail -1)"
    cp $VLOG "logs_vllm_fail_${name//\//_}_$attempt.txt"
    stop_server
    local f="logs_vllm_fail_${name//\//_}_$attempt.txt"
    grep -q -E "KeyError|not supported|ModuleNotFound" $f && return 1  # 設定錯誤，重試無用
    grep -q -E "Free memory on device|out of memory|No available memory for the cache" $f || fails=$((fails + 1))
    kill -0 $VLM_CHAIN_A 2>/dev/null && sleep 300 || sleep 30  # A 串結束後失敗只等 30 秒
  done
  return 1
}

gen_tokens() {  # vLLM 累計產生的 token 數（伺服器沒回應時印 dead）
  curl -s -m 10 localhost:$PORT/metrics | awk '/^vllm:generation_tokens_total/ {s += $2; n++} END {print n ? s : "dead"}'
}

retry() {  # 可續跑的 Python 腳本，失敗重試最多 5 次。
  # 看門狗：腳本執行中 vLLM 連續 15 分鐘沒產生任何 token → 判定卡住（11/2 10:08 發生過），
  # 停掉腳本、重啟伺服器再續跑。
  for i in 1 2 3 4 5 6 7 8 9 10; do
    "$@" &
    local pid=$! last="" still=0 hung=0
    while kill -0 $pid 2>/dev/null; do
      sleep 60
      local tok=$(gen_tokens)
      if [ "$tok" = "$last" ]; then still=$((still + 1)); else still=0; last=$tok; fi
      if [ $still -ge 15 ]; then
        say "vLLM 15 分鐘沒有產生 token（$tok），判定卡住，重啟伺服器"
        cp $VLOG "logs_vllm_hung_$(date +%m%d_%H%M).txt"
        kill $pid 2>/dev/null; sleep 5; kill -9 $pid 2>/dev/null
        hung=1; break
      fi
    done
    wait $pid && [ $hung -eq 0 ] && return 0
    say "失敗（第 $i 次）：$*"
    if [ $hung -eq 1 ] || [ "$(gen_tokens)" = "dead" ]; then
      stop_server
      serve "${SERVE_ARGS[@]}" || { say "伺服器無法重啟，放棄：$*"; return 1; }
    fi
    sleep 60
  done
  return 1
}

run_new_experiments() {  # 量表、CAPS、第三人稱 Step 1
  local model=$1; shift
  retry $PY -I run_survey.py --model $model --base-url $URL "$@" --reps 3 --workers 8
  retry $PY -I run_caps.py --model $model --base-url $URL "$@" --reps 3 --workers 8
  for d in low high; do
    retry $PY -I run_step1.py --model $model --base-url $URL "$@" --direction $d --perspective third --reps 3 --workers 8
  done
}

new_model() {  # new_model <model-path> <served-name> <tool-parser> [額外參數...]：Step 0 + Step 1
  local name=$2
  if serve "$@"; then
    if $PY -I smoke_tools.py $name $URL | tee -a $LOG; [ ${pipestatus[1]} -eq 0 ]; then
      say "$name 通過工具呼叫檢查，開始 Step 0"
      retry $PY -I run_pilot.py --model $name --base-url $URL --reps 5
      for d in high low; do
        retry $PY -I run_step1.py --model $name --base-url $URL --direction $d --reps 3 --workers 8
      done
      say "$name 完成"
    else
      say "SKIP $name：工具呼叫無法解析（見上方試跑輸出）"
    fi
  else
    say "SKIP $name：vLLM 無法啟動"
  fi
  stop_server
}

full_model() {  # 新模型：工具呼叫檢查 → Step 0 → Step 1 → 量表（修正版）→ CAPS → 第三人稱，同一個伺服器跑完
  local name=$2
  if serve "$@"; then
    if $PY -I smoke_tools.py $name $URL | tee -a $LOG; [ ${pipestatus[1]} -eq 0 ]; then
      say "$name 通過工具呼叫檢查，開始 Step 0"
      retry $PY -I run_pilot.py --model $name --base-url $URL --reps 5
      for d in high low; do
        retry $PY -I run_step1.py --model $name --base-url $URL --direction $d --reps 3 --workers 8
      done
      say "$name Step 0/1 完成，開始新實驗（量表、CAPS、第三人稱）"
      run_new_experiments $name
      say "$name 全部完成"
    else
      say "SKIP $name：工具呼叫無法解析（見上方試跑輸出）"
    fi
  else
    say "SKIP $name：vLLM 無法啟動"
  fi
  stop_server
}


trap 'stop_server' EXIT
ST=logs_toolname_stderr.txt
step() {  # step <說明> <run_step1 參數...>：成功或失敗分開記錄
  local what=$1; shift
  if retry $PY -I run_step1.py --base-url $URL --workers 8 "$@" 2>>$ST; then say "$what 完成"; else say "$what 未完成（重試用盡）"; fi
}
say "===== 開始（工具名稱檢查＋Llama L0 補樣本）====="
if serve Qwen/Qwen3-8B-FP8 Qwen/Qwen3-8B-FP8 hermes; then
  for t in ask_for_help raise_hand_neutral; do
    step "Qwen3 關閉思考 $t" --model Qwen/Qwen3-8B-FP8 --no-think --direction low --reps 3 --help-tool $t
  done
fi
stop_server
if serve meta-llama/Llama-3.1-8B-Instruct meta-llama/Llama-3.1-8B-Instruct llama3_json --quantization fp8; then
  step "Llama L0 補樣本" --model meta-llama/Llama-3.1-8B-Instruct --direction high --personas L0 --rep-start 3 --reps 9 \
    --out results/step1_extra/Llama-3.1-8B-Instruct-high-L0extra.jsonl
  for t in ask_for_help raise_hand_neutral; do
    step "Llama $t" --model meta-llama/Llama-3.1-8B-Instruct --direction low --reps 3 --help-tool $t
  done
fi
stop_server
$PY -I analyze_toolname.py > results/toolname_summary.txt 2>>$ST && say "分析完成：results/toolname_summary.txt"
say "===== TOOLNAME_DONE ====="
