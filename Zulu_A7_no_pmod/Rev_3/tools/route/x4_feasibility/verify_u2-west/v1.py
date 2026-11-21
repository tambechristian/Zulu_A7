"""Independent re-measurement of the u2-west candidate (own move code; only body_check.build/check reused)."""
import copy, json, math, sys, collections
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_3/tools'
sys.path.insert(0, T)
import body_check as BC
import route_conn as RC

M0 = json.load(open(T + '/route/bodies/base.json'))
D0 = json.load(open(T + '/route/bodies/comps.json'))
W, H = M0['board']['w'], M0['board']['h']

def ext(ps):
    return (min(p['x'] - p['w'] / 2 for p in ps), min(p['y'] - p['h'] / 2 for p in ps),
            max(p['x'] + p['w'] / 2 for p in ps), max(p['y'] + p['h'] / 2 for p in ps))

# candidate's targets (pad-extent centre, delta rotation CCW)
MOVES = {'U2': (21.75, 15.75, 270), 'LD0': (30.442, 10.628, 0), 'LD1': (30.4, 12.4, 0), 'LD2': (30.4, 14.0, 0),
         'LD3': (30.4, 15.6, 0), 'LD4': (30.4, 17.45, 0), 'BTN': (35.0, 11.8, 0), 'C155': (29.2, 19.8, 0),
         'C158': (17.751, 8.11, 0), 'C159': (23.9, 6.6, 0)}
CX, CY = 30.48, 4.9
if len(sys.argv) > 2:
    CX = float(sys.argv[1]); CY = float(sys.argv[2])

def build(moves=MOVES, s2b=True):
    M = copy.deepcopy(M0); D = copy.deepcopy(D0)
    C = {c['ref']: c for c in D['comps']}
    for ref, (nx, ny, dr) in moves.items():
        ps = [p for p in M['pads'] if p['ref'] == ref]
        e = ext(ps); cx, cy = (e[0] + e[2]) / 2, (e[1] + e[3]) / 2
        a = math.radians(dr); c, s = round(math.cos(a)), round(math.sin(a))
        for p in ps:
            dx, dy = p['x'] - cx, p['y'] - cy
            p['x'], p['y'] = nx + dx * c - dy * s, ny + dx * s + dy * c
            if dr % 180 == 90:
                p['w'], p['h'] = p['h'], p['w']
        C[ref]['rot'] = (C[ref]['rot'] + dr) % 360
    if s2b:
        M['pads'] = [p for p in M['pads'] if p['ref'] != 'X4']
        # KiCad local, rot 180 -> board (cx - x, cy - y)
        for n, net, x, y, w, h in [('1', 'VBATT', -1, -2.85, 1.0, 3.5), ('2', 'GND', 1, -2.85, 1.0, 3.5),
                                   ('MP1', '', -3.35, 2.9, 1.5, 3.4), ('MP2', '', 3.35, 2.9, 1.5, 3.4)]:
            M['pads'].append({'ref': 'X4', 'pad': n, 'net': net, 'x': CX - x, 'y': CY - y, 'shape': 'rect', 'w': w,
                              'h': h, 'layers': ['Top Layer'], 'drill': 0.0, 'plated': False})
        pe = ext([p for p in M['pads'] if p['ref'] == 'X4'])
        body = (CX - 3.95, CY - 4.4, CX + 3.95, CY + 3.2)
        D['mech']['X4'] = {'side': 'Top', 'off': [body[i] - pe[i] for i in range(4)]}
        C['X4']['pattern'] = 'JST-S2B'; C['X4']['rot'] = 180.0
    return M, D

if __name__ == '__main__':
    M, D = build()
    moved = set(MOVES) | {'X4'}
    for r in sorted(moved):
        e = ext([p for p in M['pads'] if p['ref'] == r])
        print('%-5s pad ext x %.3f..%.3f y %.3f..%.3f' % (r, e[0], e[2], e[1], e[3]))
    print('S2B body', (CX - 3.95, CY - 4.4, CX + 3.95, CY + 3.2))
    key = lambda r: r[:4]
    for g in (0.10, 0.20):
        b0 = BC.check(BC.build(*build({}, False)), None, g); b1 = BC.check(BC.build(M, D), None, g)
        k0, k1 = set(map(key, b0)), set(map(key, b1))
        print('gap %.2f whole-board findings before %d after %d' % (g, len(k0), len(k1)))
        print('  NEW:', sorted(k1 - k0)); print('  GONE:', sorted(k0 - k1))
        newd = [r for r in b1 if key(r) in k1 - k0]
        for r in sorted(newd, key=lambda r: r[5])[:20]:
            print('   ', r)
    # pad-pad (outer layers) all pairs involving moved parts, and edge
    def outer(p):
        return set(p['layers'] or BC.STACK) & {'Top Layer', 'Bottom Layer'}
    def pgap(a, b):
        if RC.pad_round(a) or RC.pad_round(b):
            c, r = (a, b) if RC.pad_round(a) else (b, a)
            if RC.pad_round(r):
                return math.hypot(a['x'] - b['x'], a['y'] - b['y']) - (min(a['w'], a['h']) + min(b['w'], b['h'])) / 2
            return RC.pad_point(r, c['x'], c['y']) - min(c['w'], c['h']) / 2
        dx = abs(a['x'] - b['x']) - (a['w'] + b['w']) / 2; dy = abs(a['y'] - b['y']) - (a['h'] + b['h']) / 2
        if dx > 0 and dy > 0: return math.hypot(dx, dy)
        return max(dx, dy)
    rows = []
    mv = [p for p in M['pads'] if p['ref'] in moved]
    for a in mv:
        e = (a['x'] - a['w'] / 2, a['y'] - a['h'] / 2, a['x'] + a['w'] / 2, a['y'] + a['h'] / 2)
        de = min(e[0], e[1], W - e[2], H - e[3])
        if de < 0.5: rows.append(('edge', a['ref'] + '.' + a['pad'], round(de, 3)))
        for b in M['pads']:
            if b['ref'] == a['ref'] or not (outer(a) & outer(b)): continue
            g = pgap(a, b)
            if g < 0.3: rows.append(('padpad', a['ref'] + '.' + a['pad'], b['ref'] + '.' + b['pad'], round(g, 3)))
    for r in sorted(set(rows), key=lambda r: r[-1]): print(r)
    json.dump({'pads': [p for p in M['pads'] if p['ref'] in moved]}, open('moved_pads.json', 'w'))
