#!/bin/bash
# 0.99.126 doğrulama B: sözleşme altılısı, CITYCHECK 31o/24, menüye dönüş 31o (MR_AFTER=60) ve 26, ZFIGHT 31o/17o
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
O=$S/dog126b.txt
cd /home/user/nothistorygame || exit 1
: > "$O"
echo "DAL $(git rev-parse --short HEAD) basla $(date -u +%H:%M)" >> "$O"
( timeout 300 "$G" --headless --path . res://tests/_ist/sur_sozlesme.tscn 2>&1 | grep -E '^SURSOZLESME (PASS|FAIL)|SCRIPT ERROR' | tail -2 > /root/is/b1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_denetim.tscn 2>&1 | grep -E '^SUROYUN nokta|SCRIPT ERROR' | tail -2 >> /root/is/b1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E 'ESYATEST|SCRIPT ERROR' | tail -2 >> /root/is/b1.txt ) &
( timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_yuru.tscn 2>&1 | grep -E 'WALKTHRU OZET|SCRIPT ERROR' | tail -2 > /root/is/b2.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tasima11_halic_sonda.tscn 2>&1 | grep -E 'HALICSONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/b2.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tur14_marmara_sonda.tscn 2>&1 | grep -E 'MARMARASONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/b2.txt ) &
wait
cat /root/is/b1.txt /root/is/b2.txt >> "$O"
echo "ZFIGHT31O: $(timeout 150 "$G" --headless --path . -s tests/zfight_check.gd -- res://scenes/chapter31o.tscn 2>&1 | grep -c '^ZFIGHT')" >> "$O"
echo "ZFIGHT17O: $(timeout 150 "$G" --headless --path . -s tests/zfight_check.gd -- res://scenes/chapter17o.tscn 2>&1 | grep -c '^ZFIGHT')" >> "$O"
CITYCHECK_CH=31o timeout 900 "$G" --headless --path . res://tests/city_check.tscn 2>&1 | grep -E "CITYCHECK (PASS|FAIL)|SCRIPT ERROR" | sed 's/^/[31o] /' >> "$O"
CITYCHECK_CH=24 timeout 900 "$G" --headless --path . res://tests/city_check.tscn 2>&1 | grep -E "CITYCHECK (PASS|FAIL)|SCRIPT ERROR" | sed 's/^/[24] /' >> "$O"
MR_AFTER=60 timeout 600 "$G" --headless --path . res://tests/menu_return.tscn -- --chapter=31o 2>&1 | grep -E "^MENURETURN|SCRIPT ERROR" | awk '!seen[$0]++' | sed 's/^/[31o MR60] /' >> "$O"
timeout 300 "$G" --headless --path . res://tests/menu_return.tscn -- --chapter=26 2>&1 | grep -E "^MENURETURN|SCRIPT ERROR" | awk '!seen[$0]++' | sed 's/^/[26] /' >> "$O"
echo "BITTI $(date -u +%H:%M)" >> "$O"
cat "$O"
