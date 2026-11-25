#!/bin/bash
# 38o VISAUDIT float (CI #344): farklı kare hızlarında 4 koşu aynı anda
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
i=0
for f in 10 15 20 20; do
  i=$((i+1))
  ( timeout 300 "$S/godot/godot" --headless --max-fps $f --path . -- --chapter=38o --autotest > /root/is/t38_$i.log 2>&1 ) &
done
wait
grep -h -E 'AUTOTEST (PASS|FAIL)|^VISAUDIT|SCRIPT ERROR' /root/is/t38_*.log | cut -c1-260 > /root/is/t38.txt
echo BITTI >> /root/is/t38.txt
