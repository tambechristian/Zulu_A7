# -*- coding: utf-8 -*-
"""Check a routing plan against the board as saved and turn it into DelphiScript.

    python tools/route_emit.py <plan.json> <BlockName>            check only
    python tools/route_emit.py <plan.json> <BlockName> --require-complete   fail unless all 39 nets join
    python tools/route_emit.py <plan.json> <BlockName> --write    also write the
        Place<BlockName> / Remove<BlockName> procedures into tools/ZuluSetup.pas

The plan has the fan-out's schema: {"vias": [{net,x,y}], "tracks": [{net,x1,y1,
x2,y2,layer,width}]}.  The check is independent of whatever produced the plan:

  every new via   : 0.20/0.35; >= clearance from every existing via, through-hole
                    pad, Top/Bottom pad it does not belong to (its land on the
                    outer layers, its 0.70 anti-pad is a plane matter); >= 0.44
                    centre-to-centre from every other via, new or old
  every new track : on Top / L3-SIG / L4-SIG / Bottom; width within its net's rule
                    on that layer; >= the layer clearance from every foreign object
                    on that layer -- existing tracks (segment-segment), vias and
                    through-hole pads (every layer), SMD pads (outer layers only),
                    and every other new track of a different net
  clearance       : 0.09 everywhere, except an SDRAM-net track on L3/L4 keeps 0.10
                    from everything and an SDRAM-CLK track on L3/L4 keeps 0.20
                    (the two Clearance_SDRAM rules, second scope All)
  connectivity    : every new track end lands on a same-net via/pad/ball/track end
                    (within 1 um) unless the plan marks it free_end

Remove<BlockName> deletes exactly the primitives the plan placed, matched by
net, layer and coordinates -- never by area -- so it stays valid after further
routing.  Coordinates in mm on the board origin.
"""
import io
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INPUTS = os.path.join(HERE, 'route_inputs.json')
SETUP = os.path.join(HERE, 'ZuluSetup.pas')
LAYER_ENUM = {'Top': 'eTopLayer', 'L3-SIG': 'eMidLayer1', 'L4-SIG': 'eMidLayer2', 'Bottom': 'eBottomLayer'}
VIA_LAND, VIA_HOLE, VIA_PITCH = 0.35, 0.20, 0.44
EPS = 1e-6


def seg_dist(a, b):
    """distance between two segments a=(x1,y1,x2,y2), b=(x1,y1,x2,y2)"""
    def pt_seg(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    def inter(p1, p2, p3, p4):
        d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
        if abs(d) < 1e-12:
            return False
        t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
        u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
        return 0 <= t <= 1 and 0 <= u <= 1
    if inter((a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])):
        return 0.0
    return min(pt_seg(a[0], a[1], *b), pt_seg(a[2], a[3], *b), pt_seg(b[0], b[1], *a), pt_seg(b[2], b[3], *a))


def pt_rect(px, py, cx, cy, sx, sy):
    dx = max(abs(px - cx) - sx / 2, 0.0)
    dy = max(abs(py - cy) - sy / 2, 0.0)
    return math.hypot(dx, dy)


def seg_rect(seg, cx, cy, sx, sy):
    """EXACT distance from a segment to an axis-aligned rectangle (0 if they touch).
    2026-09-15: this used to sample 25 points along the segment, which missed a
    0.0893 mm near-miss against a 0.09 rule; it is now closed-form."""
    x1, y1, x2, y2 = seg
    x0r, x1r, y0r, y1r = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    # an endpoint inside, or the segment crossing an edge -> 0
    if x0r <= x1 <= x1r and y0r <= y1 <= y1r:
        return 0.0
    if x0r <= x2 <= x1r and y0r <= y2 <= y1r:
        return 0.0
    edges = ((x0r, y0r, x1r, y0r), (x1r, y0r, x1r, y1r), (x1r, y1r, x0r, y1r), (x0r, y1r, x0r, y0r))
    best = min(seg_dist(seg, e) for e in edges)
    return best


def clearance_for(net, layer, inp):
    r = inp['nets'].get(net)
    if layer in ('L3-SIG', 'L4-SIG') and r is not None:
        return r['clearance']['inner']
    return 0.09


