#!/bin/zsh
# 第二段排程：等 run_queue.sh 跑完後，依序對新模型跑 Step 0 與 Step 1。
# 每個模型先用 smoke_tools.py 確認工具呼叫可以解析；不通過就跳過並記錄。
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
PY=~/miniforge3/bin/python3
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID
PORT=8014
URL=http://localhost:$PORT/v1

until grep -q QUEUE_DONE logs_queue.txt 2>/dev/null; do sleep 60; done

pick_gpu() {  # 挑剩餘記憶體最多、且至少 14 GB 的 GPU（依 PCI 編號）
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | \
    awk -F', ' '$2 >= 14000 {print $1; exit}'
}

serve() {  # serve <model> <tool-parser> [額外參數...]；啟動失敗回傳非 0
  local model=$1 parser=$2; shift 2
  local gpu=""
  until [ -n "$gpu" ]; do gpu=$(pick_gpu); [ -z "$gpu" ] && sleep 120; done
  echo "[$(date)] 在 GPU $gpu 啟動 $model"
  CUDA_VISIBLE_DEVICES=$gpu $E/bin/vllm serve $model --port $PORT --gpu-memory-utilization 0.40 --max-model-len 8192 \
    --max-num-seqs 8 --enable-auto-tool-choice --tool-call-parser $parser "$@" > logs_vllm_queue2.txt 2>&1 &
  SERVER=$!
  until grep -q -E "Application startup complete|Error" logs_vllm_queue2.txt || ! kill -0 $SERVER 2>/dev/null; do sleep 5; done
  grep -q "Application startup complete" logs_vllm_queue2.txt
}

run_model() {  # run_model <model> <tool-parser> [額外參數...]
  local model=$1
  if serve "$@"; then
    if $PY -I smoke_tools.py $model $URL; then
      echo "[$(date)] $model 通過工具呼叫檢查，開始 Step 0"
      $PY -I run_pilot.py --model $model --base-url $URL --reps 5
      for d in high low; do
        $PY -I run_step1.py --model $model --base-url $URL --direction $d --reps 3 --workers 8
      done
      echo "[$(date)] $model 完成"
    else
      echo "[$(date)] SKIP $model：工具呼叫無法解析（見上方試跑輸出）"
    fi
  else
    echo "[$(date)] SKIP $model：vLLM 無法啟動，最後的錯誤："
    grep -E "Error" logs_vllm_queue2.txt | tail -3
  fi
  kill $SERVER 2>/dev/null; sleep 20
  cp logs_vllm_queue2.txt "logs_vllm_${model//\//_}.txt"
}

# 依研究者決定的優先順序
run_model MediaTek-Research/Llama-Breeze2-8B-Instruct llama3_json --trust-remote-code --quantization fp8 \
  --limit-mm-per-prompt '{"image": 0}'
run_model mistralai/Ministral-8B-Instruct-2410 mistral --quantization fp8
run_model ibm-granite/granite-3.3-8b-instruct granite --quantization fp8
run_model Qwen/Qwen2.5-7B-Instruct hermes --quantization fp8

echo "[$(date)] QUEUE2_DONE"
