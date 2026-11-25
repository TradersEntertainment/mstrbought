#!/bin/bash
# Devriye eri yamaç sondası: eski city_life (HEAD) ×2, yeni ×2 (38o)
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
cp scripts/world/city_life.gd /root/is/city_life_yeni.gd
git show HEAD:scripts/world/city_life.gd > scripts/world/city_life.gd
: > /root/is/t38s.txt
for i in 1 2; do
  ( timeout 200 "$S/godot/godot" --headless --max-fps 20 --path . -s tests/_ci344/devriye_yamac.gd -- res://scenes/chapter38o.tscn 2>&1 | grep -E 'DEVRIYEYAMAC|SCRIPT ERROR' | sed 's/^/ESKI /' >> /root/is/t38s.txt ) &
done
wait
cp /root/is/city_life_yeni.gd scripts/world/city_life.gd
for i in 1 2; do
  ( timeout 200 "$S/godot/godot" --headless --max-fps 20 --path . -s tests/_ci344/devriye_yamac.gd -- res://scenes/chapter38o.tscn 2>&1 | grep -E 'DEVRIYEYAMAC|SCRIPT ERROR' | sed 's/^/YENI /' >> /root/is/t38s.txt ) &
done
wait
echo BITTI >> /root/is/t38s.txt
