#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
mkdir -p /root/is/d20b
timeout 300 $S/godot/godot --headless --path . res://tests/parse_check.tscn 2>&1 | grep -E "PARSECHECK|SCRIPT ERROR" > /root/is/d20b/ozet.txt
k() { timeout 500 $S/godot/godot --headless --path . -- --chapter=20 "$@" > /root/is/d20b/$1$2.txt 2>&1; echo "$* | $(grep -c VISAUDIT /root/is/d20b/$1$2.txt) | $(grep -c "SCRIPT ERROR" /root/is/d20b/$1$2.txt) | $(grep -o "AUTOTEST [A-Z]*" /root/is/d20b/$1$2.txt | head -1) | $(grep -o "D20 hat_kapali.*" /root/is/d20b/$1$2.txt | head -1)" >> /root/is/d20b/ozet.txt; }
(k --autotest; k --autotest=tape; k --autotest=late; k --autotest=hit; k --autotest=next) &
(k --autotest=lose; k --autotest=niko_idle; k --autotest=idle; k --autotest --difficulty=0; k --autotest --difficulty=2) &
wait
echo BITTI >> /root/is/d20b/ozet.txt
