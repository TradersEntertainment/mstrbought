#!/bin/bash
# 0.99.125 düzeltme doğrulaması: Bölüm 10 çeşitleri, 31o (varsayılan eski set) çeşitleri, 31o zfight, CITYCHECK
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
O=$S/dog125.txt
F='AUTOTEST (PASS|FAIL)|SCRIPT ERROR|VISAUDIT|WALKTHRU [^O]|HELDAUDIT|ARMAUDIT|WARN_FX|WARN_FLY|WARN_VOID|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^HAREKETAUDIT|T12_31O sur'
cd /home/user/nothistorygame || exit 1
: > "$O"
calis() {
  timeout 300 "$G" --headless --max-fps 20 --path . -- "$@" 2>&1 | grep -E "$F" | awk '!seen[$0]++' | sed "s/^/[$*] /" >> "$O"
}
for v in "" "=fail" "=honest" "=selfie" "=byz" "=retry" "=fez" "=retry" "=retry"; do calis --chapter=10 --autotest$v & done
wait
calis --chapter=10 --autotest=next
for v in "" "=late" "=petrion_ok" "=petrion_bad"; do calis --chapter=31o --autotest$v & done
calis --chapter=31o --autotest --yenisur=31o &
wait
echo "ZFIGHT31O: $(timeout 150 "$G" --headless --path . -s tests/zfight_check.gd -- res://scenes/chapter31o.tscn 2>&1 | grep -c '^ZFIGHT')" >> "$O"
timeout 900 "$G" --headless --path . res://tests/city_check.tscn 2>&1 | grep -E "CITYCHECK|SCRIPT ERROR" >> "$O"
echo "BITTI $(date -u +%H:%M)" >> "$O"
