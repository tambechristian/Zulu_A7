#!/bin/sh
# Rebuild the whole Fab B Rev 2 transplant prep from the PcbDocs (KiCad 10 python for the models, plain python after).
#   sh scripts/run_all.sh            (models are reused when present; delete models/ to re-import the PcbDocs)
# Never more than 2 python processes at once (~2 GB each).
set -e
P="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/prep"
TT="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools"
ST="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools"
SB="C:/Users/tambe/AppData/Local/Temp/claude/4f46ee6af972add9/cb02897e-21a5-48d4-9f87-57145adc4da2/scratchpad/sync/board/pcb"
KP="C:/Program Files/KiCad/10.0/bin/python.exe"
cd "$P"
mkdir -p models
if [ ! -f models/tgt_33023787.json ]; then
  (cd "$TT" && FABB_PCB="$TT/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" FABB_MODEL="$P/models/tgt_33023787.json" \
     timeout 1200 "$KP" route_model.py > "$P/models/tgt.log" 2>&1)
fi
for c in 22ee1dc 51ffba0 06d9f27 04819de 3b1817d 3e4ee8c 427960e; do
  if [ ! -f models/src_$c.json ]; then
    (cd "$ST" && FABB_PCB="$SB/src_$c.PcbDoc" FABB_MODEL="$P/models/src_$c.json" timeout 1200 "$KP" route_model.py \
       > "$P/models/src_$c.log" 2>&1)
  fi
done
python scripts/build_base.py
python -c "import json; json.dump({'SDRAM_DATA': ['SDRAM-D%d' % i for i in range(16)]}, open('extra_classes.json', 'w'), indent=1)"
python scripts/delta.py
(python scripts/build_transplant.py --mode clean > log_clean.txt 2>&1 && python scripts/apply_check.py "$P/transplant.json" "" > /dev/null) &
(python scripts/build_transplant.py --mode stubs > log_stubs.txt 2>&1 && python scripts/apply_check.py "$P/transplant_stubs.json" _stubs > /dev/null) &
wait
(python scripts/build_transplant.py --mode clean --rip-ja > log_clean_ripja.txt 2>&1 && python scripts/apply_check.py "$P/transplant_ripja.json" _ripja > /dev/null) &
(python scripts/build_transplant.py --mode stubs --rip-ja > log_stubs_ripja.txt 2>&1 && python scripts/apply_check.py "$P/transplant_stubs_ripja.json" _stubs_ripja > /dev/null) &
wait
for v in "" _stubs _ripja _stubs_ripja; do
  (cd "$TT" && python route_check.py "$P/transplant$v.json" "$P/base_new.json" > "$P/route_check_official$v.txt" 2>&1 || true)
  (cd "$TT" && python prune_stubs.py "$P/after_transplant$v.json" > "$P/prune_after$v.txt" 2>&1)
  (cd "$TT" && python route_conn.py "$P/after_transplant$v.json" > "$P/route_conn_after$v.txt" 2>&1)
  python "$TT/widthcheck.py" "$TT/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" "transplant$v.json" extra_classes.json > "widthcheck$v.txt" 2>&1
  python scripts/native_keys.py "transplant$v.json" > "native_keys$v.txt" 2>&1
done
python scripts/native_keys.py rip_ja.json > native_keys_rip_ja.txt 2>&1
python scripts/summarize.py
