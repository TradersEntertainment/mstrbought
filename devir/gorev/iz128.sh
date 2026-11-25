#!/bin/bash
# 0.99.128: bölüm ortası kurulumların boşluk izi (YUKLEME_IZ=700), 20 FPS
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
cd /home/user/nothistorygame || exit 1
F="AUTOTEST (PASS|FAIL|TIMEOUT)|SCRIPT ERROR|^YUKLEMEAUDIT |^YUKLEMEIZ"
( YUKLEME_IZ=700 timeout 600 $G --headless --max-fps 20 --path . -- --chapter=26 --autotest 2>&1 | grep -E "$F" | cut -c1-220 > /root/is/iz128_26.txt ) &
( YUKLEME_IZ=700 timeout 600 $G --headless --max-fps 20 --path . -- --chapter=31o --autotest 2>&1 | grep -E "$F" | cut -c1-220 > /root/is/iz128_31o.txt ) &
wait
( YUKLEME_IZ=700 timeout 600 $G --headless --max-fps 20 --path . -- --chapter=24 --autotest 2>&1 | grep -E "$F" | cut -c1-220 > /root/is/iz128_24.txt ) &
( YUKLEME_IZ=700 timeout 600 $G --headless --max-fps 20 --path . -- --chapter=13 --autotest=city 2>&1 | grep -E "$F" | cut -c1-220 > /root/is/iz128_13.txt ) &
wait
echo BITTI
