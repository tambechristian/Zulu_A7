"""compose.py <out_plan> <delta1> [delta2 ...]
Compose ../wf_place/plan_wf_place.json (relative to ../wf_place/placed_input_model.json) with deltas made relative
to the frozen result, into ONE plan relative to placed_input_model.json.
A delta 'remove' of a track that was added by an earlier layer is dropped from the tracks list instead; a delta
'remove_vias' entry drops matching earlier-added vias, and is kept as remove_vias only if it matches base vias."""
import json, sys

ST = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
BASE = json.load(open('../wf_place/placed_input_model.json'))
P = json.load(open('../wf_place/plan_wf_place.json'))


def key(t):
    return (t['net'], t['layer'], frozenset({(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))}))


def vmatch(v, r):
    return v['net'] == r['net'] and abs(v['x'] - r['x']) < 2e-3 and abs(v['y'] - r['y']) < 2e-3 and abs(v['hole'] - r['hole']) < 2e-3


tracks, vias = list(P['tracks']), list(P['vias'])
remove, remove_vias = list(P['remove']), list(P.get('remove_vias', []))
for f in sys.argv[2:]:
    D = json.load(open(f))
    for r in D.get('remove', []):
        k = key(r)
        hit = [t for t in tracks if key(t) == k]
        if hit:
            tracks = [t for t in tracks if key(t) != k]
        else:
            remove.append(r)
    for r in D.get('remove_vias', []):
        vias = [v for v in vias if not vmatch(v, r)]
        if any(vmatch(v, r) for v in BASE['vias']) and not any(vmatch(x, r) for x in remove_vias):
            remove_vias.append({k: r[k] for k in ('net', 'x', 'y', 'size', 'hole') if k in r} | ({'span': r['span']} if 'span' in r else {}))
    tracks += D['tracks']
    vias += D['vias']
for v in vias:
    if 'span' not in v and 'from' in v:
        a, b = sorted((ST.index(v['from']), ST.index(v['to'])))
        v['span'] = ST[a:b + 1]
json.dump({'tracks': tracks, 'vias': vias, 'remove': remove, 'remove_vias': remove_vias}, open(sys.argv[1], 'w'), indent=0)
print('plan:', len(tracks), 'tracks', len(vias), 'vias', len(remove), 'remove', len(remove_vias), 'remove_vias')
