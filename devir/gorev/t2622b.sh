#!/bin/bash
# 26 sürekli bekçi + 22o şerit ucu doğrulaması: 20 FPS, 4 kol, tam günlük /root/is/b26/
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
kos() {
  ad=$1; shift
  timeout 600 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" > /root/is/b26/$ad.log 2>&1
  out=$(cat /root/is/b26/$ad.log)
  r=$(echo "$out" | grep -E "AUTOTEST (PASS|FAIL)|SCRIPT ERROR|^VISAUDIT |^YUKLEMEAUDIT_KESIN " | awk '!seen[$0]++' | cut -c1-230 | tr '\n' ' ')
  b=$(echo "$out" | grep -c "BEKCI26 katidan\|BEKCI26 ayir surekli")
  echo "$ad: bekci=$b $r"
  [ -z "$(echo "$out" | grep 'AUTOTEST PASS')" ] && echo "YOK_PASS $ad $*"
}
( for i in 1 2 3; do kos c1$i --chapter=26 --autotest=council_ok; done; kos h1 --chapter=26 --autotest=hold ) > /root/is/b26/l1.txt &
( for i in 1 2 3; do kos c2$i --chapter=26 --autotest=council_ok; done; kos h2 --chapter=26 --autotest=hold_box ) > /root/is/b26/l2.txt &
( kos v0 --chapter=26 --autotest; kos v1 --chapter=26 --autotest=isidore; kos v2 --chapter=26 --autotest=nophoto; kos v3 --chapter=26 --autotest=kasim; kos v4 --chapter=26 --autotest=hold_lose ) > /root/is/b26/l3.txt &
( kos o0 --chapter=22o --autotest; kos o1 --chapter=22o --autotest=twins_late; kos o2 --chapter=22o --autotest=late; kos o3 --chapter=22o --autotest=blakh_bad; kos o4 --chapter=22o --autotest=lose; kos o5 --chapter=22o --autotest; kos o6 --chapter=26 --autotest=council_bad; kos o7 --chapter=26o --autotest ) > /root/is/b26/l4.txt &
wait
cat /root/is/b26/l[1-4].txt > /root/is/b26/ozet.txt
echo BITTI >> /root/is/b26/ozet.txt