def width_ok(net, layer, w, inp):
    r = inp['nets'].get(net)
    if r is None:
        return w >= 0.0762 - EPS
    wr = r['width']
    if layer == 'Top':
        return wr['top_min'] - EPS <= w <= wr.get('top_max', 0.15) + EPS
    if layer == 'Bottom':
        return wr.get('bottom_min', wr['inner_min']) - EPS <= w <= wr.get('bottom_max', wr['inner_max']) + EPS
    return wr['inner_min'] - EPS <= w <= wr['inner_max'] + EPS


def _key_v(v):
    return (v['net'], round(v['x'], 4), round(v['y'], 4))


def _key_t(t):
    a = (round(t['x1'], 4), round(t['y1'], 4))
    b = (round(t['x2'], 4), round(t['y2'], 4))
    return (t['net'], t['layer']) + tuple(sorted((a, b)))


def apply_removals(inp, plan):
    """a copy of inp with plan['remove'] taken out; every removal must match exactly one existing primitive"""
    rem = plan.get('remove') or {}
    rv = {_key_v(v) for v in rem.get('vias', [])}
    rt = {_key_t(t) for t in rem.get('tracks', [])}
    vias = [v for v in inp['vias'] if _key_v(v) not in rv]
    tracks = [t for t in inp['tracks'] if _key_t(t) not in rt]
    missing = []
    if len(inp['vias']) - len(vias) != len(rv):
        missing.append('remove.vias: %d listed, %d matched' % (len(rv), len(inp['vias']) - len(vias)))
    if len(inp['tracks']) - len(tracks) != len(rt):
        missing.append('remove.tracks: %d listed, %d matched' % (len(rt), len(inp['tracks']) - len(tracks)))
    out = dict(inp)
    out['vias'] = vias
    out['tracks'] = tracks
    return out, missing


