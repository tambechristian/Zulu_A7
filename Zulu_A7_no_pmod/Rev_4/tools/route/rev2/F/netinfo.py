"""netinfo.py <model.json> NET[,NET...] -- islands of a net: pads, tracks, vias per island (debug aid)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..')))
import route_conn as C  # noqa: E402

M = json.load(open(sys.argv[1]))
isl = C.islands(M)
for net in sys.argv[2].split(','):
    gs = isl.get(net, [])
    print('=== %s: %d islands' % (net, len(gs)))
    for k, g in enumerate(gs):
        print(' island %d plane=%s pads: %s' % (k, g['plane'], ' '.join('%s.%s(%.2f,%.2f)' % (
            M['pads'][i]['ref'], M['pads'][i]['pad'], M['pads'][i]['x'], M['pads'][i]['y']) for i in g['pads'])))
        for i in g['tracks']:
            t = M['tracks'][i]
            print('   T %-12s (%.3f,%.3f)-(%.3f,%.3f) w%.3f' % (t['layer'], t['x1'], t['y1'], t['x2'], t['y2'], t['w']))
        for i in g['vias']:
            v = M['vias'][i]
            print('   V (%.3f,%.3f) %s>%s %.2f/%.2f' % (v['x'], v['y'], v['span'][0], v['span'][-1], v['size'], v['hole']))
