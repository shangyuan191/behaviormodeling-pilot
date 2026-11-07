#!/bin/zsh
# 反覆執行 Gemini 的 Step 0，直到全部完成。
# 每天的額度用完時 run_pilot.py 會停下來；這裡等到太平洋時間午夜（UTC 08:00，額度重置）後再接續。
cd ~/BehaviorModeling/pilot
while true; do
  ~/miniforge3/bin/python3 -I run_pilot.py --model gemini-3.5-flash-lite --reps 3 && break
  now=$(date -u +%s)
  next=$(date -u -d "$(date -u +%F) 08:05" +%s)
  (( next <= now )) && next=$(( next + 86400 ))
  echo "[$(date)] 今日額度已用完，等到 $(date -d @$next) 再繼續"
  sleep $(( next - now ))
done
echo "[$(date)] Gemini Step 0 全部完成"
