"""apply_pair.py <usb_pair.json> <model.json> <seed.json> <out_model.json> <out_seed.json>
Fixes the hand-routed USB pair in the model (legacy USB copper dropped) and strips the USB nets and the seed copper that
touches the pair from the seed, so router.py can re-route those nets around it."""
import json
import sys

pair, model, seed, om, osd = sys.argv[1:6]
U = json.load(open(pair))
M = json.load(open(model))
S = json.load(open(seed))
USB = ('USB_D_P', 'USB_D_N')
nt, nv = len(M['tracks']), len(M['vias'])
M['tracks'] = [t for t in M['tracks'] if t['net'] not in USB] + U['tracks']
M['vias'] = [v for v in M['vias'] if v['net'] not in USB]
print('model: dropped %d legacy USB tracks, %d vias; added %d pair tracks' % (nt - (len(M['tracks']) - len(U['tracks'])),
                                                                           nv - len(M['vias']), len(U['tracks'])))


def key(o):
    return tuple(sorted((k, round(v, 4) if isinstance(v, float) else v) for k, v in o.items()))


ct = {key(t) for t in U['conflict_tracks']}
cv = {key(v) for v in U['conflict_vias']}
t0, v0 = len(S['tracks']), len(S['vias'])
S['tracks'] = [t for t in S['tracks'] if t['net'] not in USB and key(t) not in ct]
S['vias'] = [v for v in S['vias'] if v['net'] not in USB and key(v) not in cv]
print('seed: removed %d tracks, %d vias (USB + conflicts %d/%d)' % (t0 - len(S['tracks']), v0 - len(S['vias']), len(ct), len(cv)))
json.dump(M, open(om, 'w'))
json.dump({'vias': S['vias'], 'tracks': S['tracks'], 'remove': [], 'log': []}, open(osd, 'w'))
print('nets to re-route:', ','.join(U['conflict_nets']))
