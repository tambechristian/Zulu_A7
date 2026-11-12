#!/bin/sh
# Strategy G (hard nets first) -- how final_G2.json was built, run from tools/ (one python process at a time except
# where noted). Inputs: prep/base_moved.json, prep/rip.json (regenerated 2026-11-11 with the four Bottom moves).
cd "C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools"
G=route/rev2/G; P=route/rev2/prep
# 1. minimal rip (only copper that clashes with a moved land, all USB copper; moved nets' old copper kept)
python $G/rip_g.py $P/base_moved.json $P/rip.json $G/rip_min.json
# 2. hand copper: VU, TDI, CHAN20, CHAN7, USB5V0, GND ties, CHAN12/CHAN13/CHAN9, FPGA-TCK/LED0_R + USB pair/CHAN10
#    (usb_plan.json is B/usb_hand_plan.json from B/usb_hand.py)
python $G/hand.py $P/base_moved.json $G/usb_plan.json $G/hand.json
# 3. router model = base - rip_min - hand removals + hand copper (unpruned, so kept stubs are join targets)
python -c "
import json,sys; sys.path.insert(0,'.'); import compose_plan as CP
B=json.load(open('$P/base_moved.json')); r=json.load(open('$G/rip_min.json')); h=json.load(open('$G/hand.json'))
json.dump(CP.apply(B,{'remove':r['remove']+h['remove'],'remove_vias':r['remove_vias']+h['remove_vias'],'tracks':h['tracks'],'vias':h['vias']}),open('$G/model_G2.json','w'))"
# 4. remainder (42 open on 25 nets): 41 closed, N\$BTN failed on budget
python $G/router_g.py --model $G/model_G2.json --out $G/r3a.json --order y --soft 1.0 --checkpoint $G/r3a.partial.json
# 5. N$BTN first with CHAN11's router copper lifted, then CHAN11 again
python -c "
import json; P=json.load(open('$G/r3a.json'))
json.dump({'tracks':[t for t in P['tracks'] if t['net']!='CHAN11'],'vias':[v for v in P['vias'] if v['net']!='CHAN11'],'remove':[],'log':[]},open('$G/seed_noC11.json','w'))"
python $G/router_g.py --model $G/model_G2.json --seed $G/seed_noC11.json --nets 'N$BTN' --out $G/n2.json --soft 1.0 --pops 1500000 --rip 3
python $G/router_g.py --model $G/model_G2.json --seed $G/n2.json --nets CHAN11 --out $G/n3.json --soft 1.0 --pops 1500000 --rip 3
# 6. compose (augment connectors + pad-aware prune + compose_plan + removed-and-re-added dedupe), then plan hygiene
python $G/gate.py n3 $G/n3.json
python $G/dedupe.py $G/final_n3.json $G/final_G.json
python $G/vbatt_keep.py $G/final_G.json $G/final_G2.json
# 7. every gate
sh $G/final_gate.sh $G/final_G2.json
