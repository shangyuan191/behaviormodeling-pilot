#!/bin/zsh
# Qwen3-8B（關閉思考模式）Step 1：先跑高求助，再跑低求助。
cd ~/BehaviorModeling/pilot
for d in high low; do
  ~/miniforge3/bin/python3 -I run_step1.py --model Qwen/Qwen3-8B-FP8 --base-url http://localhost:8011/v1 \
    --no-think --direction $d --reps 3 --workers 8
done
