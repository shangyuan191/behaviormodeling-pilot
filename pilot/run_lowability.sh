#!/bin/zsh
# 2026-11-13：補跑「低求助 persona × 只學過加減」題（Step 1 原設計只配缺條件題）。
#  只跑 15 個低求助 persona；L0 與中性對照沿用高求助那次的 ability 資料（提示詞完全相同）。
#  輸出：results/step1_extra/<model>-low-ability.jsonl（每組設定 2,160 回合）
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
PY=~/miniforge3/bin/python3
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID
PORT=8021
URL=http://localhost:$PORT/v1
NEED_MB=${NEED_MB:-12500}
LOG=logs_lowability.txt
VLOG=logs_vllm_lowability.txt
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

VLM_CHAIN_A=999999999  # 11/13：VLM A 串早已結束，佔位用的不存在 PID
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

LOWP=L-0-1,L-0-2,L-0-3,L-T-1,L-T-2,L-T-3,L-TA-1,L-TA-2,L-TA-3,L-TAC-1,L-TAC-2,L-TAC-3,L-TACT-1,L-TACT-2,L-TACT-3
low_ability() {  # low_ability <served-name> <輸出檔 tag> [run_step1 額外參數...]
  local name=$1 tag=$2; shift 2
  retry $PY -I run_step1.py --model $name --base-url $URL --direction low --needs ability --personas $LOWP \
    --reps 3 --workers 8 --out results/step1_extra/$tag-low-ability.jsonl "$@"
  say "$tag 完成：$(wc -l < results/step1_extra/$tag-low-ability.jsonl) / 2160 行"
}

trap 'stop_server' EXIT
say "===== 開始（低求助 × 只學過加減）====="
# Llama 已於 11/13 16:57 跑完（2160 行）；第一次佇列的 Qwen2.5 在 435 行時 vLLM 卡住（Running 8, 0 tok/s），改加 --enforce-eager 重跑
if serve Qwen/Qwen2.5-7B-Instruct Qwen/Qwen2.5-7B-Instruct hermes --quantization fp8 --enforce-eager; then
  low_ability Qwen/Qwen2.5-7B-Instruct Qwen2.5-7B-Instruct
fi
stop_server
if serve ibm-granite/granite-3.3-8b-instruct ibm-granite/granite-3.3-8b-instruct granite --quantization fp8 \
    --chat-template templates/granite33_tools.jinja; then
  low_ability ibm-granite/granite-3.3-8b-instruct granite-3.3-8b-instruct
fi
stop_server
# Qwen3 放最後：開啟思考最慢；11/4 曾卡住，--enforce-eager 可解
if serve Qwen/Qwen3-8B-FP8 Qwen/Qwen3-8B-FP8 hermes --enforce-eager; then
  low_ability Qwen/Qwen3-8B-FP8 Qwen3-8B-FP8-nothink --no-think
  low_ability Qwen/Qwen3-8B-FP8 Qwen3-8B-FP8
fi
stop_server
say "===== LOWABILITY_DONE ====="
