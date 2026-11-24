#!/bin/bash
# G17/G18 teslimini bekler (durum.md ilk 3 satırında BİTTİ|TESLİM) ya da $1 sn
cd /home/user/nothistorygame || exit 1
t=0
while [ $t -lt "$1" ]; do
  for p in "wip/denetim17:docs/_kanit_denetim17/durum.md" "wip/goz18:docs/_kanit_goz18/durum.md"; do
    b=${p%%:*}; f=${p#*:}
    git fetch -q origin $b 2>/dev/null && git show FETCH_HEAD:$f 2>/dev/null | head -3 | grep -qE "BİTTİ|TESLİM" && { echo "TESLIM $b $(date -u +%H:%M)"; exit 0; }
  done
  sleep 300; t=$((t+300))
done
echo "SURE_DOLDU $(date -u +%H:%M)"
