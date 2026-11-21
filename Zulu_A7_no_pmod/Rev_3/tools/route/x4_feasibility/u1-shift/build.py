import json, copy, sys, math, subprocess
exec(open('geo.py').read())
P0 = bc.build(M, D)
U1b = P0['Top']['U1']['body'][0]
GRP = sorted([r for r, v in P0['Bottom'].items() if v['body'] and U1b[0] <= (v['body'][0][0]+v['body'][0][2])/2 <= U1b[2]
       and U1b[1] <= (v['body'][0][1]+v['body'][0][3])/2 <= U1b[3]] + ['C119', 'C121', 'C122'])
CAPS = {  # old grid columns -> list in row order (south->north)
    0: ['C140', 'C143', 'C146', 'C93'], 1: ['C141', 'C144', 'C85', 'C97'], 2: ['C142', 'C145', 'C86', 'C98']}
TO_BOTTOM = {'R127': 2.3, 'R129': 2.3, 'R130': 2.3, 'R131': 2.3, 'R132': 2.3, 'C157': 2.3}   # dx when flipped to Bottom

def centre(ref, M):
    ps = [p for p in M['pads'] if p['ref'] == ref]
    return ((min(p['x']-p['w']/2 for p in ps)+max(p['x']+p['w']/2 for p in ps))/2,
            (min(p['y']-p['h']/2 for p in ps)+max(p['y']+p['h']/2 for p in ps))/2)

def build(dx1=3.5, u2=(5.75, 0.15), u4=(3.5, 0.3), q1=(44.85, 21.1), s2b_cx=29.2, s2b_cy=4.9,
          cap_cols=None, cap_rows=(3.75, 6.983, 10.217, 13.45)):
    M2 = copy.deepcopy(M); D2 = copy.deepcopy(D)
    moves = {}
    def mv(ref, dx, dy, side=None):
        for p in M2['pads']:
            if p['ref'] == ref:
                if side == 'Bottom':   # mirror about the part centre in x
                    cx, cy = c0
                    p['x'] = 2*cx - p['x']
                    p['layers'] = ['Bottom Layer']
                p['x'] += dx; p['y'] += dy
        if side == 'Bottom':
            for c in D2['comps']:
                if c['ref'] == ref: c['layer'] = 'BOTTOM'
    # X4 -> S2B
    M2['pads'] = [p for p in M2['pads'] if p['ref'] != 'X4']
    pads, body = s2b(s2b_cx, s2b_cy)
    nets = {'1': 'VBATT', '2': 'GND', 'MP1': '', 'MP2': ''}
    for q in pads:
        M2['pads'].append(dict(ref='X4', pad=q['pad'], net=nets[q['pad']], x=q['x'], y=q['y'], shape='rect', w=q['w'], h=q['h'],
                               layers=['Top Layer'], drill=0.0, plated=False))
    pe = (s2b_cx-4.1, s2b_cy-4.6, s2b_cx+4.1, s2b_cy+4.6)
    D2['mech']['X4'] = {'side': 'Top', 'off': [body[0]-pe[0], body[1]-pe[1], body[2]-pe[2], body[3]-pe[3]]}
    moves['X4'] = 'replaced by JST S2B-PH-SM4-TB, Top, rot 180, centre (%.3f, %.3f) (pads %.2f..%.2f x %.2f..%.2f)' % (s2b_cx, s2b_cy, *pe[::2], *pe[1::2]) if False else \
        'S2B-PH-SM4-TB Top rot 180 centre (%.3f, %.3f); pads x %.2f..%.2f y %.2f..%.2f; body x %.2f..%.2f y %.2f..%.2f' % (
            s2b_cx, s2b_cy, pe[0], pe[2], pe[1], pe[3], body[0], body[2], body[1], body[3])
    for ref, (dx, dy) in [('U2', u2), ('U4', u4)]:
        c0 = centre(ref, M); mv(ref, dx, dy); moves[ref] = ((round(c0[0],3), round(c0[1],3)), (round(c0[0]+dx,3), round(c0[1]+dy,3)), 'Top, rot unchanged')
    c0 = centre('U1', M); mv('U1', dx1, 0); moves['U1'] = ((round(c0[0],3), round(c0[1],3)), (round(c0[0]+dx1,3), round(c0[1],3)), 'Top, rot 0')
    for r in GRP:
        c0 = centre(r, M); mv(r, dx1, 0); moves[r] = ((round(c0[0],3), round(c0[1],3)), (round(c0[0]+dx1,3), round(c0[1],3)), 'Bottom, with U1')
    c0 = centre('Q1', M); mv('Q1', q1[0]-c0[0], q1[1]-c0[1]); moves['Q1'] = ((round(c0[0],3), round(c0[1],3)), q1, 'Top rot 0')
    if cap_cols is None:
        x0 = U1b[2] + dx1 + 0.1 + 0.75
        cap_cols = (x0, x0+1.7, x0+3.4)
    for k, refs in CAPS.items():
        for j, r in enumerate(refs):
            c0 = centre(r, M); mv(r, cap_cols[k]-c0[0], cap_rows[j]-c0[1])
            moves[r] = ((round(c0[0],3), round(c0[1],3)), (round(cap_cols[k],3), round(cap_rows[j],3)), 'Top rot 90')
    for r, dx in TO_BOTTOM.items():
        c0 = centre(r, M); mv(r, dx, 0, side='Bottom')
        moves[r] = ((round(c0[0],3), round(c0[1],3)), (round(c0[0]+dx,3), round(c0[1],3)), 'Top -> BOTTOM (mirrored)')
    return M2, D2, moves

def findings(M2, D2, gapv=0.10):
    res = bc.check(bc.build(M2, D2), None, gapv)
    worst = {}
    for r in res:
        k = r[:4]
        if k not in worst or r[5] < worst[k][5]: worst[k] = r
    return worst

def padpad(M2, moved, minc=0.2):
    """pad-to-pad copper clearance for every moved part's pads vs every other part's pads on a shared copper layer,
    plus board-edge clearance 0.30.  Returns list of violations (ref, pad, other, pad, gap)."""
    out = []
    def lay(p): return set(p['layers'] or bc.STACK)
    mp = [p for p in M2['pads'] if p['ref'] in moved]
    for p in mp:
        b = box(p)
        e = min(b[0], b[1], W-b[2], H-b[3])
        if e < 0.3 - 1e-9: out.append((p['ref'], p['pad'], 'EDGE', '', round(e, 3)))
        for q in M2['pads']:
            if q['ref'] == p['ref'] or not (lay(p) & lay(q)): continue
            if q['ref'] in moved and q['ref'] < p['ref']: continue
            g = pgap(q, b) if q.get('shape') == 'circle' else bc.gap(box(q), b)
            if g < minc - 1e-9: out.append((p['ref'], p['pad'], q['ref'], q['pad'], round(g, 3)))
    return out
