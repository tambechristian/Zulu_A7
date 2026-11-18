"""mkE.py: modelE = frozenD minus PGOODALL R107->U8-15 copper; rip.json lists the removed copper."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(H, '..', 'model_frozenD.json')))
RT = set(range(4825, 4837))
RV = set(range(1558, 1564))
for i in RT: assert M['tracks'][i]['net'] == 'PWR_PGOODALL'
for i in RV: assert M['vias'][i]['net'] == 'PWR_PGOODALL'
rip = {'tracks': [M['tracks'][i] for i in sorted(RT)], 'vias': [M['vias'][i] for i in sorted(RV)]}
M['tracks'] = [t for i, t in enumerate(M['tracks']) if i not in RT]
M['vias'] = [v for i, v in enumerate(M['vias']) if i not in RV]
json.dump(M, open(os.path.join(H, 'modelE.json'), 'w'))
json.dump(rip, open(os.path.join(H, 'ripE.json'), 'w'), indent=0)
print(len(rip['tracks']), len(rip['vias']))
