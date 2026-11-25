#!/bin/bash
# 36b VISAUDIT overlap (CI #345, (-11.1,21.0) savunucu ↔ Person): --sonda36 ile 4 kopya aynı anda, 2 tur
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
for tur in 1 2; do
  for i in 1 2 3 4; do
    ( timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- --chapter=36b --autotest --sonda36 > /root/is/t36b_${tur}_$i.log 2>&1 ) &
  done
  wait
done
for f in /root/is/t36b_*.log; do echo "== $f"; grep -E 'AUTOTEST (PASS|FAIL)|^VISAUDIT |SONDA36YAKIN|SCRIPT ERROR|WALKTHRU|GORUNMEZ' "$f" | cut -c1-300 | head -12; grep '^SONDA36 t=' "$f" | tail -1 | cut -c1-80; done > /root/is/t36b.txt
echo BITTI >> /root/is/t36b.txt
