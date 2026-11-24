#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
cd /home/user/nothistorygame || exit 1
O=/root/is/tek127.txt
: > $O
F="AUTOTEST (PASS|FAIL|TIMEOUT)|SCRIPT ERROR|^VISAUDIT |^WALKTHRU|^GORUNMEZZEMIN |^ALETAUDIT |^DONUKAUDIT "
( for i in 1 2 3 4; do echo "26nophoto#$i $(timeout 300 $G --headless --max-fps 20 --path . -- --chapter=26 --autotest=nophoto 2>&1 | grep -E "$F" | cut -c1-200 | tr "\n" " ")" >> $O; done ) &
( for i in 1 2 3 4; do echo "31opetrion#$i $(timeout 300 $G --headless --max-fps 20 --path . -- --chapter=31o --autotest=petrion_bad 2>&1 | grep -E "$F" | cut -c1-200 | tr "\n" " ")" >> $O; done ) &
( for i in 1 2 3 4; do echo "esya#$i $(timeout 300 $G --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E "ESYATEST (PASS|FAIL)|ESYATEST sayac|SCRIPT ERROR" | cut -c1-200 | tr "\n" " ")" >> $O; done ) &
wait
echo BITTI >> $O
