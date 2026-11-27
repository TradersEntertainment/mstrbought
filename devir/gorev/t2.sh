#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  ad=$1; shift
  timeout 900 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" > /root/is/b131/$ad.log 2>&1
  out=$(cat /root/is/b131/$ad.log)
  r=$(echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^GUNNER |^HELDDEFAULT|GUNNER_HIT|TASIMA8" | awk '!seen[$0]++' | cut -c1-200 | tr '\n' ' ')
  echo "$ad: $r"
}
( kos e1 --chapter=26 --autotest=council_ok; kos e2 --chapter=26 --autotest; kos e3 --chapter=30o --autotest; kos e4 --chapter=20 --autotest; kos e5 --chapter=0 --autotest ) > /root/is/b131/m1.txt &
( kos f1 --chapter=26 --autotest=hold; kos f2 --chapter=30 --autotest; kos f3 --chapter=20o --autotest; kos f4 --chapter=26o --autotest; kos f5 --chapter=arena --autotest=osm ) > /root/is/b131/m2.txt &
wait
cat /root/is/b131/m1.txt /root/is/b131/m2.txt > /root/is/b131/ozet2.txt
echo BITTI >> /root/is/b131/ozet2.txt
