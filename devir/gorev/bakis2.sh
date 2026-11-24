#!/bin/bash
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
for c in 12b 13 18b; do
  mkdir -p /root/is/bakis2/$c
  timeout 700 xvfb-run -a -s "-screen 0 1280x720x24" $S/godot/godot --path . --rendering-driver opengl3 --resolution 1280x720 res://tests/_ist/bakis_kare.tscn -- bolum=$c shots=/root/is/bakis2/$c sure=540 ara=15 en_cok=9 > /root/is/bakis2/$c.log 2>&1
  echo "$c $(grep -c "^BAKIS bolum" /root/is/bakis2/$c.log) $(grep -c BAKIS_HALKA_ATLA /root/is/bakis2/$c.log)" >> /root/is/bakis2/ozet.txt
done
