#!/bin/bash
# 0.99.131 aksiyon cilası: atılma + boş el doğrulaması, 20 FPS, 4 kol, günlük /root/is/b131/
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  ad=$1; shift
  timeout 900 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" > /root/is/b131/$ad.log 2>&1
  out=$(cat /root/is/b131/$ad.log)
  r=$(echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^GUNNER |^HELDDEFAULT|GUNNER_HIT" | awk '!seen[$0]++' | cut -c1-200 | tr '\n' ' ')
  echo "$ad: $r"
}
( kos a1 --chapter=30o --autotest; kos a2 --chapter=26o --autotest ) > /root/is/b131/l1.txt &
( kos b1 --chapter=20o --autotest; kos b2 --chapter=20 --autotest ) > /root/is/b131/l2.txt &
( kos c1 --chapter=30 --autotest; kos c2 --chapter=33o --autotest ) > /root/is/b131/l3.txt &
( kos d1 --chapter=26 --autotest; kos d2 --chapter=2 --autotest ) > /root/is/b131/l4.txt &
wait
cat /root/is/b131/l[1-4].txt > /root/is/b131/ozet1.txt
echo BITTI >> /root/is/b131/ozet1.txt
