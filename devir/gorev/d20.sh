#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
mkdir -p /root/is/d20
for i in 1 2 3 4 5 6 7 8; do
  timeout 400 $S/godot/godot --headless --path . -- --chapter=20 --autotest --difficulty=2 > /root/is/d20/k$i.txt 2>&1
  echo "k$i $(grep -c VISAUDIT /root/is/d20/k$i.txt) $(grep -o "AUTOTEST [A-Z]*" /root/is/d20/k$i.txt | head -1)" >> /root/is/d20/ozet.txt
done
echo BITTI >> /root/is/d20/ozet.txt
