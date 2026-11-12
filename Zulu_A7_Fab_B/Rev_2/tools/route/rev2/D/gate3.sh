#!/bin/sh
# gate3.sh <router plan> <tag>: hand_plan (rip + extra rip + USB + U10 ties + USB5V0 + VU) + router plan -> compose -> every gate
set -e
T=/c/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools
D=$T/route/rev2/D
TAG=$2
python - "$1" "$TAG" <<'PY'
import json,sys
D='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/D/'
h=json.load(open(D+'hand_plan.json')); r=json.load(open(sys.argv[1])); t=sys.argv[2]
json.dump({'remove':h['remove'],'remove_vias':h['remove_vias']},open(D+'rip3.json','w'))
json.dump({'tracks':h['tracks']+r['tracks'],'vias':h['vias']+r['vias'],'remove':r.get('remove',[]),'remove_vias':r.get('remove_vias',[])},open(D+'plus_%s.json'%t,'w'))
PY
cd $T
python compose_plan.py route/rev2/prep/base_moved.json route/rev2/D/rip3.json route/rev2/D/plus_$TAG.json route/rev2/D/final_$TAG.json | tail -4
python route_check.py route/rev2/D/final_$TAG.json route/rev2/prep/base_moved.json | tail -4
python C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/widthcheck.py "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" route/rev2/D/final_$TAG.json | tail -3
python $D/via_pad.py route/rev2/prep/base_moved.json route/rev2/D/final_$TAG.json
python $D/usb_metrics.py route/rev2/D/final_$TAG.json
python - $TAG <<'PY'
import json,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as C
D='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'
M=C.apply(json.load(open(D+'prep/base_moved.json')),json.load(open(D+'D/final_%s.json'%sys.argv[1])))
json.dump(M,open(D+'D/board_%s.json'%sys.argv[1],'w'))
PY
python prune_stubs.py route/rev2/D/board_$TAG.json | tail -3
