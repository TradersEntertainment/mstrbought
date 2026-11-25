#!/bin/bash
# 0.99.128 ön doğrulama: içe aktarma + ayrıştırma + 13 =city (perde), 8y, 24, 31o (YUKLEMEAUDIT), 20 FPS
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
cd /home/user/nothistorygame || exit 1
O=/root/is/dog128.txt
: > $O
timeout 900 $G --headless --path . --import > /root/is/dog128_import.log 2>&1
echo "IMPORT script_error=$(grep -c 'SCRIPT ERROR' /root/is/dog128_import.log) parse_error=$(grep -c 'Parse Error' /root/is/dog128_import.log)" >> $O
echo "PARSE $(timeout 300 $G --headless --path . res://tests/parse_check.tscn 2>&1 | grep -E 'PARSECHECK|SCRIPT ERROR' | head -3 | tr '\n' ' ')" >> $O
F="AUTOTEST (PASS|FAIL|TIMEOUT)|SCRIPT ERROR|^VISAUDIT |^WALKTHRU|^GORUNMEZZEMIN |^ALETAUDIT |^DONUKAUDIT |^YUKLEMEAUDIT"
for a in "13 =city" "8y " "24 " "31o " "26 " ; do
  set -- $a
  echo "$1$2 $(timeout 600 $G --headless --max-fps 20 --path . -- --chapter=$1 --autotest$2 2>&1 | grep -E "$F" | cut -c1-260 | tr "\n" " ")" >> $O
done
echo BITTI >> $O
