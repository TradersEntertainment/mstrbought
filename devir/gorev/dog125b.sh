#!/bin/bash
# 0.99.125: 24 v2 kalabalık — CITYCHECK (yalnız 24, iki kez) ve STREETCHECK
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
O=$S/dog125b.txt
cd /home/user/nothistorygame || exit 1
: > "$O"
for k in 1 2; do
  CITYCHECK_CH=24 timeout 900 "$G" --headless --path . res://tests/city_check.tscn 2>&1 | grep -E "CITYCHECK|SCRIPT ERROR|Parse Error" >> "$O"
done
timeout 900 "$G" --headless --path . res://tests/street_check.tscn 2>&1 | grep -E "STREETCHECK|SCRIPT ERROR|Parse Error" >> "$O"
echo "BITTI $(date -u +%H:%M)" >> "$O"
