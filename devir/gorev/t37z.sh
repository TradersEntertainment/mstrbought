#!/bin/bash
# 37o düzeltmesi: =lose ×4 aynı anda (yük), ardından "" ve =trespass ×1 aynı anda
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
for i in 1 2 3 4; do
  ( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=37o --autotest=lose > /root/is/t37z_$i.log 2>&1 ) &
done
wait
( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=37o --autotest > /root/is/t37z_5.log 2>&1 ) &
( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=37o --autotest=trespass > /root/is/t37z_6.log 2>&1 ) &
( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=37o --autotest=lose > /root/is/t37z_7.log 2>&1 ) &
wait
grep -h -E 'AUTOTEST (PASS|FAIL)|WAVERUNNER|SCRIPT ERROR|TASIMA6FAZ faz=barikat' /root/is/t37z_*.log > /root/is/t37z.txt
echo BITTI >> /root/is/t37z.txt
