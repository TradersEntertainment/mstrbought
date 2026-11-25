#!/bin/bash
# ESYATEST gömük sondası: eski esya_fizik.gd (HEAD) ve yeni
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
cp scripts/level/esya_fizik.gd /root/is/esya_fizik_yeni.gd
git show HEAD:scripts/level/esya_fizik.gd > scripts/level/esya_fizik.gd
timeout 120 "$S/godot/godot" --headless --path . -s tests/_ci344/esya_gomuk_sonda.gd 2>&1 | grep -E 'ESYAGOMUKSONDA|ESYAAUDIT|SCRIPT ERROR: (Parse|Invalid|Cannot|Attempt)' | sed 's/^/ESKI /' > /root/is/tgomuk.txt
cp /root/is/esya_fizik_yeni.gd scripts/level/esya_fizik.gd
timeout 120 "$S/godot/godot" --headless --path . -s tests/_ci344/esya_gomuk_sonda.gd 2>&1 | grep -E 'ESYAGOMUKSONDA|ESYAAUDIT|SCRIPT ERROR: (Parse|Invalid|Cannot|Attempt)' | sed 's/^/YENI /' >> /root/is/tgomuk.txt
echo BITTI >> /root/is/tgomuk.txt
