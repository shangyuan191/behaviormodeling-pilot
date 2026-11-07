#!/bin/zsh
# Qwen3-8B 開啟思考模式的 Step 1（高求助、低求助），跑完關閉伺服器、釋放 GPU。
cd ~/BehaviorModeling/pilot
E=~/miniforge3/envs/adl_hw3_py311
export PATH=$E/bin:/usr/local/cuda-13.0/bin:$PATH CUDA_HOME=/usr/local/cuda-13.0 CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=${GPU:-3}
$E/bin/vllm serve Qwen/Qwen3-8B-FP8 --port 8011 --gpu-memory-utilization 0.40 --max-model-len 8192 --max-num-seqs 8 \
  --enable-auto-tool-choice --tool-call-parser hermes > logs_vllm_qwen_think.txt 2>&1 &
SERVER=$!
until grep -q -E "Application startup complete|Error" logs_vllm_qwen_think.txt; do sleep 5; done
if grep -q "Application startup complete" logs_vllm_qwen_think.txt; then
  for d in high low; do
    ~/miniforge3/bin/python3 -I run_step1.py --model Qwen/Qwen3-8B-FP8 --base-url http://localhost:8011/v1 \
      --direction $d --reps 3 --workers 6
  done
fi
kill $SERVER
echo ALL_DONE
