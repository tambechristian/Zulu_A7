#!/bin/sh
# final_gate.sh <plan>: every gate on prep/base_moved.json, sequential (one python process at a time)
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools"
G=route/rev2/G; BASE=route/rev2/prep/base_moved.json; F=$1
echo "== route_check"; python route_check.py $F $BASE | tail -3
echo "== exact-removal route_check"; python $G/check_exact.py $BASE $F | grep -v "^plan"
echo "== widthcheck"; python "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools/widthcheck.py" "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb/Zulu_a7_no_pmod.PcbDoc" $F | tail -1
python -c "
import json,sys
sys.path.insert(0,'.')
import compose_plan as CP
json.dump(CP.apply(json.load(open('$BASE')),json.load(open('$F'))),open('$G/board_final.json','w'))"
echo "== prune_stubs (base - remove + plan)"; python prune_stubs.py $G/board_final.json | tail -1
echo "== route_conn"; python route_conn.py $G/board_final.json
echo "== via_pad"; python route/rev2/D/via_pad.py $BASE $F
echo "== emit audit"; python $G/emit_audit.py $BASE $F
echo "== analyze"; python route/rev2/B/analyze.py $BASE $F | grep -v "^    laser"
echo "== usb_metrics (board)"; python route/rev2/D/usb_metrics.py $G/board_final.json
