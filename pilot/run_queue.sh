#!/bin/zsh
# 依序對多個模型跑下一輪實驗（量表、CAPS、第三人稱），一次只開一個 vLLM 伺服器。
# 用法：./run_queue.sh            （會先等開啟思考的 Qwen Step 1 跑完）
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
PY=~/miniforge3/bin/python3
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID
PORT=8013
URL=http://localhost:$PORT/v1

# 等前一個工作（開啟思考的 Qwen Step 1）結束
until grep -q ALL_DONE logs_step1_qwen_think.txt 2>/dev/null; do sleep 60; done

pick_gpu() {  # 挑剩餘記憶體最多、且至少 14 GB 的 GPU（依 PCI 編號）
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | sort -t, -k2 -nr | \
    awk -F', ' '$2 >= 14000 {print $1; exit}'
}

serve() {  # serve <model> <tool-parser> [額外參數...]
  local model=$1 parser=$2; shift 2
  local gpu=""
  until [ -n "$gpu" ]; do gpu=$(pick_gpu); [ -z "$gpu" ] && sleep 120; done
  echo "[$(date)] 在 GPU $gpu 啟動 $model"
  CUDA_VISIBLE_DEVICES=$gpu $E/bin/vllm serve $model --port $PORT --gpu-memory-utilization 0.40 --max-model-len 8192 \
    --max-num-seqs 8 --enable-auto-tool-choice --tool-call-parser $parser "$@" > logs_vllm_queue.txt 2>&1 &
  SERVER=$!
  until grep -q -E "Application startup complete|Error" logs_vllm_queue.txt; do sleep 5; done
  grep -q "Application startup complete" logs_vllm_queue.txt
}

run_new_experiments() {  # run_new_experiments <model> [--no-think]
  local model=$1; shift
  $PY -I run_survey.py --model $model --base-url $URL "$@" --reps 3 --workers 8
  $PY -I run_caps.py --model $model --base-url $URL "$@" --reps 3 --workers 8
  for d in low high; do
    $PY -I run_step1.py --model $model --base-url $URL "$@" --direction $d --perspective third --reps 3 --workers 8
  done
}

# 1. Qwen3-8B：關閉思考跑全部新實驗；開啟思考只補量表（和開啟思考的 Step 1 配對）
if serve Qwen/Qwen3-8B-FP8 hermes; then
  run_new_experiments Qwen/Qwen3-8B-FP8 --no-think
  $PY -I run_survey.py --model Qwen/Qwen3-8B-FP8 --base-url $URL --reps 3 --workers 8
fi
kill $SERVER; sleep 20

# 2. Llama-3.1-8B
if serve meta-llama/Llama-3.1-8B-Instruct llama3_json --quantization fp8; then
  run_new_experiments meta-llama/Llama-3.1-8B-Instruct
fi
kill $SERVER; sleep 20

echo "[$(date)] QUEUE_DONE"
