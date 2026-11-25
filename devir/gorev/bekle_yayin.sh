#!/bin/bash
# Açık depodaki guncelleme.json'da $1 sürümü çıkana dek bekler (en çok $2 sn); sonucu /root/is/yayin128.txt
U=https://github.com/TradersEntertainment/nothistorygamedemo/releases/latest/download/guncelleme.json
t=0
while [ $t -lt "$2" ]; do
  j=$(curl -sL --max-time 30 "$U")
  if echo "$j" | grep -q "\"$1\""; then echo "TAMAM t=$t"; echo "$j" | head -c 1500; exit 0; fi
  sleep 120; t=$((t+120))
done
echo "SURE DOLDU t=$t"; echo "$j" | head -c 600
