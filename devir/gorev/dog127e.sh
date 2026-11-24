#!/bin/bash
# 0.99.127 doğrulama E (kapı geçidi kule eteği + G18): sözleşme altılısı, 8y çeşitleri + =yuru, kapılı bölümler (20 FPS),
# ZFIGHT 8y/26/31o/26o/10h/13/24
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
O=$S/dog127e.txt
F='AUTOTEST (PASS|FAIL|TIMEOUT)|SCRIPT ERROR|^VISAUDIT|^WALKTHRU|^HELDAUDIT|^ARMAUDIT|WARN_FX_STUCK|^WARN_FLY_ITEM|WARN_VOID_TELEPORT|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^HAREKETAUDIT'
cd /home/user/nothistorygame || exit 1
: > "$O"
echo "DAL $(git rev-parse --short HEAD)+degisiklik basla $(date -u +%H:%M)" >> "$O"
mkdir -p /root/is/havada8y_sonra; : > /root/is/c0.txt; : > /root/is/c2.txt; : > /root/is/c3.txt; : > /root/is/c4.txt
true
( timeout 300 "$G" --headless --path . res://tests/_ist/sur_sozlesme.tscn 2>&1 | grep -E '^SURSOZLESME (PASS|FAIL)|SCRIPT ERROR' | tail -2 > /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_denetim.tscn 2>&1 | grep -E '^SUROYUN nokta|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E 'ESYATEST (PASS|FAIL)|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_yuru.tscn 2>&1 | grep -E 'WALKTHRU OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tasima11_halic_sonda.tscn 2>&1 | grep -E 'HALICSONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tur14_marmara_sonda.tscn 2>&1 | grep -E 'MARMARASONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  for f in chapter8y chapter26 chapter31o chapter26o chapter10h chapter13 chapter24 chapter20; do echo "ZFIGHT $f: $(timeout 150 "$G" --headless --path . -s tests/zfight_check.gd -- res://scenes/$f.tscn 2>&1 | grep -c '^ZFIGHT')" >> /root/is/c1.txt; done ) &
( for v in "" "=warn" "=dep" "=opened" "=honest" "=hikmet" "=sinerji" "=yuru" "=next"; do
    echo "[8y$v] $(timeout 300 "$G" --headless --max-fps 20 --path . -- --chapter=8y --autotest$v 2>&1 | grep -E "$F|T10_8Y yuru|YURU" | awk '!seen[$0]++' | tr '\n' ' ' | cut -c1-400)" >> /root/is/c2.txt
  done ) &
( for a in "--chapter=26 --autotest" "--chapter=26 --autotest=nophoto" "--chapter=26o --autotest" "--chapter=31o --autotest" "--chapter=31o --autotest=late" "--chapter=10h --autotest" "--chapter=12b --autotest" "--chapter=13 --autotest=city" "--chapter=23 --autotest" "--chapter=24 --autotest"; do
    echo "[$a] $(timeout 300 "$G" --headless --max-fps 20 --path . -- $a 2>&1 | grep -E "$F" | awk '!seen[$0]++' | tr '\n' ' ' | cut -c1-400)" >> /root/is/c3.txt
  done ) &
( for a in "--chapter=20 --autotest" "--chapter=20 --autotest --difficulty=2" "--chapter=22o --autotest" "--chapter=41o --autotest" "--chapter=42b --autotest" "--chapter=6 --autotest=byz" "--chapter=7 --autotest=byz"; do
    echo "[$a] $(timeout 300 "$G" --headless --max-fps 20 --path . -- $a 2>&1 | grep -E "$F" | awk '!seen[$0]++' | tr '\n' ' ' | cut -c1-400)" >> /root/is/c4.txt
  done ) &
wait
cat /root/is/c0.txt /root/is/c1.txt /root/is/c2.txt /root/is/c3.txt /root/is/c4.txt >> "$O"
echo "BITTI $(date -u +%H:%M)" >> "$O"
