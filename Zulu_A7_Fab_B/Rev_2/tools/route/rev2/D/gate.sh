#!/bin/sh
# gate.sh <router plan>: merge rip + USB + ties + router plan, compose, and run every gate
set -e
T=/c/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools
D=$T/route/rev2/D
python - "$@" <<'PY'
import json,sys
D='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'
r=json.load(open(D+'prep/rip.json')); x=json.load(open(D+'D/extra_rip.json'))
json.dump({'remove':r['remove']+x['remove'],'remove_vias':r['remove_vias']+x['remove_vias']},open(D+'D/rip_D.json','w'))
ps=[json.load(open(D+'D/usb_tracks.json')),json.load(open(D+'D/ties.json'))]+[json.load(open(a)) for a in sys.argv[1:]]
out={k:sum((p.get(k,[]) for p in ps),[]) for k in ('tracks','vias','remove','remove_vias')}
json.dump(out,open(D+'D/route_plus.json','w'))
PY
cd $T
python compose_plan.py route/rev2/prep/base_moved.json route/rev2/D/rip_D.json route/rev2/D/route_plus.json route/rev2/D/final_plan.json | tail -5
python route_check.py route/rev2/D/final_plan.json route/rev2/prep/base_moved.json | tail -4
python C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/widthcheck.py "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc" route/rev2/D/final_plan.json | tail -3
python $D/via_pad.py route/rev2/prep/base_moved.json route/rev2/D/final_plan.json
python $D/usb_metrics.py route/rev2/D/final_plan.json
python - <<'PY'
import json,sys
sys.path.insert(0,'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as C
D='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'
M=C.apply(json.load(open(D+'prep/base_moved.json')),json.load(open(D+'D/final_plan.json')))
json.dump(M,open(D+'D/final_board.json','w'))
PY
python prune_stubs.py route/rev2/D/final_board.json | tail -3
