#!/bin/bash
# birlesik: + tasima10 (kapi/hub) + tasima11 (Haliç/deniz) dogrulamasi
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
OUT=$S/birlesik17.txt
cd /home/user/nothistorygame || exit 1
: > "$OUT"
timeout 900 "$S/godot/godot" --headless --path . --import >/dev/null 2>&1
timeout 300 "$S/godot/godot" --headless --path . res://tests/parse_check.tscn 2>&1 | grep -E "PARSE|SCRIPT ERROR|PASS|FAIL" | tail -2 >> "$OUT"
echo "DAL $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD)" >> "$OUT"
timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/sur_sozlesme.tscn 2>&1 | grep -E '^SURSOZLESME PASS|^SURSOZLESME FAIL|SCRIPT ERROR' | tail -2 >> "$OUT"
timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/sur_oyun_denetim.tscn 2>&1 | grep -E '^SUROYUN nokta|SCRIPT ERROR' | tail -2 >> "$OUT"
timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/esya_fizik.tscn 2>&1 | grep -E "ESYATEST|ESYAAUDIT OZET|SCRIPT ERROR" | tail -2 >> "$OUT"
timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/tasima8d_tekme.tscn -- --chapter=26o 2>&1 | grep -E "PASS|FAIL|SCRIPT ERROR|ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)" | tail -4 >> "$OUT"
timeout 300 "$S/godot/godot" --headless --path . res://tests/_ist/sur_oyun_yuru.tscn 2>&1 | grep -E 'WALKTHRU OZET|SCRIPT ERROR' | tail -2 >> "$OUT"
kos() {
  local et="$1"; shift
  local r
  r=$(timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . -- "$@" 2>&1 \
      | grep -E 'AUTOTEST (PASS|FAIL)|SCRIPT ERROR|VISAUDIT|WALKTHRU|HELDAUDIT|ARMAUDIT|WARN_FX|WARN_FLY|WARN_VOID|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^HAREKETAUDIT' | cut -c1-220 | tr '\n' '|')
  echo "$et $* :: ${r:-CIKTI_YOK}" >> "$OUT"
}
export -f kos
export S OUT
{
  for v in "" =b =c =y =letter =next =byz =byzmistake =byzfail =byzclimb =byzgive; do echo "c6$v --chapter=6 --autotest$v"; done
  for v in "" =byz =byzcell =byzniko =fez =form =lost =next =tea =wall =wallkeep; do echo "c7$v --chapter=7 --autotest$v"; done
  for v in "" =dep =hikmet =honest =next =opened =sinerji =warn; do echo "c8y$v --chapter=8y --autotest$v"; done
  for v in "" =honest =next =open =pass =save =save1 =shame; do echo "c10h$v --chapter=10h --autotest$v"; done
  for v in "" =d2 =d3 =lie =next =year; do echo "c12b$v --chapter=12b --autotest$v"; done
  for v in "" =caught =chain =fall =fez =item =market =next =nofez =wet; do echo "c4$v --chapter=4 --autotest$v"; done
  for v in "" =chain =edirne_none =edirne_policy =fall =lost =nophoto =osm =route =ship_bad =ship_ok =two; do echo "c17$v --chapter=17 --autotest$v"; done
  echo "c17leg --chapter=17 --autotest=edirne_legend --bag=phone,book,selfie,cube"
  for v in "" =miss; do echo "c18b$v --chapter=18b --autotest$v"; done
  for v in "" =captive18 =flee =saved =ship_bad =ship_ok =ship_ok_flee =tezkire; do echo "c19$v --chapter=19 --autotest$v"; done
  for v in "" =hooks_bad =hooks_ok =silent; do echo "c19o$v --chapter=19o --autotest$v"; done
  for v in "" =lose; do echo "c29$v --chapter=29 --autotest$v"; echo "c29o$v --chapter=29o --autotest$v"; done
  for v in "" =hooks_bad =hooks_ok =lose =esik_dur =dis_dur; do echo "c38o$v --chapter=38o --autotest$v"; done
  echo "e8y --chapter=8y --autotest --eskisur=8y"; echo "e12b --chapter=12b --autotest --eskisur=12b"; echo "e38o --chapter=38o --autotest --eskisur=38o"; echo "e17 --chapter=17 --autotest --eskisur=17"; echo "e4 --chapter=4 --autotest=chain --eskisur=4"
  for c in 0 10 11 12 13 18 20 23 24 25 26 26o 27 28o 30 30o 31o 37o 39o 43o 44b 17o 41o 42b 1 2; do echo "d$c --chapter=$c --autotest"; done
} | xargs -P 4 -L 1 bash -c 'kos "$@"' _
echo "MR $(timeout 300 "$S/godot/godot" --headless --max-fps 20 --path . res://tests/menu_return.tscn -- --chapter=26 2>&1 | grep -E "MENURETURN|SCRIPT ERROR" | tail -1)" >> "$OUT"
echo "BITTI kosu=$(grep -c ' :: ' "$OUT") PASS=$(grep -c 'AUTOTEST PASS' "$OUT") DENETIM=$(grep -cE 'VISAUDIT|WALKTHRU|HELDAUDIT|ARMAUDIT|WARN_|ESYAAUDIT|HAREKETAUDIT|SCRIPT ERROR|AUTOTEST FAIL|CIKTI_YOK' "$OUT")" >> "$OUT"
tail -1 "$OUT"
