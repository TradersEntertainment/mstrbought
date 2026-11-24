#!/bin/bash
# Bütün bölümlerin gerçek hız (PACE) donuk taraması: 3 parça, çıktı /root/is/pace/p<k>.txt, özet /root/is/pace/ozet.txt
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
cd /home/user/nothistorygame || exit 1
echo "basla $(date -u +%H:%M) $(git rev-parse --short HEAD)" > /root/is/pace/ozet.txt
for k in 0 1 2; do
  ( GODOT=$S/godot/godot bash tests/_denetim17/pace_tarama.sh $k 3 > /root/is/pace/p$k.txt 2>&1; echo "PARCA $k BITTI $(date -u +%H:%M)" >> /root/is/pace/ozet.txt ) &
done
wait
echo "TUM_BITTI $(date -u +%H:%M)" >> /root/is/pace/ozet.txt
