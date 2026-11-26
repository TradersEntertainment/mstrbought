#!/bin/bash
# G22 teslimini bekler: durum.md'de "Faz A: TAMAM" (ilk kez görülünce) ya da ilk 3 satırda BİTTİ; en çok $1 sn
# $2 = "fazA_gorulmedi" ise Faz A'yı da haber verir; başka değerse yalnız BİTTİ'yi bekler
cd /home/user/nothistorygame || exit 1
f="docs/_kanit_saray22/durum.md"
t=0
while [ $t -lt "$1" ]; do
  if git fetch -q origin wip/saray22 2>/dev/null; then
    d=$(git show FETCH_HEAD:$f 2>/dev/null)
    echo "$d" | head -3 | grep -qiE "BİTTİ|TESLİM" && { echo "BITTI wip/saray22 $(date -u +%H:%M)"; exit 0; }
    if [ "$2" = "fazA_gorulmedi" ] && echo "$d" | grep -q "Faz A: TAMAM"; then echo "FAZ_A wip/saray22 $(date -u +%H:%M)"; exit 0; fi
  fi
  sleep 300; t=$((t+300))
done
echo "SURE_DOLDU $(date -u +%H:%M)"
