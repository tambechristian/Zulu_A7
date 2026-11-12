#!/bin/sh
# gate.sh <router plan> <tag>: rip_H + USB hand copper + router plan -> compose -> every gate (one python at a time)
T=/c/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools
H=$T/route/rev2/H
TAG=$2
cd $T
python - "$1" "$TAG" <<'PY'
import json,sys
H='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/H/'
u=json.load(open(H+'usb_fixed.json')); r=json.load(open(sys.argv[1]))
json.dump({'tracks':u['tracks']+r['tracks'],'vias':u['vias']+r['vias'],'remove':r.get('remove',[]),'remove_vias':r.get('remove_vias',[])},open(H+'plus_%s.json'%sys.argv[2],'w'))
PY
python compose_plan.py route/rev2/prep/base_moved.json route/rev2/H/rip_H.json route/rev2/H/plus_$TAG.json route/rev2/H/final_$TAG.json | tail -2
python route_check.py route/rev2/H/final_$TAG.json route/rev2/prep/base_moved.json | tail -12
python C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/widthcheck.py "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" route/rev2/H/final_$TAG.json | tail -3
python $H/via_pad.py route/rev2/prep/base_moved.json route/rev2/H/final_$TAG.json
python $H/usb_metrics.py route/rev2/H/final_$TAG.json
python - $TAG <<'PY'
import json,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as C
H='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'
M=C.apply(json.load(open(H+'prep/base_moved.json')),json.load(open(H+'H/final_%s.json'%sys.argv[1])))
json.dump(M,open(H+'H/board_%s.json'%sys.argv[1],'w'))
PY
python prune_stubs.py route/rev2/H/board_$TAG.json | tail -3
