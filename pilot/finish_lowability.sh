#!/bin/zsh
# 11/13：等 run_lowability.sh 結束，自動產出結果表 results/lowability_summary.txt
cd ~/BehaviorModeling/pilot
while pgrep -f "run_lowability.sh" >/dev/null; do sleep 60; done
{ echo "產出時間：$(date '+%F %T')"; echo; grep -E "完成|DONE|放棄|SKIP|卡住" logs_lowability.txt; echo; wc -l results/step1_extra/*-low-ability.jsonl; python3 -I analyze_lowability.py; } > results/lowability_summary.txt 2>&1
