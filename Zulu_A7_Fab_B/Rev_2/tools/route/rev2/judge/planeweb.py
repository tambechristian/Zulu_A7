"""planeweb.py: raster the L2-GND / L5-VCC3V3 pours (board inset 0.3, minus other-net clearance zones: through via
0.175, other vias / pads / tracks 0.09) and report components + plane-net vias / drilled pads not on the main pour.
Also after an opening of radius 0.125 (necks under 0.25 mm do not conduct)."""
import json, math, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, '.')
import judge as J
G = 0.02
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'


def run(M, tag):
    W, H = M['board']['w'], M['board']['h']
    nx, ny = int(W / G) + 1, int(H / G) + 1
    X = (np.arange(nx) + 0.0) * G
    Y = (np.arange(ny) + 0.0) * G
    out = {}
    for layer, net in (('L2-GND', 'GND'), ('L5-VCC3V3', 'VCC3V3')):
        a = np.ones((ny, nx), bool)
        e = int(round(0.3 / G))
        a[:e, :] = a[-e:, :] = False
        a[:, :e] = a[:, -e:] = False

        def disk(x, y, r):
            i0, i1 = max(0, int((x - r) / G) - 1), min(nx, int((x + r) / G) + 2)
            j0, j1 = max(0, int((y - r) / G) - 1), min(ny, int((y + r) / G) + 2)
            xx, yy = np.meshgrid(X[i0:i1], Y[j0:j1])
            a[j0:j1, i0:i1] &= (xx - x) ** 2 + (yy - y) ** 2 > r * r

        def rect(x, y, w, h, c):
            i0, i1 = max(0, int((x - w / 2 - c) / G)), min(nx, int((x + w / 2 + c) / G) + 2)
            j0, j1 = max(0, int((y - h / 2 - c) / G)), min(ny, int((y + h / 2 + c) / G) + 2)
            xx, yy = np.meshgrid(X[i0:i1], Y[j0:j1])
            dx = np.maximum(np.abs(xx - x) - w / 2, 0)
            dy = np.maximum(np.abs(yy - y) - h / 2, 0)
            a[j0:j1, i0:i1] &= dx * dx + dy * dy > c * c

        mine = []
        for v in M['vias']:
            if layer not in v['span']:
                continue
            if v['net'] == net:
                mine.append(('v', v['x'], v['y']))
                continue
            c = 0.175 if v['span'] == J.STACK else 0.09
            disk(v['x'], v['y'], v['size'] / 2 + c)
        for p in M['pads']:
            if layer not in J.pad_layers(p):
                continue
            if p['net'] == net:
                mine.append(('p', p['x'], p['y']))
                continue
            if J.C.pad_round(p):
                disk(p['x'], p['y'], min(p['w'], p['h']) / 2 + 0.09)
            else:
                rect(p['x'], p['y'], p['w'], p['h'], 0.09)
        for t in M['tracks']:
            if t['layer'] != layer or t['net'] == net:
                continue
            L = J.tlen(t)
            n = max(1, int(L / 0.01))
            for k in range(n + 1):
                disk(t['x1'] + (t['x2'] - t['x1']) * k / n, t['y1'] + (t['y2'] - t['y1']) * k / n, t['w'] / 2 + 0.09)
        res = {}
        for mode in ('raw', 'open0.125'):
            b = a
            if mode != 'raw':
                r = int(round(0.125 / G))
                yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
                st = xx * xx + yy * yy <= r * r
                b = ndimage.binary_opening(a, structure=st)
            lab, n = ndimage.label(b, structure=np.ones((3, 3)))
            sizes = np.bincount(lab.ravel())
            sizes[0] = 0
            main = int(np.argmax(sizes))
            off = []
            comps = set()
            for kind, x, y in mine:
                i, j = int(round(x / G)), int(round(y / G))
                l = lab[j, i]
                if l == 0:            # the via centre sits in a cleared pixel? look in a small window
                    w = lab[max(0, j - 8):j + 9, max(0, i - 8):i + 9]
                    vals = w[w > 0]
                    l = int(np.bincount(vals).argmax()) if vals.size else 0
                comps.add(l)
                if l != main:
                    off.append((kind, round(x, 3), round(y, 3), int(l)))
            res[mode] = {'components': int(n), 'components_with_net_objects': len(comps - {0}), 'main_area_mm2': round(float(sizes[main]) * G * G, 2),
                         'objects': len(mine), 'objects_off_main': off}
        out[layer] = res
    return out


if __name__ == '__main__':
    R = {}
    B0 = json.load(open(T + 'model_base.json'))
    for v in B0['vias']:
        v['span'] = J.span(v)
    R['unmoved'] = run(B0, 'unmoved')
    for k in sys.argv[1:]:
        M = json.load(open(k + '/result.json'))
        R[k] = run(M, k)
    json.dump(R, open('planeweb.json', 'w'), indent=1)
    for k, d in R.items():
        for layer, res in d.items():
            for mode, r in res.items():
                print(k, layer, mode, 'comps', r['components'], 'comps w/ net objs', r['components_with_net_objects'], 'main mm2', r['main_area_mm2'],
                      'objs', r['objects'], 'off-main', len(r['objects_off_main']))
