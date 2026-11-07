#!/bin/zsh
# 2026-11-02：等 run_fix.sh 跑完後，用 pythonic 工具解析器重跑 Breeze2 的 Step 0 + Step 1。
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
PY=~/miniforge3/bin/python3
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID
PORT=8017
URL=http://localhost:$PORT/v1
NEED_MB=${NEED_MB:-14000}
LOG=logs_fix2.txt
VLOG=logs_vllm_fix2.txt
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

serve() {  # serve <model-path> <served-name> <tool-parser> [額外參數...]
  SERVE_ARGS=("$@")  # 給看門狗重啟用
  local model=$1 name=$2 parser=$3; shift 3
  for attempt in 1 2 3; do
    local g=""
    until [ -n "$g" ]; do g=$(pick_gpu); [ -z "$g" ] && sleep 120; done
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
    grep -q -E "KeyError|not supported|ModuleNotFound" "logs_vllm_fail_${name//\//_}_$attempt.txt" && return 1  # 設定錯誤，重試無用
    sleep 300
  done
  return 1
}

gen_tokens() {  # vLLM 累計產生的 token 數（伺服器沒回應時印 dead）
  curl -s -m 10 localhost:$PORT/metrics | awk '/^vllm:generation_tokens_total/ {s += $2; n++} END {print n ? s : "dead"}'
}

retry() {  # 可續跑的 Python 腳本，失敗重試最多 5 次。
  # 看門狗：腳本執行中 vLLM 連續 15 分鐘沒產生任何 token → 判定卡住（11/2 10:08 發生過），
  # 停掉腳本、重啟伺服器再續跑。
  for i in 1 2 3 4 5; do
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

trap 'stop_server' EXIT
until grep -q FIX_DONE logs_fix.txt 2>/dev/null; do sleep 120; done
say "===== 開始（run_fix.sh 已完成）====="
# Breeze2 用 Python 函式語法呼叫工具 → pythonic 解析器（舊資料見 results/_invalid_breeze2_llama3json_parser）
new_model ~/BehaviorModeling/models/breeze2-8b-llm MediaTek-Research/Llama-Breeze2-8B-Instruct pythonic --quantization fp8
say "===== FIX2_DONE ====="
