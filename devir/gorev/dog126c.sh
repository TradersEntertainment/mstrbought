#!/bin/bash
# 0.99.126 doğrulama C (8y oyuncu bildirimi: görünmez rampa, havada keçi, Hasan beklemesi): kareler, sözleşme altılısı,
# 8y/26/26o/31o/9 çeşitleri (20 FPS, tam süzgeç), 8y =yuru, ZFIGHT 8y/26/31o
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
G=$S/godot/godot
O=$S/dog126c.txt
F='AUTOTEST (PASS|FAIL|TIMEOUT)|SCRIPT ERROR|^VISAUDIT|^WALKTHRU|^HELDAUDIT|^ARMAUDIT|WARN_FX_STUCK|^WARN_FLY_ITEM|WARN_VOID_TELEPORT|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^HAREKETAUDIT'
cd /home/user/nothistorygame || exit 1
: > "$O"
echo "DAL $(git rev-parse --short HEAD)+degisiklik basla $(date -u +%H:%M)" >> "$O"
mkdir -p /root/is/havada8y_sonra; : > /root/is/c2.txt; : > /root/is/c3.txt
( timeout 900 xvfb-run -a -s "-screen 0 1280x720x24" "$G" --path . --rendering-driver opengl3 --resolution 1280x720 res://tests/_ist/havada8y_kare.tscn -- bolum=8y shots=/root/is/havada8y_sonra 2>&1 | grep -E 'KECI|RAMPA.*Toprak|KOPRU_COCUK|SCRIPT ERROR' > /root/is/c0.txt ) &
( timeout 300 "$G" --headless --path . res://tests/_ist/sur_sozlesme.tscn 2>&1 | grep -E '^SURSOZLESME (PASS|FAIL)|SCRIPT ERROR' | tail -2 > /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_denetim.tscn 2>&1 | grep -E '^SUROYUN nokta|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E 'ESYATEST (PASS|FAIL)|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/sur_oyun_yuru.tscn 2>&1 | grep -E 'WALKTHRU OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tasima11_halic_sonda.tscn 2>&1 | grep -E 'HALICSONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  timeout 300 "$G" --headless --path . res://tests/_ist/tur14_marmara_sonda.tscn 2>&1 | grep -E 'MARMARASONDA OZET|SCRIPT ERROR' | tail -2 >> /root/is/c1.txt
  for f in chapter8y chapter26 chapter31o chapter26o; do echo "ZFIGHT $f: $(timeout 150 "$G" --headless --path . -s tests/zfight_check.gd -- res://scenes/$f.tscn 2>&1 | grep -c '^ZFIGHT')" >> /root/is/c1.txt; done ) &
( for v in "" "=warn" "=dep" "=opened" "=honest" "=hikmet" "=sinerji" "=yuru" "=next"; do
    echo "[8y$v] $(timeout 300 "$G" --headless --max-fps 20 --path . -- --chapter=8y --autotest$v 2>&1 | grep -E "$F|T10_8Y yuru|YURU" | awk '!seen[$0]++' | tr '\n' ' ' | cut -c1-400)" >> /root/is/c2.txt
  done ) &
( for a in "--chapter=26 --autotest" "--chapter=26 --autotest=nophoto" "--chapter=26o --autotest" "--chapter=31o --autotest" "--chapter=31o --autotest=late" "--chapter=9 --autotest" "--chapter=9 --autotest=hikmet" "--chapter=13 --autotest"; do
    echo "[$a] $(timeout 300 "$G" --headless --max-fps 20 --path . -- $a 2>&1 | grep -E "$F" | awk '!seen[$0]++' | tr '\n' ' ' | cut -c1-400)" >> /root/is/c3.txt
  done ) &
wait
cat /root/is/c0.txt /root/is/c1.txt /root/is/c2.txt /root/is/c3.txt >> "$O"
echo "BITTI $(date -u +%H:%M)" >> "$O"
