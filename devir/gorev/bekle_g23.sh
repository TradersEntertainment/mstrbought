#!/bin/bash
# G23 teslimini bekler: wip/sur23 durum.md İLK satırı "G22b BİTTİ"; en çok $1 sn. Yerel dalı değiştirmez (refs/remotes).
cd /home/user/nothistorygame || exit 1
f="docs/_kanit_sur23/durum.md"
t=0
while [ $t -lt "$1" ]; do
  if git fetch -q origin wip/sur23:refs/remotes/origin/wip/sur23 2>/dev/null; then
    d=$(git show origin/wip/sur23:$f 2>/dev/null | head -1)
    echo "$d" | grep -q "^G23 BİTTİ" && { echo "BITTI $d $(date -u +%H:%M)"; exit 0; }
  fi
  sleep 300; t=$((t+300))
done
echo "SURE_DOLDU $(date -u +%H:%M) son: $d"
