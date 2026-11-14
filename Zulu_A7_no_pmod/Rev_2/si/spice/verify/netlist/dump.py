import json, math, sys
M = json.load(open('../../../../tools/route/model.json'))
for net in sys.argv[1:]:
    print('=====', net)
    for t in M['tracks']:
        if t['net'] == net:
            L = math.hypot(t['x2']-t['x1'], t['y2']-t['y1'])
            print('T %-12s w=%.4f (%.3f,%.3f)-(%.3f,%.3f) L=%.3f' % (t['layer'], t['w'], t['x1'], t['y1'], t['x2'], t['y2'], L))
    for v in M['vias']:
        if v['net'] == net:
            print('V (%.3f,%.3f) size=%.3f hole=%.3f span=%s' % (v['x'], v['y'], v['size'], v['hole'], v['span']))
    for p in M['pads']:
        if p['net'] == net:
            print('P', p)
