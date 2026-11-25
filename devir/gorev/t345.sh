#!/bin/bash
# CI #345 düzeltmeleri (36b yürüyüş + Giustiniani yeri, EsyaFizik zorla dondurmada zemin): hedefli, 4 kol, 20 FPS
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  out=$(timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" 2>&1)
  echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|WARN_FX_STUCK|^WARN_FLY_ITEM|^VISAUDIT |^WALKTHRU|^HELDAUDIT|^ARMAUDIT|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^GORUNMEZZEMIN |^ALETAUDIT |^DONUKAUDIT |^YUKLEMEAUDIT_KESIN " | awk '!seen[$0]++' | cut -c1-220
  [ -z "$(echo "$out" | grep 'AUTOTEST PASS')" ] && echo "YOK_PASS $*"
}
( out=$(timeout 120 "$S/godot/godot" --headless --path . res://tests/parse_check.tscn 2>&1); echo "$out" | grep -E "PARSECHECK|Parse Error|Compile Error" | head -3
  for i in 1 2; do timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E "ESYATEST (PASS|FAIL)|SCRIPT ERROR"; done
  kos --chapter=36b --autotest ) > /root/is/t345_1.txt &
( kos --chapter=36b --autotest=leave; kos --chapter=36b --autotest; kos --chapter=20 --autotest; kos --chapter=26 --autotest ) > /root/is/t345_2.txt &
( kos --chapter=8y --autotest; kos --chapter=37o --autotest; kos --chapter=30o --autotest ) > /root/is/t345_3.txt &
( kos --chapter=31o --autotest; kos --chapter=32o --autotest; kos --chapter=36b --autotest=leave; kos --chapter=38o --autotest ) > /root/is/t345_4.txt &
wait
cat /root/is/t345_[1-4].txt > /root/is/t345.txt
echo BITTI >> /root/is/t345.txt
