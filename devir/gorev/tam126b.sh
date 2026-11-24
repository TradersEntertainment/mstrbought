#!/bin/bash
# 0.99.126 tam test (8y düzeltmeleri sonrası): run_tests.sh 4 parça (kuyruk parça 0'da).
S=/tmp/claude-0/-home-user-mstrbought/30127caa-76dd-5459-81fb-4bbd5156d7e0/scratchpad
OZET=$S/tam126b_ozet.txt
cd /home/user/nothistorygame || exit 1
: > "$OZET"
echo "DAL $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD) basla $(date -u +%H:%M)" >> "$OZET"
git checkout -q -- i18n/strings.en.translation i18n/strings.tr.translation 2>/dev/null
timeout 900 "$S/godot/godot" --headless --path . --import > "$S/tam126b_import.log" 2>&1
echo "IMPORT script_error=$(grep -c 'SCRIPT ERROR' "$S/tam126b_import.log")" >> "$OZET"
for k in 0 1 2 3; do
  ( SHARD=$k SHARDS=4 MAXFPS=20 GODOT=$S/godot/godot bash tests/run_tests.sh > "$S/tam126b_$k.txt" 2>&1; echo "PARCA $k CIKIS $?" >> "$S/tam126b_$k.txt" ) &
done
wait
for k in 0 1 2 3; do echo "parca $k: $(grep -c '^AUTOTEST PASS' $S/tam126b_$k.txt) pass | $(tail -1 $S/tam126b_$k.txt)" >> "$OZET"; done
echo "FAIL_TIMEOUT_SCRIPTERR=$(cat $S/tam126b_[0-3].txt | grep -cE 'AUTOTEST FAIL|AUTOTEST TIMEOUT|SCRIPT ERROR')" >> "$OZET"
echo "DENETIM=$(cat $S/tam126b_[0-3].txt | grep -cE '^VISAUDIT|^WALKTHRU|^HELDAUDIT|^ARMAUDIT|WARN_FX_STUCK|^WARN_FLY_ITEM|WARN_VOID_TELEPORT|^ZFIGHT|^JOURNEY_MISS|^JOURNEY_OVERLAP|^ESYAAUDIT (dusme|havada|gomuk|tikama|sinir)|^HAREKETAUDIT|ESYATEST FAIL')" >> "$OZET"
echo "MENURETURN_PASS=$(grep -c 'MENURETURN PASS' $S/tam126b_0.txt)" >> "$OZET"
echo "BITTI $(date -u +%H:%M)" >> "$OZET"
cat "$OZET"
