#!/bin/bash
# Dört yöne bakış kareleri: iki şerit, her bölüm ayrı klasör. Çıktı: /root/is/bakis/<bölüm>/, özet /root/is/bakis/ozet.txt
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
cd /home/user/nothistorygame || exit 1
serit() {
  for g in "$@"; do
    c=${g%%:*}; v=""; [ "$g" != "$c" ] && v="cesit=${g#*:}"
    mkdir -p /root/is/bakis/$c
    timeout 700 xvfb-run -a -s "-screen 0 1280x720x24" $G --path . --rendering-driver opengl3 --resolution 1280x720 \
      res://tests/_ist/bakis_kare.tscn -- bolum=$c shots=/root/is/bakis/$c sure=540 ara=15 en_cok=9 $v > /root/is/bakis/$c.log 2>&1
    n=$(grep -c '^BAKIS bolum' /root/is/bakis/$c.log)
    e=$(grep -c 'SCRIPT ERROR' /root/is/bakis/$c.log)
    b=$(grep -o 'BAKIS_BITTI.*' /root/is/bakis/$c.log | head -1)
    a=$(grep -o 'AUTOTEST [A-Z]*' /root/is/bakis/$c.log | head -1)
    echo "$c nokta=$n hata=$e | $b | $a" >> /root/is/bakis/ozet.txt
  done
}
echo "basla $(date -u +%H:%M)" > /root/is/bakis/ozet.txt
serit 8y 0 4b 6:byz 10h 13 17o 19 20 21 22o 24 26 28o 29o 32o 37o 41o &
serit 26o 4 7:byz 12b 17 18b 19o 20o 22 23 25 29 31o 36b 38o 42b &
wait
echo "BITTI $(date -u +%H:%M)" >> /root/is/bakis/ozet.txt
