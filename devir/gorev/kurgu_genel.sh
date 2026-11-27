#!/bin/bash
# Genel fragman kurgusu: aksiyon_1080 + tg_1080 (tüfekçi yeniden çekimi). Kullanım: kurgu_genel.sh ÇIKTI.mp4 [--dry]
K=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad/fragman2/kayit
R=$K/aksiyon_1080.avi:$K/aksiyon_1080.log
T=$K/tg_1080.avi:$K/tg_1080.log
cd /home/user/nothistorygame
python3 tools/trailer/story_cut.py "$1" \
  $R:ok_yagmuru::0.45 \
  "$R:cannon:7.0:5.0::TOPU KENDİN DOLDUR, KENDİN NİŞANLA" \
  $R:kizak_kayis::0.7 \
  $R:sahi_hey::0.7 \
  $R:fren_ipi::4.0 \
  $R:havlu_ok2::3.4 \
  $R:fici::1.87 \
  $R:flight:::sessiz \
  $R:wall_duel \
  $T:tower_gunner:${TG0:-0}:${TG1:-0} \
  $R:duel30 \
  $R:arena::1.5 \
  $R:card \
  --music assets/audio/music/battle_ottoman.mp3 $2
