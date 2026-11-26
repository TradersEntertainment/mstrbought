#!/bin/bash
# 31o personhidden (D31O_AZ_03) düzeltmesi + clear_line'ı kullanan öteki bölümler: 20 FPS, 4 kol
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  out=$(timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" 2>&1)
  echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^WALKTHRU|^HELDAUDIT|^ARMAUDIT|^GORUNMEZZEMIN |^ALETAUDIT |^DONUKAUDIT |^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^YUKLEMEAUDIT_KESIN " | awk '!seen[$0]++' | cut -c1-220
  [ -z "$(echo "$out" | grep 'AUTOTEST PASS')" ] && echo "YOK_PASS $*"
}
( for i in 1 2; do kos --chapter=31o --autotest=late; kos --chapter=31o --autotest; done ) > /root/is/t31_1.txt &
( for i in 1 2; do kos --chapter=31o --autotest=late; done; kos --chapter=31o --autotest=petrion_bad ) > /root/is/t31_2.txt &
( kos --chapter=20 --autotest; kos --chapter=20 --autotest=lose; kos --chapter=26o --autotest ) > /root/is/t31_3.txt &
( kos --chapter=26 --autotest; kos --chapter=26 --autotest=hold_lose; kos --chapter=31o --autotest=late ) > /root/is/t31_4.txt &
wait
cat /root/is/t31_[1-4].txt > /root/is/t31.txt
echo BITTI >> /root/is/t31.txt
