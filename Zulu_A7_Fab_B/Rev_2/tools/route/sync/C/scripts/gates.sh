#!/bin/sh
# gates.sh <plan.json> <tag>  -- every gate on one strategy-C plan, sequentially (one python process at a time).
# Output in C/out/<tag>/: check.json (judge-style full check), route_check_official.txt (TARGET's CLI),
# route_check_sdram.txt (C/tools copy: SDRAM-D0..15 in the SDRAM set), widthcheck.txt, prune.txt, route_conn.txt,
# planeweb (C/out/planeweb.json, all tags given to planes.py).
set -e
C="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/C"
P="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/sync/prep"
T="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools"
PLAN=$1; TAG=$2; O="$C/out/$TAG"
mkdir -p "$O"
md5sum "$PLAN" > "$O/md5.txt"
python "$C/scripts/check.py" "$PLAN" "$TAG" > "$O/check.txt" 2>&1
(cd "$T" && python route_check.py "$PLAN" "$P/base_new.json" > "$O/route_check_official.txt" 2>&1 || true)
(cd "$C/tools" && python route_check.py "$PLAN" "$P/base_new.json" > "$O/route_check_sdram.txt" 2>&1 || true)
python "$T/widthcheck.py" "$T/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" "$PLAN" "$P/extra_classes.json" > "$O/widthcheck.txt" 2>&1
(cd "$T" && python prune_stubs.py "$O/result.json" > "$O/prune.txt" 2>&1)
(cd "$T" && python route_conn.py "$O/result.json" > "$O/route_conn.txt" 2>&1)
python "$C/scripts/planes.py" "$TAG" > "$O/planeweb.txt" 2>&1
echo done > "$O/DONE"
