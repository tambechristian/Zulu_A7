"""judge.py <base_moved.json> <base_unmoved.json> <plan.json> <out_dir>

Independent judge of a composed Rev 2 plan.
  1. emit-readiness: every 'remove' track / 'remove_vias' via is matched with emit_copper's own rules
     (track: net, layer, width +-0.002, ends either way +-0.002; via: net, hole +-0.002, centre +-0.002, span ends);
     Kill counts must equal the list lengths and each entry must hit exactly one board object.
  2. result board = base_moved - (emit-matched objects) + plan  -> out_dir/result.json (for prune_stubs / route_conn)
  3. full-board exact DRC (route_check's rules: clearance per R.clearance, hole-hole 0.24, edge 0.30) on the result
     AND on the unmoved base; violations keyed by object identity; NEW = in result, not in the unmoved base.
     This covers KEPT copper next to moved lands, which route_check never checks.
  4. via-in-SMD-pad audit on the result (through: must be 0; microvias: list those not on the unmoved board)
  5. counts, added length, USB metrics.
"""
import json
import math
import os
import sys
from collections import Counter, defaultdict

TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools'
sys.path.insert(0, TOOLS)
import route_conn as C  # noqa: E402
import router as R  # noqa: E402

STACK = R.STACK


def span(v):
    if 'span' in v:
        return list(v['span'])
    return STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]


def vkind(v):
    s = span(v)
    if s == STACK:
        return 'through'
    if s == ['L3-SIG', 'L4-SIG']:
        return 'buried L3-L4'
    return 'laser %s-%s' % (s[0].split('-')[0].replace(' Layer', ''), s[-1].split('-')[0].replace(' Layer', ''))


def tkey(t):
    a = (round(t['x1'], 3), round(t['y1'], 3))
    b = (round(t['x2'], 3), round(t['y2'], 3))
    return ('t', t['net'], t['layer'], round(t['w'], 4), tuple(sorted((a, b))))


def vkey(v):
    s = span(v)
    return ('v', v['net'], round(v['x'], 3), round(v['y'], 3), round(v['hole'], 3), s[0], s[-1])


def pkey(p):
    return ('p', p['ref'], p['pad'])


def tlen(t):
    return math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1'])


# ---------------------------------------------------------------------------------------------------- emit matching
def emit_match(B, P):
    rm, rmv = P.get('remove', []), P.get('remove_vias', [])
    probs = []
    kill_t = []                      # emit adds a board track once per matching line
    hits_per_rm = [0] * len(rm)
    by = defaultdict(list)
    for i, r in enumerate(rm):
        by[(r['net'], r['layer'])].append(i)

    def near(a, b):
        return abs(a - b) < 0.002
    for j, t in enumerate(B['tracks']):
        for i in by.get((t['net'], t['layer']), ()):
            r = rm[i]
            if not near(t['w'], r['w']):
                continue
            f = near(t['x1'], r['x1']) and near(t['y1'], r['y1']) and near(t['x2'], r['x2']) and near(t['y2'], r['y2'])
            b = near(t['x1'], r['x2']) and near(t['y1'], r['y2']) and near(t['x2'], r['x1']) and near(t['y2'], r['y1'])
            if f or b:
                kill_t.append(j)
                hits_per_rm[i] += 1
    if len(kill_t) != len(rm):
        probs.append('emit would REFUSE: track Kill.Count %d != %d' % (len(kill_t), len(rm)))
    for i, h in enumerate(hits_per_rm):
        if h != 1:
            probs.append('remove track matches %d board tracks: %s' % (h, rm[i]))
    if len(set(kill_t)) != len(kill_t):
        probs.append('a board track is matched by several remove lines')
    kill_v = set()
    hits_per_rmv = [0] * len(rmv)
    for j, v in enumerate(B['vias']):
        hit = False
        s = span(v)
        for i, r in enumerate(rmv):
            rs = span(r)
            if r['net'] == v['net'] and near(v['hole'], r['hole']) and near(v['x'], r['x']) and near(v['y'], r['y']) \
                    and rs[0] == s[0] and rs[-1] == s[-1]:
                hit = True
                hits_per_rmv[i] += 1
        if hit:
            kill_v.add(j)
    if len(kill_v) != len(rmv):
        probs.append('emit would REFUSE: via KillV.Count %d != %d' % (len(kill_v), len(rmv)))
    for i, h in enumerate(hits_per_rmv):
        if h != 1:
            probs.append('remove via matches %d board vias: %s' % (h, rmv[i]))
    return set(kill_t), kill_v, probs


