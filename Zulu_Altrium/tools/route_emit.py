# -*- coding: utf-8 -*-
"""Check a routing plan against the board as saved and turn it into DelphiScript.

    python tools/route_emit.py <plan.json> <BlockName>            check only
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
    """distance from a segment to an axis-aligned rectangle (0 if it crosses)"""
    x1, y1, x2, y2 = seg
    n = 24
    return min(pt_rect(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n, cx, cy, sx, sy) for k in range(n + 1))


def clearance_for(net, layer, inp):
    if layer in ('L3-SIG', 'L4-SIG') and net in inp['nets']:
        return inp['nets'][net]['clearance']['inner']
    return 0.09


def width_ok(net, layer, w, inp):
    r = inp['nets'].get(net)
    if r is None:
        return w >= 0.0762 - EPS
    wr = r['width']
    if layer == 'Top':
        return wr['top_min'] - EPS <= w <= 0.15 + EPS
    return wr['inner_min'] - EPS <= w <= wr['inner_max'] + EPS


def check(inp, plan):
    problems = []
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
                if p['net'] == v['net']:
                    continue
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


def emit(plan, name):
    B = '{ ==== %s BLOCK, generated by tools/route_emit.py -- do not edit by hand ==== }' % name.upper()
    E = '{ ==== END %s BLOCK ==== }' % name.upper()
    L = [B, '', 'Procedure Place%s;' % name, 'Var', '    N : IPCB_Net;', '    Missing : String;', 'Begin',
         '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;', "    Missing := '';", '    PCBServer.PreProcess;', '    Try']
    nets = sorted({v['net'] for v in plan['vias']} | {t['net'] for t in plan['tracks']})
    for net in nets:
        q = net.replace("'", "''")
        L.append("        N := FanNet('%s');" % q)
        L.append("        If N = Nil Then Missing := Missing + ' %s' Else" % q)
        L.append('        Begin')
        for v in plan['vias']:
            if v['net'] == net:
                L.append('            FanVia(N, %.4f, %.4f);' % (v['x'], v['y']))
        for t in plan['tracks']:
            if t['net'] == net:
                L.append('            FanTrk(N, %s, %.4f, %.4f, %.4f, %.4f, %.4f);' % (
                    LAYER_ENUM[t['layer']], t['width'], t['x1'], t['y1'], t['x2'], t['y2']))
        L.append('        End;')
    L += ['    Finally', '        PCBServer.PostProcess;', '    End;', '    Brd.ViewManager_FullUpdate;',
          "    If Missing <> '' Then",
          "        ShowMessage('Zulu A7 - %s placed, but these nets were NOT found:' + Missing + #13#10 + 'Their primitives were skipped. Do not save until this is understood.')" % name,
          '    Else',
          "        ShowMessage('Zulu A7 - %s placed: %d vias, %d tracks.' + #13#10 + 'Now Tools > Design Rule Check > Run, then Ctrl+S if it is clean.');" % (name, len(plan['vias']), len(plan['tracks'])),
          'End;', '', '',
          'Procedure Remove%s;' % name, 'Var', '    It   : IPCB_BoardIterator;', '    P    : IPCB_Primitive;',
          '    Kill : TInterfaceList;', '    i    : Integer;', '    x, y, x2, y2 : Double;', 'Begin',
          '    Brd := BoardOrNil;', '    If Brd = Nil Then Exit;', '    Kill := TInterfaceList.Create;',
          '    It := Brd.BoardIterator_Create;', '    It.AddFilter_ObjectSet(MkSet(eViaObject, eTrackObject));',
          '    It.AddFilter_LayerSet(AllLayers);', '    It.AddFilter_Method(eProcessAll);', '    P := It.FirstPCBObject;',
          '    While P <> Nil Do', '    Begin']
    # match by coordinates: vias by (x,y), tracks by (x1,y1,x2,y2) within 1 um
    L.append('        If P.ObjectId = eViaObject Then')
    L.append('        Begin')
    L.append('            x := CoordToMMs(P.X); y := CoordToMMs(P.Y);')
    conds = ['((Abs(x - %.4f) < 0.001) And (Abs(y - %.4f) < 0.001))' % (v['x'], v['y']) for v in plan['vias']]
    for k in range(0, len(conds), 1):
        L.append('            If %s Then Kill.Add(P);' % conds[k])
    L.append('        End')
    L.append('        Else If P.ObjectId = eTrackObject Then')
    L.append('        Begin')
    L.append('            x := CoordToMMs(P.X1); y := CoordToMMs(P.Y1); x2 := CoordToMMs(P.X2); y2 := CoordToMMs(P.Y2);')
    for t in plan['tracks']:
        L.append('            If (Abs(x - %.4f) < 0.001) And (Abs(y - %.4f) < 0.001) And (Abs(x2 - %.4f) < 0.001) And (Abs(y2 - %.4f) < 0.001) Then Kill.Add(P);'
                 % (t['x1'], t['y1'], t['x2'], t['y2']))
    L += ['        End;', '        P := It.NextPCBObject;', '    End;', '    Brd.BoardIterator_Destroy(It);',
          '    PCBServer.PreProcess;', '    Try', '        For i := 0 To Kill.Count - 1 Do', '            Brd.RemovePCBObject(Kill.Items[i]);',
          '    Finally', '        PCBServer.PostProcess;', '    End;', '    Brd.ViewManager_FullUpdate;',
          "    ShowMessage('Zulu A7 - removed ' + IntToStr(Kill.Count) + ' %s object(s) (expected %d). Press Ctrl+S.');" % (name, len(plan['vias']) + len(plan['tracks'])),
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
    if '--write' not in sys.argv:
        return 0
    block, B, E = emit(plan, name)
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