POWER = ('GND', 'GNDADC', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VCCADC')


def power_balls_on_vias(inp, plan, u1_lands):
    """every U1 power/GND ball that reached a same-net via before the plan must still reach one"""
    def reaches(vias, tracks, ball):
        net = ball['net']
        segs = [t for t in tracks if t['net'] == net and t['layer'] == 'Top']
        vs = [v for v in vias if v['net'] == net]
        pts = [(ball['x'], ball['y'])]
        for t in segs:
            pts += [(t['x1'], t['y1']), (t['x2'], t['y2'])]
        for v in vs:
            pts.append((v['x'], v['y']))
        # same-net balls are joined too (a chain runs ball to ball)
        for b in u1_lands:
            if b['net'] == net:
                pts.append((b['x'], b['y']))
        n = len(pts)
        adj = [set() for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if abs(pts[i][0] - pts[j][0]) < 1.5e-3 and abs(pts[i][1] - pts[j][1]) < 1.5e-3:
                    adj[i].add(j); adj[j].add(i)
        idx = {}
        k = 1
        for t in segs:
            adj[k].add(k + 1); adj[k + 1].add(k)
            k += 2
        via_ids = set(range(k, k + len(vs)))
        seen = {0}
        stack = [0]
        while stack:
            i = stack.pop()
            if i in via_ids:
                return True
            for j in adj[i]:
                if j not in seen:
                    seen.add(j); stack.append(j)
        return False
    if not plan.get('remove'):
        return []
    after, _ = apply_removals(inp, plan)
    va = after['vias'] + [dict(x=v['x'], y=v['y'], net=v['net']) for v in plan.get('vias', [])]
    ta = after['tracks'] + plan.get('tracks', [])
    lost = []
    for b in u1_lands:
        if b['net'] in POWER and reaches(inp['vias'], inp['tracks'], b) and not reaches(va, ta, b):
            lost.append('power ball U1-%s (%s) no longer reaches a %s via' % (b['pad'], b['net'], b['net']))
    return lost


def check(inp, plan):
    problems = []
    u1_lands = [p for p in inp['top_pads'] if p['ref'] == 'U1']
    problems += power_balls_on_vias(inp, plan, u1_lands)
    inp, missing = apply_removals(inp, plan)
    problems += missing
    vias_old = inp['vias']
    tracks_old = inp['tracks']
    th = inp['th_pads']
    smd = {'Top': inp['top_pads'], 'Bottom': inp['bottom_pads']}
    nv, nt = plan.get('vias', []), plan.get('tracks', [])
    known_nets = set(inp['nets'])
    # vias
    for i, v in enumerate(nv):
        c = 0.10 if v['net'] in known_nets else 0.09
        for w in vias_old:
            d = math.hypot(v['x'] - w['x'], v['y'] - w['y'])
            if d < VIA_PITCH - EPS:
                problems.append('via %d (%s) %.4f from existing via (%s) at %.3f,%.3f' % (i, v['net'], d, w['net'], w['x'], w['y']))
        for j, w in enumerate(nv):
            if j > i and math.hypot(v['x'] - w['x'], v['y'] - w['y']) < VIA_PITCH - EPS:
                problems.append('vias %d and %d %.4f apart' % (i, j, math.hypot(v['x'] - w['x'], v['y'] - w['y'])))
        for p in th:
            if p['net'] == v['net']:
                continue
            d = pt_rect(v['x'], v['y'], p['x'], p['y'], p['sx'], p['sy']) - VIA_LAND / 2
            if d < c - EPS:
                problems.append('via %d (%s) %.4f from TH pad %s-%s (%s)' % (i, v['net'], d, p['ref'], p['pad'], p['net']))
        for L in ('Top', 'Bottom'):
            for p in smd[L]:
                # no via-in-pad and no via touching a pad, whatever its net: a tented via in or at
                # an SMD pad wicks solder (2026-09-15, power feeds)
                d = pt_rect(v['x'], v['y'], p['x'], p['y'], p['sx'], p['sy']) - VIA_LAND / 2
                if d < 0.09 - EPS:
                    problems.append('via %d (%s) %.4f from %s pad %s-%s (%s)' % (i, v['net'], d, L, p['ref'], p['pad'], p['net']))
        for t in tracks_old:
            if t['net'] == v['net']:
                continue
            d = seg_dist((t['x1'], t['y1'], t['x2'], t['y2']), (v['x'], v['y'], v['x'], v['y'])) - t['width'] / 2 - VIA_LAND / 2
            if d < clearance_for(t['net'], t['layer'], inp) - EPS:
                problems.append('via %d (%s) %.4f from existing %s track (%s)' % (i, v['net'], d, t['layer'], t['net']))
    # tracks
    allv = vias_old + [dict(x=v['x'], y=v['y'], size=VIA_LAND, net=v['net']) for v in nv]
    for i, t in enumerate(nt):
        if t['layer'] not in LAYER_ENUM:
            problems.append('track %d layer %r' % (i, t['layer']))
            continue
        if not width_ok(t['net'], t['layer'], t['width'], inp):
            problems.append('track %d (%s, %s) width %.4f outside its rule' % (i, t['net'], t['layer'], t['width']))
        c = clearance_for(t['net'], t['layer'], inp)
        seg = (t['x1'], t['y1'], t['x2'], t['y2'])
        for w in allv:
            if w['net'] == t['net']:
                continue
            d = seg_dist(seg, (w['x'], w['y'], w['x'], w['y'])) - t['width'] / 2 - w['size'] / 2
            if d < c - EPS:
                problems.append('track %d (%s, %s) %.4f from via (%s) at %.3f,%.3f' % (i, t['net'], t['layer'], d, w['net'], w['x'], w['y']))
        for p in th:
            if p['net'] == t['net']:
                continue
            d = seg_rect(seg, p['x'], p['y'], p['sx'], p['sy']) - t['width'] / 2
            if d < c - EPS:
                problems.append('track %d (%s, %s) %.4f from TH pad %s-%s' % (i, t['net'], t['layer'], d, p['ref'], p['pad']))
        if t['layer'] in smd:
            for p in smd[t['layer']]:
                if p['net'] == t['net']:
                    continue
                d = seg_rect(seg, p['x'], p['y'], p['sx'], p['sy']) - t['width'] / 2
                if d < c - EPS:
                    problems.append('track %d (%s, %s) %.4f from pad %s-%s (%s)' % (i, t['net'], t['layer'], d, p['ref'], p['pad'], p['net']))
        for o in tracks_old:
            if o['layer'] != t['layer'] or o['net'] == t['net']:
                continue
            d = seg_dist(seg, (o['x1'], o['y1'], o['x2'], o['y2'])) - t['width'] / 2 - o['width'] / 2
            if d < max(c, clearance_for(o['net'], o['layer'], inp)) - EPS:
                problems.append('track %d (%s, %s) %.4f from existing track (%s)' % (i, t['net'], t['layer'], d, o['net']))
        for j, o in enumerate(nt):
            if j <= i or o['layer'] != t['layer'] or o['net'] == t['net']:
                continue
            d = seg_dist(seg, (o['x1'], o['y1'], o['x2'], o['y2'])) - t['width'] / 2 - o['width'] / 2
            if d < max(c, clearance_for(o['net'], o['layer'], inp)) - EPS:
                problems.append('tracks %d (%s) and %d (%s) on %s %.4f apart' % (i, t['net'], j, o['net'], t['layer'], d))
    # keep-out fills (Altium checks them at the clearance gap) and the board edge
    edge = inp.get('edge_clearance', 0.25)
    ol = inp.get('outline')
    for i, v in enumerate(nv):
        for k in inp.get('keepouts', []):
            d = pt_rect(v['x'], v['y'], (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2, k['x1'] - k['x0'], k['y1'] - k['y0']) - VIA_LAND / 2
            if d < 0.09 - EPS:
                problems.append('via %d (%s) %.4f from the %s keep-out fill' % (i, v['net'], d, k['layer']))
        if ol and min(v['x'] - ol['x0'], ol['x1'] - v['x'], v['y'] - ol['y0'], ol['y1'] - v['y']) - VIA_LAND / 2 < edge - EPS:
            problems.append('via %d (%s) closer than %.2f mm to the board edge' % (i, v['net'], edge))
    for i, t in enumerate(nt):
        seg = (t['x1'], t['y1'], t['x2'], t['y2'])
        for k in inp.get('keepouts', []):
            if k['layer'] != t['layer']:
                continue
            d = seg_rect(seg, (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2, k['x1'] - k['x0'], k['y1'] - k['y0']) - t['width'] / 2
            if d < 0.09 - EPS:
                problems.append('track %d (%s, %s) %.4f from the keep-out fill' % (i, t['net'], t['layer'], d))
        if ol:
            m = min(min(t['x1'], t['x2']) - ol['x0'], ol['x1'] - max(t['x1'], t['x2']),
                    min(t['y1'], t['y2']) - ol['y0'], ol['y1'] - max(t['y1'], t['y2'])) - t['width'] / 2
            if m < edge - EPS:
                problems.append('track %d (%s, %s) %.4f from the board edge (min %.2f)' % (i, t['net'], t['layer'], m, edge))
    # connectivity of new track ends
    anchors = [(v['x'], v['y'], v['net'], 'via') for v in allv]
    anchors += [(p['x'], p['y'], p['net'], 'thpad') for p in th]
    for L in ('Top', 'Bottom'):
        anchors += [(p['x'], p['y'], p['net'], L + 'pad') for p in smd[L]]
    for n, v in inp['nets'].items():
        for e in v['u1']:
            if e.get('x') is not None:
                anchors.append((e['x'], e['y'], n, e['kind']))
    ends = {}
    for t in nt + tracks_old:
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            ends.setdefault((t['net'], t['layer'], round(x, 4), round(y, 4)), 0)
            ends[(t['net'], t['layer'], round(x, 4), round(y, 4))] += 1
    for i, t in enumerate(nt):
        if t.get('free_end'):
            continue
        for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            ok = ends.get((t['net'], t['layer'], round(x, 4), round(y, 4)), 0) >= 2
            ok = ok or any(a[2] == t['net'] and math.hypot(a[0] - x, a[1] - y) < 1e-3 for a in anchors)
            if not ok:
                problems.append('track %d (%s, %s) end %.4f,%.4f connects to nothing of its net' % (i, t['net'], t['layer'], x, y))
    return problems


def completeness(inp, plan, tol=0.0015):
    """For every SDRAM net: is its U3 pad joined to its U1 end through same-net
    copper (new plan + existing board)?  Nodes are track ends, via centres and
    pad/ball/stub-end centres, merged when within tol on the same layer; a via
    joins all four signal layers; an SMD pad joins a track end anywhere inside
    its rectangle on its own layer.  Returns {net: (ok, reason)}."""
    layers = ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')
    out = {}
    for net, v in inp['nets'].items():
        segs = [t for t in plan.get('tracks', []) + inp['tracks'] if t['net'] == net]
        vias = [w for w in plan.get('vias', []) + inp['vias'] if w['net'] == net]
        nodes = []          # (x, y, layer)
        def node(x, y, L):
            for i, (a, b, c) in enumerate(nodes):
                if c == L and abs(a - x) <= tol and abs(b - y) <= tol:
                    return i
            nodes.append((x, y, L))
            return len(nodes) - 1
        adj = {}
        def link(i, j):
            adj.setdefault(i, set()).add(j)
            adj.setdefault(j, set()).add(i)
        for t in segs:
            link(node(t['x1'], t['y1'], t['layer']), node(t['x2'], t['y2'], t['layer']))
        for w in vias:
            ids = [node(w['x'], w['y'], L) for L in layers]
            for j in ids[1:]:
                link(ids[0], j)
        dest = v.get('pads') or [dict(v['u3'][0], layer='Bottom')]
        pad_nodes = []
        for pad in dest:
            pls = layers if pad.get('layer') == 'Multi' else (pad.get('layer') or 'Bottom',)
            ids = [node(pad['x'], pad['y'], L) for L in pls]
            for j in ids[1:]:
                link(ids[0], j)
            for i, (x, y, L) in enumerate(list(nodes)):
                if L in pls and abs(x - pad['x']) <= pad['sx'] / 2 + 1e-9 and abs(y - pad['y']) <= pad['sy'] / 2 + 1e-9:
                    link(ids[0], i)
            pad_nodes.append((ids[0], pad))
        start = pad_nodes[0][0]
        pad = pad_nodes[0][1]
        # every pad of the net -- U1 balls included -- must share one component.  The U1 'end'
        # (moat via / stub end / ball) is informational only: a goal point once went stale when
        # later routing added same-net copper (2026-09-15).
        e = v['u1'][0] if v['u1'] else dict(kind='all pads', ball='-')
        goals = {pn[0] for pn in pad_nodes[1:]} or {start}
        # one full traversal from the first pad; every other pad must be reached.  (The previous
        # version broke out when it popped the first goal without expanding that node, then
        # resumed from the stack -- a pad reachable only through the goal node was missed.)
        seen = {start}
        stack = [start]
        while stack:
            n = stack.pop()
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        others = [pn for pn in pad_nodes[1:] if pn[0] not in seen]
        found = not others
        out[net] = (found, '' if found else 'not all pads of %s in one component' % net)
    return out


def _pas(net):
    return net.replace("'", "''")


def _via_match(vs, var='V'):
    """DelphiScript condition matching any of the vias vs (net name + centre within 1 um)"""
    conds = ["((nm = '%s') And (Abs(x - %.4f) < 0.001) And (Abs(y - %.4f) < 0.001))" % (_pas(v['net']), v['x'], v['y']) for v in vs]
    return conds


def _trk_match(ts):
    """condition per track: net, layer, and both ends in either order within 1 um"""
    conds = []
    for t in ts:
        lay = LAYER_ENUM[t['layer']]
        conds.append("((nm = '%s') And (T.Layer = %s) And "
                     "(((Abs(x - %.4f) < 0.001) And (Abs(y - %.4f) < 0.001) And (Abs(x2 - %.4f) < 0.001) And (Abs(y2 - %.4f) < 0.001)) Or "
                     "((Abs(x - %.4f) < 0.001) And (Abs(y - %.4f) < 0.001) And (Abs(x2 - %.4f) < 0.001) And (Abs(y2 - %.4f) < 0.001))))"
                     % (_pas(t['net']), lay, t['x1'], t['y1'], t['x2'], t['y2'], t['x2'], t['y2'], t['x1'], t['y1']))
    return conds


def _collect(L, vias, tracks, listvar):
    """emit two iterator passes (typed IPCB_Via, then IPCB_Track) adding matches to listvar"""
    if vias:
        L += ['    It := Brd.BoardIterator_Create;', '    It.AddFilter_ObjectSet(MkSet(eViaObject));',
              '    It.AddFilter_LayerSet(AllLayers);', '    It.AddFilter_Method(eProcessAll);',
              '    V := It.FirstPCBObject;', '    While V <> Nil Do', '    Begin',
              "        nm := ''; If V.Net <> Nil Then nm := V.Net.Name;",
              '        x := CoordToMMs(V.X); y := CoordToMMs(V.Y);']
        for c in _via_match(vias):
            L.append('        If %s Then %s.Add(V);' % (c, listvar))
        L += ['        V := It.NextPCBObject;', '    End;', '    Brd.BoardIterator_Destroy(It);']
    if tracks:
        L += ['    It := Brd.BoardIterator_Create;', '    It.AddFilter_ObjectSet(MkSet(eTrackObject));',
              '    It.AddFilter_LayerSet(AllLayers);', '    It.AddFilter_Method(eProcessAll);',
              '    T := It.FirstPCBObject;', '    While T <> Nil Do', '    Begin',
              "        nm := ''; If T.Net <> Nil Then nm := T.Net.Name;",
              '        x := CoordToMMs(T.X1); y := CoordToMMs(T.Y1); x2 := CoordToMMs(T.X2); y2 := CoordToMMs(T.Y2);']
        for c in _trk_match(tracks):
            L.append('        If %s Then %s.Add(T);' % (c, listvar))
        L += ['        T := It.NextPCBObject;', '    End;', '    Brd.BoardIterator_Destroy(It);']


def _add(L, vias, tracks):
    nets = sorted({v['net'] for v in vias} | {t['net'] for t in tracks})
    for net in nets:
        q = _pas(net)
        L.append("        N := FanNet('%s');" % q)
        L.append("        If N = Nil Then Missing := Missing + ' %s' Else" % q)
        L.append('        Begin')
        for v in vias:
            if v['net'] == net:
                L.append('            FanVia(N, %.4f, %.4f);' % (v['x'], v['y']))
        for t in tracks:
            if t['net'] == net:
                L.append('            FanTrk(N, %s, %.4f, %.4f, %.4f, %.4f, %.4f);' % (
                    LAYER_ENUM[t['layer']], t['width'], t['x1'], t['y1'], t['x2'], t['y2']))
        L.append('        End;')


VARS = ['Var', '    N    : IPCB_Net;', '    V    : IPCB_Via;', '    T    : IPCB_Track;', '    It   : IPCB_BoardIterator;',
        '    Kill : TInterfaceList;', '    i    : Integer;', '    x, y, x2, y2 : Double;', '    nm   : String;', '    Missing : String;']


def emit(plan, name, inp=None):
    """Place<name>: find the plan's removals (refuse unless every one matches exactly once),
    remove them, add the plan's primitives, one transaction.  Remove<name>: delete what was
    added and put the removed copper back."""
    B = '{ ==== %s BLOCK, generated by tools/route_emit.py -- do not edit by hand ==== }' % name.upper()
    E = '{ ==== END %s BLOCK ==== }' % name.upper()
    rem = plan.get('remove') or {}
    rv = rem.get('vias', [])
    rt = rem.get('tracks', [])
    if inp is not None and rt:          # widths of removed tracks, for restoring them
        byk = {_key_t(t): t for t in inp['tracks']}
        rt = [dict(t, width=byk[_key_t(t)]['width']) for t in rt]
    nv, nt = plan.get('vias', []), plan.get('tracks', [])

    L = [B, '', 'Procedure Place%s;' % name] + VARS + ['Begin', '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;',
                                                      "    Missing := '';", '    Kill := TInterfaceList.Create;']
    if rv or rt:
        L.append('    { the existing copper this plan replaces: all of it, or nothing happens }')
        _collect(L, rv, rt, 'Kill')
        L += ['    If Kill.Count <> %d Then' % (len(rv) + len(rt)), '    Begin',
              "        ShowMessage('Zulu A7 - %s: found ' + IntToStr(Kill.Count) + ' of the %d objects it must replace. Nothing changed.');" % (name, len(rv) + len(rt)),
              '        Kill.Free;', '        Exit;', '    End;']
    L += ['    PCBServer.PreProcess;', '    Try', '        For i := 0 To Kill.Count - 1 Do', '            Brd.RemovePCBObject(Kill.Items[i]);']
    _add(L, nv, nt)
    L += ['    Finally', '        PCBServer.PostProcess;', '    End;', '    Kill.Free;', '    Brd.ViewManager_FullUpdate;',
          "    If Missing <> '' Then",
          "        ShowMessage('Zulu A7 - %s placed, but these nets were NOT found:' + Missing + #13#10 + 'Their primitives were skipped. Do not save until this is understood.')" % name,
          '    Else',
          "        ShowMessage('Zulu A7 - %s placed: removed %d, added %d vias and %d tracks.' + #13#10 + 'Now Tools > Design Rule Check > Run, then Ctrl+S if it is clean.');" % (name, len(rv) + len(rt), len(nv), len(nt)),
          'End;', '', '',
          'Procedure Remove%s;' % name] + VARS + ['Begin', '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;',
                                                 "    Missing := '';", '    Kill := TInterfaceList.Create;']
    _collect(L, nv, nt, 'Kill')
    L += ['    PCBServer.PreProcess;', '    Try', '        For i := 0 To Kill.Count - 1 Do', '            Brd.RemovePCBObject(Kill.Items[i]);']
    if rv or rt:
        L.append('        { put back the copper Place%s removed }' % name)
        _add(L, rv, rt)
    L += ['    Finally', '        PCBServer.PostProcess;', '    End;', '    Brd.ViewManager_FullUpdate;',
          "    ShowMessage('Zulu A7 - removed ' + IntToStr(Kill.Count) + ' %s object(s) (expected %d)%s. Press Ctrl+S.');"
          % (name, len(nv) + len(nt), (' and restored %d' % (len(rv) + len(rt))) if (rv or rt) else ''),
          '    Kill.Free;', 'End;', '', E]
    return '\n'.join(L) + '\n', B, E


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    plan_path, name = sys.argv[1], sys.argv[2]
    inp = json.load(io.open(INPUTS, encoding='utf-8'))
    plan = json.load(io.open(plan_path, encoding='utf-8'))
    print('plan: %d vias, %d tracks' % (len(plan.get('vias', [])), len(plan.get('tracks', []))))
    problems = check(inp, plan)
    if problems:
        print('%d PROBLEM(S):' % len(problems))
        for p in problems[:40]:
            print('  ', p)
        if len(problems) > 40:
            print('   ... and %d more' % (len(problems) - 40))
        return 1
    print('geometry and connectivity check: clean')
    comp = completeness(apply_removals(inp, plan)[0], plan)
    before = completeness(inp, {'vias': [], 'tracks': []})
    touched = {v['net'] for v in plan.get('vias', [])} | {t['net'] for t in plan.get('tracks', [])}
    bad_all = sorted(n for n, (ok, _) in comp.items() if not ok)
    # --require-complete (2026-09-15, staged power routing): every net joined on the board
    # before the plan stays joined, and every net the plan touches ends up joined.  Nets the
    # plan leaves alone may stay unjoined -- a later stage owns them.
    regress = sorted(n for n in comp if before[n][0] and not comp[n][0])
    unfinished = sorted(n for n in touched if n in comp and not comp[n][0])
    bad = regress + unfinished
    print('nets joined end to end: %d/%d  (touched by the plan: %d, of them joined: %d)%s%s' % (
        len(comp) - len(bad_all), len(comp), len(touched & set(comp)), len([n for n in touched if n in comp and comp[n][0]]),
        ('  NOT JOINED (touched): ' + ' '.join(unfinished)) if unfinished else '',
        ('  DISJOINED BY THE PLAN: ' + ' '.join(regress)) if regress else ''))
    if plan.get('remove'):
        print('removes %d existing via(s) and %d track(s); every U1 power/GND ball still reaches its via' % (
            len(plan['remove'].get('vias', [])), len(plan['remove'].get('tracks', []))))
    if bad and '--require-complete' in sys.argv:
        print('INCOMPLETE - --require-complete refuses this plan')
        return 1
    if '--write' not in sys.argv:
        return 0
    block, B, E = emit(plan, name, inp)
    s = io.open(SETUP, encoding='utf-8', errors='replace').read()
    tail = "End.\n\n{ End of ZuluSetup.pas }\n"
    assert s.endswith(tail)
    if B in s:
        a = s.index(B)
        b = s.index(E) + len(E) + 1
        s = s[:a] + block + s[b:]
    else:
        s = s[:-len(tail)] + '\n' + block + '\n' + tail
    io.open(SETUP, 'w', encoding='utf-8').write(s)
    print('wrote Place%s / Remove%s into %s' % (name, name, os.path.normpath(SETUP)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
