#!/bin/sh
# gate.sh KEY PLAN  -- official gates + judge, all output in $S/KEY/
S="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/judge"
T="C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools"
K=$1; P=$2
mkdir -p "$S/$K"
cd "$T"
md5sum "$P" > "$S/$K/md5.txt"
python route_check.py "$P" route/rev2/prep/base_moved.json > "$S/$K/route_check.txt" 2>&1
python "$T/widthcheck.py" "$T/../Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" "$P" > "$S/$K/widthcheck.txt" 2>&1
python "$S/judge.py" route/rev2/prep/base_moved.json route/rev2/model_base.json "$P" "$S/$K" > "$S/$K/judge.txt" 2>&1
python prune_stubs.py "$S/$K/result.json" > "$S/$K/prune.txt" 2>&1
python route_conn.py "$S/$K/result.json" > "$S/$K/route_conn.txt" 2>&1
echo done > "$S/$K/DONE"
