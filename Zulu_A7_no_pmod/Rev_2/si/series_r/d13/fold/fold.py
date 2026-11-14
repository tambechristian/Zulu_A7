"""Fold the adversarial DFM fixes into d13/final_plan.json -> d13/fold/plan_fixed.json.

F1 (required): U1's visible designator moves from (39.2168, 16.6251) to (39.70, 16.55), rot 0 (d13/verify/u1_silk.py:
   the most robust legal anchor within 2.5 mm; >= 0.374 mm to every Top mask opening, >= 3.7 mm to other silk).
F2 (carry-overs): microvia typing and the net-class add are already in the plan; the VIPPO list is made explicit in a
   new 'vippo' key (every new via whose hole lies inside a new R pad); the re-pour is an implementation step.
Copper lists are copied unchanged.  New keys: 'designator_moves', 'vippo'.  emit_copper ignores both.
"""
import hashlib, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'final_plan.json')
assert hashlib.md5(open(SRC, 'rb').read()).hexdigest().startswith('6bd34bd7')
P = json.load(open(SRC))
B = json.load(open(os.path.join(HERE, '..', '..', 'board_extract.json')))
u1 = [t for t in B['texts'] if t['comp'] == 'U1' and t['designator'] and t['layer'] == 'TopOverlay']
assert len(u1) == 1 and abs(u1[0]['x'] - 39.2168) < 1e-4 and abs(u1[0]['y'] - 16.6251) < 1e-4 and not u1[0]['hidden']
P['source'] = dict(P['source'],
                   plan='16-resistor plan: 13-resistor plan (dq_series_r_plan_13.json md5 f2949630) + gnd47 unlock + R132 D13 '
                        '(Top, u3_end, nudged dy=+0.0035) + R133 D14 + R134 D15 (Bottom, u1_end F4) + DFM fix F1 '
                        '(U1 designator moved); d13 pass, combined plan d13/final_plan.json md5 6bd34bd7',
                   generated_by='si/series_r/d13/fold/fold.py')
P['designator_moves'] = [dict(ref='U1', layer='TopOverlay', text='U1', height=0.8001, stroke=0.1524, rot=0,
                              x_from=39.2168, y_from=16.6251, x=39.70, y=16.55,
                              why='DFM fix F1: at (39.2168,16.6251) it is 0.045 mm from R132-1 mask opening '
                                  '(SilkToSolderMaskClearance 0.254, in the batch DRC); hiding it is the alternative')]
vippo = []
for pr in P['parts']:
    for k, pn in (('pad1', '1'), ('pad2', '2')):
        pd = pr[k]
        hits = [v for v in P['vias'] if v.get('why') != 'rename' and abs(v['x'] - pd['x']) < 0.15 and abs(v['y'] - pd['y']) < 0.15]
        if hits:
            vippo.append(dict(pad='%s-%s' % (pr['ref'], pn), net=pd['net'], x=hits[0]['x'], y=hits[0]['y'],
                              vias=['%s>%s %.2f/%.2f' % (v['from'].replace(' Layer', ''), v['to'].replace(' Layer', ''), v['size'], v['hole']) for v in hits],
                              fill='filled and capped (VIPPO)'))
P['vippo'] = vippo
out = os.path.join(HERE, 'plan_fixed.json')
json.dump(P, open(out, 'w', newline='\n'), indent=1)
# copper lists identical to the combined plan
Q = json.load(open(SRC))
for k in Q:
    if k != 'source':
        assert Q[k] == P[k], k
print('wrote', out, hashlib.md5(open(out, 'rb').read()).hexdigest(), 'vippo', [v['pad'] for v in vippo])
