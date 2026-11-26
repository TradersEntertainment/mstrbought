#!/bin/bash
# G22b teslimini bekler: wip/saray22 durum.md İLK satırı "G22b BİTTİ"; en çok $1 sn. Yerel dalı değiştirmez (refs/remotes).
cd /home/user/nothistorygame || exit 1
f="docs/_kanit_saray22/durum.md"
t=0
while [ $t -lt "$1" ]; do
  if git fetch -q origin wip/saray22:refs/remotes/origin/wip/saray22 2>/dev/null; then
    d=$(git show origin/wip/saray22:$f 2>/dev/null | head -1)
    echo "$d" | grep -q "^G22b BİTTİ" && { echo "BITTI $d $(date -u +%H:%M)"; exit 0; }
  fi
  sleep 300; t=$((t+300))
done
echo "SURE_DOLDU $(date -u +%H:%M) son: $d"
