#!/bin/bash
# ESYATEST gömük izi: 6 tur × 6 (düzeltmeden sonra) kopya (ESYA_IZ=1)
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
: > /root/is/tesya4.txt
for tur in 1 2 3 4 5 6; do
  for i in 1 2 3 4 5 6; do
    ( ESYA_IZ=1 timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/esya_fizik.tscn > /root/is/tesya4_$i.log 2>&1 ) &
  done
  wait
  for i in 1 2 3 4 5 6; do echo "== $tur.$i $(grep -cE 'ESYATEST PASS' /root/is/tesya4_$i.log)"; grep -E '^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|ESYAIZ' /root/is/tesya4_$i.log | cut -c1-400; done >> /root/is/tesya4.txt
done
echo BITTI >> /root/is/tesya4.txt
