#!/bin/bash
# CityLife devriye düzeltmesi: devriyeli bölümler hedefli, 4 kol aynı anda, 20 FPS (CI koşulu)
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  out=$(timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" 2>&1)
  echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|WARN_FX_STUCK|^WARN_FLY_ITEM|^VISAUDIT |^WALKTHRU|^HELDAUDIT|^ARMAUDIT|^GORUNMEZZEMIN |^ALETAUDIT |^DONUKAUDIT |^YUKLEMEAUDIT_KESIN " | awk '!seen[$0]++' | cut -c1-220
}
( for v in "" "=lose" "=hooks_ok" "=hooks_bad"; do kos --chapter=38o --autotest$v; done > /root/is/t38h_1.txt ) &
( for v in "" "=hit" "=lose"; do kos --chapter=20 --autotest$v; done; kos --chapter=20o --autotest > /root/is/t38h_2b.txt; ) > /root/is/t38h_2.txt &
( kos --chapter=26 --autotest; kos --chapter=30o --autotest; kos --chapter=37o --autotest; kos --chapter=37o --autotest=lose ) > /root/is/t38h_3.txt &
( kos --chapter=31o --autotest; kos --chapter=24 --autotest; kos --chapter=36b --autotest ) > /root/is/t38h_4.txt &
wait
cat /root/is/t38h_1.txt /root/is/t38h_2.txt /root/is/t38h_2b.txt /root/is/t38h_3.txt /root/is/t38h_4.txt > /root/is/t38h.txt
echo BITTI >> /root/is/t38h.txt
