import json, math
import rank as R
from lib import C
A = [c for c in json.load(open('ranked_D14.json')) if c['body_ok']]
Bc = [c for c in json.load(open('ranked_D15.json')) if c['body_ok']]
def ext(c):
    xs, ys = [], []
    for (L, nn, x1, y1, x2, y2, w, why) in c['add']:
        if why in ('connector', 'piece'):
            xs += [x1, x2]; ys += [y1, y2]
    xs += [c['rbox'][0], c['rbox'][2]]; ys += [c['rbox'][1], c['rbox'][3]]
    return [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15]
for c in A + Bc:
    c['ext'] = ext(c)
# pieces are long (they are sub-segments of the run); use only the R box + connectors for the quick test
def ext2(c):
    xs, ys = [c['rbox'][0], c['rbox'][2]], [c['rbox'][1], c['rbox'][3]]
    for (L, nn, x1, y1, x2, y2, w, why) in c['add']:
        if why == 'connector':
            xs += [x1, x2]; ys += [y1, y2]
    return [min(xs) - 0.15, min(ys) - 0.15, max(xs) + 0.15, max(ys) + 0.15]
res = []
n = 0
for a in A:
    for b in Bc:
        if C.d_rect_rect(((a['rbox'][0]+a['rbox'][2])/2, (a['rbox'][1]+a['rbox'][3])/2, (a['rbox'][2]-a['rbox'][0])/2, (a['rbox'][3]-a['rbox'][1])/2),
                         ((b['rbox'][0]+b['rbox'][2])/2, (b['rbox'][1]+b['rbox'][3])/2, (b['rbox'][2]-b['rbox'][0])/2, (b['rbox'][3]-b['rbox'][1])/2)) < 0.254:
            continue
        m = min(a['new_margin'][0], b['new_margin'][0])
        if res and len(res) > 200 and m < res[-1][0] - 1e-9:
            continue
        pm = R.pair_ok(a, b)
        n += 1
        if pm[0] < -1e-6:
            continue
        res.append((min(m, pm[0]), a['i'], b['i'], pm))
        res.sort(key=lambda r: (-r[0]))
        res = res[:300]
print('pairs checked', n)
for r in res[:15]:
    a = [c for c in A if c['i'] == r[1]][0]; b = [c for c in Bc if c['i'] == r[2]][0]
    print('%.4f D14#%d (%.3f,%.3f) D15#%d (%.3f,%.3f) pair %s proof %s/%s' % (r[0], r[1], a['cx'], a['cy'], r[2], b['cx'], b['cy'], r[3], a['proof'], b['proof']))
json.dump([[r[0], r[1], r[2], r[3]] for r in res], open('pairs_D14_D15.json', 'w'))
