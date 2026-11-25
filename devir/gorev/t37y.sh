#!/bin/bash
# 37o =lose yük altında: 4 koşu aynı anda, tam günlük
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
for i in 1 2 3 4; do
  ( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=37o --autotest=lose > /root/is/t37y_$i.log 2>&1 ) &
done
wait
grep -h -E 'AUTOTEST (PASS|FAIL)|WAVERUNNER' /root/is/t37y_*.log > /root/is/t37y.txt
echo BITTI >> /root/is/t37y.txt
