#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  ad=$1; shift
  timeout 900 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" > /root/is/b131/$ad.log 2>&1
  out=$(cat /root/is/b131/$ad.log)
  r=$(echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^GUNNER |^HELDDEFAULT|GUNNER_HIT|GUNSPOT|TASIMA8 tasima" | awk '!seen[$0]++' | cut -c1-200 | tr '\n' ' ')
  echo "$ad: $r"
}
( kos h1 --chapter=20 --autotest; kos h2 --chapter=26 --autotest=council_ok; kos h3 --chapter=30 --autotest; kos h4 --chapter=0 --autotest ) > /root/is/b131/n1.txt &
( kos i1 --chapter=30o --autotest; kos i2 --chapter=26 --autotest=hold; kos i3 --chapter=20 --autotest=hard; kos i4 --chapter=26o --autotest ) > /root/is/b131/n2.txt &
wait
cat /root/is/b131/n1.txt /root/is/b131/n2.txt > /root/is/b131/ozet3.txt
echo BITTI >> /root/is/b131/ozet3.txt
