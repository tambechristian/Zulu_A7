# -*- coding: utf-8 -*-
"""Stage 13 judge -- make a route_inputs.json read back from the PLACED PcbDoc usable by the gates (read-only on input).
Altium stores a laser stack as separate via objects at one XY (Top-L2 + L2-L3, L4-L5 + L5-Bottom; route_emit emits them
so), and tools/block_place.islands joins a via only on the SIGNAL layers of its span -- so a Top-L2 object and an L2-L3
object never meet there and every stacked net reads as split.  This merges, per net and XY, via objects whose spans
chain through a shared layer into the one record the plan used (Top/L2/L3, L4/L5/Bottom), and adds the gate inputs'
'hdi' model.  A buried L3-L4 object stays its own record (it shares a signal layer with the stacks, so islands joins it).
    python merge_stacks.py <route_inputs.json> <judge/inputs_gate.json> <out.json>"""
import collections, io, json, sys
a = json.load(io.open(sys.argv[1], encoding='utf-8'))
g = json.load(io.open(sys.argv[2], encoding='utf-8'))
ST = g['hdi']['stack']
CHAIN = {('Top', 'L2-GND'): 'T', ('L2-GND', 'L3-SIG'): 'T', ('L4-SIG', 'L5-VCC3V3'): 'B', ('L5-VCC3V3', 'Bottom'): 'B'}
land = {tuple(s['span']): (s['land'], s['hole']) for s in g['hdi']['spans']}
groups = collections.defaultdict(list); keep = []
for v in a['vias']:
    sp = tuple(v.get('span') or ST)
    k = CHAIN.get(sp)
    if k is None:
        keep.append(v)
    else:
        groups[(v['net'], round(v['x'], 4), round(v['y'], 4), k)].append(v)
n_m = 0
for (net, x, y, k), lst in groups.items():
    sps = {tuple(v['span']) for v in lst}
    full = (('Top', 'L2-GND'), ('L2-GND', 'L3-SIG')) if k == 'T' else (('L4-SIG', 'L5-VCC3V3'), ('L5-VCC3V3', 'Bottom'))
    if set(full) <= sps and len(lst) == 2:
        sp = ['Top', 'L2-GND', 'L3-SIG'] if k == 'T' else ['L4-SIG', 'L5-VCC3V3', 'Bottom']
        L, H = land[tuple(sp)]
        keep.append(dict(span=sp, x=lst[0]['x'], y=lst[0]['y'], size=L, hole=H, net=net)); n_m += 1
    else:
        keep.extend(lst)                      # a lone Top-L2 (lever 1) or anything unpaired stays as it is
out = dict(a); out['vias'] = keep; out['hdi'] = g['hdi']
json.dump(out, io.open(sys.argv[3], 'w', encoding='utf-8'))
print('via objects %d -> records %d (%d stacks merged)' % (len(a['vias']), len(keep), n_m))
