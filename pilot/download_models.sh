#!/bin/zsh
# 下載新一輪要比較的開源模型（每個 --exclude 要分開寫）
H=~/miniforge3/envs/adl_hw3_py311/bin/hf
for m in MediaTek-Research/Llama-Breeze2-8B-Instruct mistralai/Ministral-8B-Instruct-2410 \
         ibm-granite/granite-3.3-8b-instruct Qwen/Qwen2.5-7B-Instruct; do
  $H download $m --exclude "original/*" --exclude "*.gguf" --exclude "consolidated*" > /dev/null 2>&1 \
    && echo "OK $m $(du -shL ~/.cache/huggingface/hub/models--${m//\//--}/snapshots | cut -f1)" || echo "FAIL $m"
done
echo DOWNLOAD_DONE
