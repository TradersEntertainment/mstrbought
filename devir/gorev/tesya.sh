#!/bin/bash
# ESYATEST gomuk=1 (CI #345): 6 kopya aynı anda (yük), tam günlük
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
for i in 1 2 3 4 5 6; do
  ( timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/esya_fizik.tscn > /root/is/tesya_$i.log 2>&1 ) &
done
wait
for i in 1 2 3 4 5 6; do echo "== $i"; grep -E 'ESYATEST (PASS|FAIL)|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|gomuk' /root/is/tesya_$i.log | cut -c1-300 | head -8; done > /root/is/tesya.txt
echo BITTI >> /root/is/tesya.txt
