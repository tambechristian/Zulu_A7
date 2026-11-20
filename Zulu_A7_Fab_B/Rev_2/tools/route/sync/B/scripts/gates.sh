#!/bin/sh
# gates.sh PLAN TAG ROUTERS  -- every gate on a composed Strategy B plan, one python process at a time; output in B/gates_TAG/
#   TARGET's own CLIs (route_check vs prep/base_new.json, widthcheck with prep/extra_classes.json, prune_stubs and
#   route_conn on the result), the rev2 judge (emit-match, full-board exact DRC vs the unmoved base_cur, via-in-SMD-pad,
#   USB), check_b.py (the same with SDRAM-D0..15 in the SDRAM rules), planeweb, native keys, report_b.py.
set -e
B="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/B"
P0="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/prep"
T="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools"
J="$T/route/rev2/judge"
PLAN=$1; TAG=$2; ROUTERS=$3
O="$B/gates_$TAG"
mkdir -p "$O"
md5sum "$PLAN" > "$O/md5.txt"
(cd "$T" && python route_check.py "$PLAN" "$P0/base_new.json" > "$O/route_check_official.txt" 2>&1 || true)
python "$T/widthcheck.py" "$T/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" "$PLAN" "$P0/extra_classes.json" > "$O/widthcheck.txt" 2>&1 || true
(cd "$T" && python "$J/judge.py" "$P0/base_new.json" "$P0/base_cur.json" "$PLAN" "$O" > "$O/judge.txt" 2>&1 || true)
(cd "$T" && python prune_stubs.py "$O/result.json" > "$O/prune.txt" 2>&1 || true)
(cd "$T" && python route_conn.py "$O/result.json" > "$O/route_conn.txt" 2>&1 || true)
python "$B/scripts/check_b.py" "$PLAN" "$TAG" > "$O/check_b.txt" 2>&1 || true
python "$P0/scripts/native_keys.py" "$PLAN" > "$O/native_keys.txt" 2>&1 || true
python "$B/scripts/planeweb_b.py" "$O/planeweb.json" "base_cur=$P0/base_cur.json" "transplant_clean=$P0/after_transplant.json" "result=$O/result.json" > "$O/planeweb.txt" 2>&1 || true
python "$B/scripts/report_b.py" "$PLAN" "$ROUTERS" "$O/report.json" > "$O/report.txt" 2>&1 || true
echo done > "$O/DONE"
