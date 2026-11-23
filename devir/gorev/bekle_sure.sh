#!/bin/bash
# Nöbetçi: en çok $1 saniye bekler; wip/ist2-* dallarından biri değişirse erken çıkar ve değişenleri yazar.
SURE="${1:-1500}"
URL=https://github.com/TradersEntertainment/nothistorygame
once=$(git ls-remote "$URL" 'refs/heads/wip/ist2-*' 2>/dev/null | sort)
gecen=0
while [ "$gecen" -lt "$SURE" ]; do
  sleep 60
  gecen=$((gecen + 60))
  simdi=$(git ls-remote "$URL" 'refs/heads/wip/ist2-*' 2>/dev/null | sort)
  if [ -n "$simdi" ] && [ "$simdi" != "$once" ]; then
    echo "SAAT $(date -u +%H:%M) DEGISTI"
    diff <(echo "$once") <(echo "$simdi") | grep '^>' | sed 's/^> //'
    exit 0
  fi
done
echo "SAAT $(date -u +%H:%M) degisiklik yok"
