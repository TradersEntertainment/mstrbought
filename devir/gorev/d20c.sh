#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
mkdir -p /root/is/d20c
timeout 300 $S/godot/godot --headless --path . res://tests/parse_check.tscn 2>&1 | grep -E "PARSECHECK|SCRIPT ERROR" > /root/is/d20c/ozet.txt
k() { timeout 500 $S/godot/godot --headless --max-fps 20 --path . -- --chapter=20 --autotest $2 > /root/is/d20c/k$1.txt 2>&1; echo "k$1 $2 | vis=$(grep -c VISAUDIT /root/is/d20c/k$1.txt) | err=$(grep -c "SCRIPT ERROR" /root/is/d20c/k$1.txt) | $(grep -o "AUTOTEST [A-Z]*" /root/is/d20c/k$1.txt | head -1) | $(grep -c "D20 hat_kapali" /root/is/d20c/k$1.txt) hat" >> /root/is/d20c/ozet.txt; }
(k 1 --difficulty=2; k 2 --difficulty=2; k 3 --difficulty=2; k 7 --difficulty=0) &
(k 4 --difficulty=2; k 5 --difficulty=2; k 6 --difficulty=2; k 8 "") &
wait
echo BITTI >> /root/is/d20c/ozet.txt
