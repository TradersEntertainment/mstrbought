#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  ad=$1; shift
  timeout 900 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" > /root/is/b131/$ad.log 2>&1
  out=$(cat /root/is/b131/$ad.log)
  r=$(echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^GUNNER |GUNNER_HIT" | awk '!seen[$0]++' | cut -c1-180 | tr '\n' ' ')
  echo "$ad: $r"
}
( kos j1 --chapter=26 --autotest; kos j2 --chapter=30o --autotest ) > /root/is/b131/o1.txt &
( kos k1 --chapter=20 --autotest; kos k2 --chapter=30 --autotest ) > /root/is/b131/o2.txt &
wait
cat /root/is/b131/o1.txt /root/is/b131/o2.txt > /root/is/b131/ozet4.txt
echo BITTI >> /root/is/b131/ozet4.txt
