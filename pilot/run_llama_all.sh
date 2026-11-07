#!/bin/zsh
# Llama-3.1-8B：Step 0（重複 5 次）→ Step 1 高求助 → Step 1 低求助
cd ~/BehaviorModeling/pilot
URL=http://localhost:8012/v1
M=meta-llama/Llama-3.1-8B-Instruct
~/miniforge3/bin/python3 -I run_pilot.py --model $M --base-url $URL --reps 5
for d in high low; do
  ~/miniforge3/bin/python3 -I run_step1.py --model $M --base-url $URL --direction $d --reps 3 --workers 8
done
echo ALL_DONE
