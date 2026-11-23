#!/bin/bash
# Nöbetçi (TAŞIMA 13 / TUR 15): en çok $1 saniye; 5 dakikada bir iki dalın raporuna bakar.
# Bir dalda rapor.md "hâlâ kötü" bölümüyle varsa ve durum.md "BİTTİ/TESLİM/tamamlandı" diyorsa çıkar.
SURE="${1:-7000}"
cd /home/user/nothistorygame || exit 1
gecen=0
while [ "$gecen" -lt "$SURE" ]; do
  sleep 300
  gecen=$((gecen + 300))
  for d in tasima13:_kanit_ist2_tasima13 tur15:_kanit_ist2_tur15; do
    dal="wip/ist2-${d%%:*}"
    kl="docs/${d##*:}"
    git fetch -q origin "$dal" 2>/dev/null || continue
    r=$(git show "FETCH_HEAD:$kl/rapor.md" 2>/dev/null | grep -ci "hâlâ kötü")
    b=$(git show "FETCH_HEAD:$kl/durum.md" 2>/dev/null | grep -ciE "BİTTİ|BITTI|TESLİM|TESLIM|tamamlandı|son kayıt")
    if [ "${r:-0}" -gt 0 ] && [ "${b:-0}" -gt 0 ]; then
      echo "SAAT $(date -u +%H:%M) TESLIM $dal $(git rev-parse --short FETCH_HEAD)"
      exit 0
    fi
  done
done
echo "SAAT $(date -u +%H:%M) teslim yok"