# ---------------------------------------------------------------------------------------------------- DRC
def pad_layers(p):
    return p['layers'] or (STACK if p['drill'] > 0 else [])


def pad_pad(a, b):
    ra, rb = C.pad_round(a), C.pad_round(b)
    if ra and rb:
        return max(0.0, math.hypot(a['x'] - b['x'], a['y'] - b['y']) - min(a['w'], a['h']) / 2 - min(b['w'], b['h']) / 2)
    if ra:
        return max(0.0, C.pad_point(b, a['x'], a['y']) - min(a['w'], a['h']) / 2)
    if rb:
        return max(0.0, C.pad_point(a, b['x'], b['y']) - min(b['w'], b['h']) / 2)
    dx = max(abs(a['x'] - b['x']) - (a['w'] + b['w']) / 2, 0)
    dy = max(abs(a['y'] - b['y']) - (a['h'] + b['h']) / 2, 0)
    return math.hypot(dx, dy)


def gap(ka, a, kb, b):
    if ka > kb:
        ka, a, kb, b = kb, b, ka, a
    # order: 'p' < 't' < 'v'
    if ka == 'p' and kb == 'p':
        return pad_pad(a, b)
    if ka == 'p' and kb == 't':
        return C.pad_seg(a, (b['x1'], b['y1'], b['x2'], b['y2'])) - b['w'] / 2
    if ka == 'p' and kb == 'v':
        return C.pad_point(a, b['x'], b['y']) - b['size'] / 2
    if ka == 't' and kb == 't':
        return C.seg_seg((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2'])) - a['w'] / 2 - b['w'] / 2
    if ka == 't' and kb == 'v':
        return C.seg_dist(a['x1'], a['y1'], a['x2'], a['y2'], b['x'], b['y']) - a['w'] / 2 - b['size'] / 2
    return math.hypot(a['x'] - b['x'], a['y'] - b['y']) - a['size'] / 2 - b['size'] / 2


def bbox(k, o):
    if k == 'p':
        return o['x'] - o['w'] / 2, o['y'] - o['h'] / 2, o['x'] + o['w'] / 2, o['y'] + o['h'] / 2
    if k == 't':
        r = o['w'] / 2
        return min(o['x1'], o['x2']) - r, min(o['y1'], o['y2']) - r, max(o['x1'], o['x2']) + r, max(o['y1'], o['y2']) + r
    r = o['size'] / 2
    return o['x'] - r, o['y'] - r, o['x'] + r, o['y'] + r


def okey(k, o):
    return pkey(o) if k == 'p' else tkey(o) if k == 't' else vkey(o)


CELL = 0.5
MARG = 0.11


def drc(M):
    W, H = M['board']['w'], M['board']['h']
    viol = {}
    for layer in STACK:
        objs = []
        for p in M['pads']:
            if layer in pad_layers(p):
                objs.append(('p', p))
        for t in M['tracks']:
            if t['layer'] == layer:
                objs.append(('t', t))
        for v in M['vias']:
            if layer in v['span']:
                objs.append(('v', v))
        grid = defaultdict(list)
        for i, (k, o) in enumerate(objs):
            x0, y0, x1, y1 = bbox(k, o)
            for gx in range(int(math.floor((x0 - MARG) / CELL)), int(math.floor((x1 + MARG) / CELL)) + 1):
                for gy in range(int(math.floor((y0 - MARG) / CELL)), int(math.floor((y1 + MARG) / CELL)) + 1):
                    grid[(gx, gy)].append(i)
        seen = set()
        for cell in grid.values():
            for a in range(len(cell)):
                i = cell[a]
                ki, oi = objs[i]
                for b in range(a + 1, len(cell)):
                    j = cell[b]
                    pr = (i, j) if i < j else (j, i)
                    if pr in seen:
                        continue
                    seen.add(pr)
                    kj, oj = objs[j]
                    ni, nj = oi.get('net') or '', oj.get('net') or ''
                    if ni and ni == nj:
                        continue
                    if ki == 'p' and kj == 'p' and oi['ref'] == oj['ref']:
                        continue                  # footprint-internal pad spacing is the footprint's business
                    clr = max(R.clearance(ni, layer), R.clearance(nj, layer))
                    g = gap(ki, oi, kj, oj)
                    if g < clr - 1e-4:
                        key = ('clr', layer, frozenset((okey(ki, oi), okey(kj, oj))))
                        viol[key] = 'clearance %s %.4f < %.3f: %s %s | %s %s' % (
                            layer, g, clr, ki, desc(ki, oi), kj, desc(kj, oj))
    # hole-hole: via-via (any nets, sharing a layer, not the same point), via-drilled pad (other net)
    vias = M['vias']
    grid = defaultdict(list)
    for i, v in enumerate(vias):
        grid[(int(v['x'] // 1.0), int(v['y'] // 1.0))].append(i)
    for i, v in enumerate(vias):
        gx, gy = int(v['x'] // 1.0), int(v['y'] // 1.0)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in grid.get((gx + dx, gy + dy), ()):
                    if j <= i:
                        continue
                    o = vias[j]
                    if not set(o['span']) & set(v['span']):
                        continue
                    dd = math.hypot(o['x'] - v['x'], o['y'] - v['y'])
                    if dd < 1e-6:
                        continue
                    d = dd - o['hole'] / 2 - v['hole'] / 2
                    if d < R.HOLE_HOLE - 1e-4:
                        key = ('hole', frozenset((vkey(v), vkey(o))))
                        viol[key] = 'hole-hole %.4f: via %s | via %s' % (d, desc('v', v), desc('v', o))
    drilled = [p for p in M['pads'] if p['drill'] > 0]
    for v in vias:
        for p in drilled:
            if p['net'] == v['net'] and p['net']:
                continue
            d = math.hypot(p['x'] - v['x'], p['y'] - v['y']) - p['drill'] / 2 - v['hole'] / 2
            if d < R.HOLE_HOLE - 1e-4:
                key = ('hole', frozenset((vkey(v), pkey(p))))
                viol[key] = 'hole-pad %.4f: via %s | pad %s' % (d, desc('v', v), desc('p', p))

    def edge_ok_pt(x, y, r):
        if x - r < R.EDGE or y - r < R.EDGE or x + r > W - R.EDGE or y + r > H - R.EDGE:
            return False
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            if abs(x - cx) < 1.2 + r and abs(y - cy) < 1.2 + r:
                return False
        return True
    for t in M['tracks']:
        if not all(edge_ok_pt(x, y, t['w'] / 2) for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2']))):
            viol[('edge', tkey(t))] = 'edge track %s' % desc('t', t)
    for v in vias:
        if not edge_ok_pt(v['x'], v['y'], v['size'] / 2):
            viol[('edge', vkey(v))] = 'edge via %s' % desc('v', v)
    return viol


def desc(k, o):
    if k == 'p':
        return '%s-%s(%s)@%.3f,%.3f' % (o['ref'], o['pad'], o['net'], o['x'], o['y'])
    if k == 't':
        return '%s %s w%.3f (%.3f,%.3f)-(%.3f,%.3f)' % (o['net'], o['layer'], o['w'], o['x1'], o['y1'], o['x2'], o['y2'])
    s = o['span']
    return '%s %.3f,%.3f %s>%s %.2f/%.2f' % (o['net'], o['x'], o['y'], s[0][:3], s[-1][:3], o['size'], o['hole'])


# ---------------------------------------------------------------------------------------------------- via in pad
def via_pad_hits(v, smd):
    out = []
    r = v['size'] / 2
    for p in smd:
        if not set(p['layers']) & set(v['span']):
            continue
        if C.pad_round(p):
            d = math.hypot(v['x'] - p['x'], v['y'] - p['y']) - min(p['w'], p['h']) / 2
        else:
            d = math.hypot(max(abs(v['x'] - p['x']) - p['w'] / 2, 0), max(abs(v['y'] - p['y']) - p['h'] / 2, 0))
        if d < r - 1e-4:
            out.append(('%s-%s(%s)' % (p['ref'], p['pad'], p['net']), round(r - d, 4)))
    return out


# ---------------------------------------------------------------------------------------------------- USB
def usb_metrics(M):
    P = [t for t in M['tracks'] if t['net'] == 'USB_D_P']
    N = [t for t in M['tracks'] if t['net'] == 'USB_D_N']
    out = {'P_mm': round(sum(map(tlen, P)), 4), 'N_mm': round(sum(map(tlen, N)), 4)}
    out['mismatch_mm'] = round(abs(out['P_mm'] - out['N_mm']), 4)
    out['layers'] = sorted({t['layer'] for t in P + N})
    out['widths'] = sorted({round(t['w'], 4) for t in P + N})
    out['vias'] = sum(1 for v in M['vias'] if v['net'] in ('USB_D_P', 'USB_D_N'))
    out['segments'] = [len(P), len(N)]
    for tol in (0.005, 0.01, 0.03):
        c = 0.0
        for t in P:
            L = tlen(t)
            n = max(1, int(L / 0.005))
            for k in range(n):
                x = t['x1'] + (t['x2'] - t['x1']) * (k + 0.5) / n
                y = t['y1'] + (t['y2'] - t['y1']) * (k + 0.5) / n
                d = min(C.seg_dist(u['x1'], u['y1'], u['x2'], u['y2'], x, y) for u in N)
                if abs(d - 0.30) <= tol:
                    c += L / n
        out['coupled_mm_tol%.3f' % tol] = round(c, 3)
    # minimum edge-to-edge gap between P and N
    out['min_gap_mm'] = round(min(C.seg_seg((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2']))
                                  - a['w'] / 2 - b['w'] / 2 for a in P for b in N), 4)
    out['geom'] = sorted(tkey(t)[1:] for t in P + N)
    return out


def main():
    Bm = json.load(open(sys.argv[1]))
    B0 = json.load(open(sys.argv[2]))
    P = json.load(open(sys.argv[3]))
    out = sys.argv[4]
    os.makedirs(out, exist_ok=True)
    for v in Bm['vias'] + B0['vias']:
        v['span'] = span(v)
    rep = {'plan': sys.argv[3]}
    kt, kv, probs = emit_match(Bm, P)
    rep['emit_problems'] = probs
    newv = [dict(v, span=span(v)) for v in P['vias']]
    Res = {'board': Bm['board'], 'planes': Bm['planes'], 'pads': Bm['pads'],
           'tracks': [t for i, t in enumerate(Bm['tracks']) if i not in kt] + P['tracks'],
           'vias': [v for i, v in enumerate(Bm['vias']) if i not in kv] + newv}
    json.dump(Res, open(os.path.join(out, 'result.json'), 'w'))
    oc = C.open_count(C.islands(Res))
    rep['open_exact'] = sum(oc.values())
    rep['open_nets_exact'] = sorted(oc)
    # duplicates
    tk = Counter(tkey(t) for t in Res['tracks'])
    vk = Counter(vkey(v) for v in Res['vias'])
    rep['dup_tracks_result'] = sum(c - 1 for c in tk.values() if c > 1)
    rep['dup_vias_result'] = sum(c - 1 for c in vk.values() if c > 1)
    rep['zero_len_tracks_plan'] = sum(1 for t in P['tracks'] if tlen(t) < 1e-6)
    rep['short_tracks_plan_lt_0.01'] = sum(1 for t in P['tracks'] if tlen(t) < 0.01)
    # DRC
    v_res = drc(Res)
    v_b0 = drc(B0)
    v_bm = drc(Bm)
    new = {k: s for k, s in v_res.items() if k not in v_b0}
    rep['drc_counts'] = {'unmoved_base': len(v_b0), 'base_moved': len(v_bm), 'result': len(v_res), 'new_vs_unmoved': len(new),
                         'fixed_vs_unmoved': sum(1 for k in v_b0 if k not in v_res)}
    rep['drc_new'] = sorted(new.values())
    # via-in-pad
    smd = [p for p in Bm['pads'] if not p['drill']]
    smd0 = [p for p in B0['pads'] if not p['drill']]
    old_uvia_pad = set()
    for v in B0['vias']:
        if v['span'] != STACK and via_pad_hits(v, smd0):
            old_uvia_pad.add(vkey(v))
    th, uv_new, uv_all = [], [], 0
    for v in Res['vias']:
        h = via_pad_hits(v, smd)
        if not h:
            continue
        if v['span'] == STACK:
            th.append((desc('v', v), h))
        else:
            uv_all += 1
            if vkey(v) not in old_uvia_pad:
                uv_new.append((desc('v', v), h))
    rep['through_via_in_smd_pad_result'] = th
    rep['uvia_in_smd_pad_result_total'] = uv_all
    rep['uvia_in_smd_pad_unmoved_base'] = len(old_uvia_pad)
    rep['uvia_in_smd_pad_new'] = uv_new
    rep['new_through_vias'] = [desc('v', v) for v in newv if v['span'] == STACK]
    # counts
    rm_tk = Counter(tkey(t) for t in P.get('remove', []))
    rm_vk = Counter(vkey(v) for v in P.get('remove_vias', []))
    readd_t = sum(1 for t in P['tracks'] if tkey(t) in rm_tk)
    readd_v = sum(1 for v in P['vias'] if vkey(v) in rm_vk)
    rep['counts'] = {
        'tracks_added': len(P['tracks']), 'tracks_removed': len(P.get('remove', [])),
        'vias_added': len(P['vias']), 'vias_removed': len(P.get('remove_vias', [])),
        'tracks_readded_identical': readd_t, 'vias_readded_identical': readd_v,
        'vias_added_by_type': dict(Counter(vkind(v) for v in P['vias'])),
        'vias_removed_by_type': dict(Counter(vkind(v) for v in P.get('remove_vias', []))),
        'net_via_change_by_type': {},
        'added_track_mm': round(sum(map(tlen, P['tracks'])), 2),
        'removed_track_mm': round(sum(map(tlen, P.get('remove', []))), 2),
        'added_track_mm_excl_readded': round(sum(tlen(t) for t in P['tracks'] if tkey(t) not in rm_tk), 2),
        'board_tracks': len(Res['tracks']), 'board_vias': len(Res['vias']),
        'board_vias_unmoved': len(B0['vias']), 'board_tracks_unmoved': len(B0['tracks']),
    }
    a, r = Counter(vkind(v) for v in P['vias']), Counter(vkind(v) for v in P.get('remove_vias', []))
    rep['counts']['net_via_change_by_type'] = {k: a[k] - r[k] for k in sorted(set(a) | set(r))}
    rep['counts']['board_via_types'] = dict(Counter(vkind(v) for v in Res['vias']))
    rep['counts']['unmoved_via_types'] = dict(Counter(vkind(v) for v in B0['vias']))
    rep['usb'] = usb_metrics(Res)
    json.dump(rep, open(os.path.join(out, 'judge.json'), 'w'), indent=1, default=str)
    show = dict(rep)
    show['usb'] = {k: v for k, v in rep['usb'].items() if k != 'geom'}
    print(json.dumps(show, indent=1, default=str))


if __name__ == '__main__':
    main()
