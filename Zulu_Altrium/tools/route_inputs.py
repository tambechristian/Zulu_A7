# -*- coding: utf-8 -*-
"""Everything the SDRAM-bus routing needs, read from the PcbDoc AS SAVED (so the
placed fan-out is part of the geometry), written to tools/route_inputs.json.

    python tools/route_inputs.py

WHAT IT WRITES
  nets        the 39 SDRAM nets: for each, its U3 pad(s) on Bottom and its U1
              end as the fan-out left it -- a moat via (ring 2), a Top stub
              whose free end sits 0.10 mm outside the land field (ring 1), or
              the ball itself (ring 0, nothing placed) -- plus the net's class
              and its rule set (width, clearance on L3/L4)
  vias        every via on the board (377): span (layer names in stack order, Top first), x, y,
              size, hole, net -- the via span parameters themselves stay in tools/hdi.json (tools/hdi.py
              reads it; nothing is copied here, so an edit to hdi.json is in force at once)
  tracks      every track on Top / L3-SIG / L4-SIG / Bottom: net, layer, ends, width
  th_pads     every through-hole pad (copper on every layer): x, y, size, net
  bottom_pads every Bottom SMD pad inside the region (obstacles for Bottom stubs)
  top_pads    every Top SMD pad inside the region
  region      the routing window
  u3          body and pad-row geometry
  rules       the values that bind: SDRAM width table, clearances, via, holes

Pad rotation is the double at byte 52 of the pad body; a 90/270 pad swaps its
size axes on the board.  Via records: layer@0, net int16@3, x@13, y@17,
size@21, hole@25, start layer id@29, end layer id@30.  Track records: layer@0, net@3, x1@13 y1@17 x2@21 y2@25
width@29.  Coordinates in mm on the board origin, y up.
"""
import io
import json
import os
import struct

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
FAN = os.path.join(HERE, 'fanout_plan.json')
OUT = os.path.join(HERE, 'route_inputs.json')
U = 2.54e-6
LAYER = {1: 'Top', 2: 'L3-SIG', 3: 'L4-SIG', 32: 'Bottom', 74: 'Multi', 39: 'L2-GND', 40: 'L5-VCC3V3'}
# 2026-09-29 (HDI): the Board6 layer chain LAYER1NEXT=39 -> 2 -> 3 -> 40 -> 32, i.e. the order a via's
# start/end layer bytes (body [29] and [30], the same numeric ids as above) are sorted by.  A via's
# span is STACK[idx(low) : idx(high) + 1]; every via on the board today reads (1, 32) = through.
STACK = ['Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom']
PLANE_IDS = (39, 40)                 # never a track or fill layer: excluded explicitly below
HDI = os.path.join(HERE, 'hdi.json')
# The whole board.  2026-09-15: this was x 14..45, y 3.5..21, which silently dropped U1's
# lands east of x 45 and U4's east pads -- the checker could not see them, and a router
# (astar) had to synthesise them itself.  Nothing is clipped now.
REGION = dict(x0=0.0, x1=69.85, y0=0.0, y1=25.40)

DATA = ['D%d' % k for k in range(16)]
ADDR = ['A%d' % k for k in range(13)] + ['BS0', 'BS1']
CTRL = ['CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK']
CLS = {n: 'SDRAM_DATA' for n in DATA}
CLS.update({n: 'SDRAM_ADDR' for n in ADDR})
CLS.update({n: 'SDRAM_CTRL' for n in CTRL})
# 2026-09-15: nets co-routed with the bus because routing the bus alone forecloses
# them (tools/route_foreclosure.py).  Global Width / Clearance rules apply to them.
XADC = ['AIN15_N', 'AIN15_P', 'AIN16_N', 'AIN16_P']
CLS.update({n: 'XADC' for n in XADC})
# 2026-09-15: the power feeds.  Every pad of these nets must end up in one component;
# they have no single U1 'end'.  GND/GNDADC are NOT here: they join through vias to the
# L2/L5 planes, and the pad audit keeps every GND pad a via slot.
POWER = ['VU', 'USB5V0', 'VBATT', 'NetL1_1', 'NetL2_1', 'NetL3_1', 'VCC3V3', 'VCC1V8',
         'VCC1V0', 'VCCADC', 'GNDADC', 'FT-VCORE', 'FT-VPHY', 'FT-VPLL']   # GNDADC is VCCADC's
         # own return, not the plane: it is routed copper like any other net (added 2026-09-16)
CLS.update({n: 'POWER' for n in POWER})
# the charger's status LEDs and its programming resistors: small nets, but they share the block's
# corridors, and a net missing from here is invisible to route_emit's completeness walk and to its
# width check (2026-09-16: the five LED nets were routed in stage 1 while the gate could not see them)
CHARGER = ['NetLD3_A', 'NetLD3_K', 'NetLD4_A', 'NetLD4_K', 'LD5_K',
           'NetR102_2', 'NetR103_2', 'NetR104_2', 'NetR105_2', 'NetR106_2']
CLS.update({n: 'CHARGER' for n in CHARGER})
OUTLINE = dict(x0=0.0, y0=0.0, x1=69.85, y1=25.40)     # Board6 VX/VY: 2750 x 1000 mil
EDGE_CLEARANCE = 0.25                                  # JLC: copper >= 0.2 mm from routed edges
WLAYER = {'Top': 'TOPLAYER', 'L3-SIG': 'MIDLAYER1', 'L4-SIG': 'MIDLAYER2', 'Bottom': 'BOTTOMLAYER'}


def mil(v):
    v = (v or '').strip()
    if v.endswith('mil'):
        return float(v[:-3]) * 0.0254
    if v.endswith('mm'):
        return float(v[:-2])
    return float(v) * 0.0254 if v else None


def scope_matches(expr, net, classes):
    """'All', or InNet('x') / InNetClass('c') terms joined by ' Or '.  Anything else raises,
    so an unfamiliar scope is noticed instead of silently matching nothing."""
    import re
    expr = (expr or '').strip()
    if expr == 'All':
        return True
    terms = [t.strip() for t in expr.split(' Or ')]
    hit = False
    for term in terms:
        m = re.fullmatch(r"InNet\('([^']*)'\)", term)
        if m:
            hit = hit or m.group(1) == net
            continue
        m = re.fullmatch(r"InNetClass\('([^']*)'\)", term)
        if m:
            hit = hit or net in classes.get(m.group(1), ())
            continue
        raise ValueError('unparsed Width scope term %r in %r' % (term, expr))
    return hit


def width_table(net, width_rules, classes):
    """the per-layer min/pref/max DRC applies to this net: highest-priority matching Width rule,
    per-layer keys resolved as override-else-default (the file's sparse-delta form)"""
    rs = sorted(width_rules, key=lambda kv: int(kv.get('PRIORITY', 99)))
    for kv in rs:
        if kv.get('ENABLED') == 'TRUE' and scope_matches(kv.get('SCOPE1EXPRESSION'), net, classes):
            out = dict(rule=kv['NAME'])
            for L, pre in WLAYER.items():
                key = {'Top': 'top', 'L3-SIG': 'inner', 'L4-SIG': 'inner4', 'Bottom': 'bottom'}[L]
                out[key + '_min'] = round(mil(kv.get(pre + '_MINWIDTH', kv.get('MINLIMIT'))), 4)
                out[key + '_pref'] = round(mil(kv.get(pre + '_PREFWIDTH', kv.get('PREFEREDWIDTH'))), 4)
                out[key + '_max'] = round(mil(kv.get(pre + '_MAXWIDTH', kv.get('MAXLIMIT'))), 4)
            assert (out['inner_min'], out['inner_max']) == (out['inner4_min'], out['inner4_max']), net
            return out
    raise KeyError('no Width rule matches ' + net)


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    out = {}
    for i, r in enumerate(x for x in d.split(chr(0)) if key in x):
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        out[i] = kv
    return out


def main():
    f = olefile.OleFileIO(PCB)
    nets = {i: kv.get('NAME') for i, kv in kvs(f, 'Nets6/Data', 'NAME=').items()}
    comps = {i: kv for i, kv in kvs(f, 'Components6/Data', 'SOURCEDESIGNATOR=').items()}

    # ---- pads ---------------------------------------------------------------
    d = f.openstream('Pads6/Data').read()
    pads = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        if t != 2:
            break
        name = d[i + 6:i + 6 + d[i + 5]].decode('latin-1')
        i += 5 + ln
        for k in range(3):
            l2 = struct.unpack('<I', d[i:i + 4])[0]
            i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        b = d[i + 4:i + 4 + l2]
        i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        i += 4 + l2
        if len(b) < 60:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        comp = struct.unpack('<h', b[7:9])[0]
        x = struct.unpack('<i', b[13:17])[0] * U
        y = struct.unpack('<i', b[17:21])[0] * U
        sx = struct.unpack('<i', b[21:25])[0] * U
        sy = struct.unpack('<i', b[25:29])[0] * U
        hole = struct.unpack('<i', b[45:49])[0] * U
        rot = struct.unpack('<d', b[52:60])[0]
        if round(rot) % 180 == 90:
            sx, sy = sy, sx
        # Pads6 shape bytes top/mid/bottom (1 round, 2 rect, 3 octagon).  A pad is modelled round only when
        # all three say round; every other pad keeps the rectangle (an octagon lies inside it: conservative).
        # Round -> corner radius cr = min(sx, sy) / 2 (a circle, or an obround when sx != sy).  2026-09-30:
        # until then every pad was a rectangle, which put U1's 0.225 mm round lands' corners 0.047 mm too close
        # to every diagonal neighbour and killed every interstitial via site under U1.
        round_pad = b[49] == 1 and b[50] == 1 and b[51] == 1
        cr = min(sx, sy) / 2 if round_pad else 0.0
        c = comps.get(comp, {})
        pads.append(dict(ref=c.get('SOURCEDESIGNATOR'), pad=name, layer=LAYER.get(b[0], str(b[0])),
                         x=round(x, 4), y=round(y, 4), sx=round(sx, 4), sy=round(sy, 4),
                         hole=round(hole, 4), rot=rot, net=nets.get(net) if net >= 0 else None,
                         shape='round' if round_pad else 'rect', cr=round(cr, 4)))

    # ---- vias ---------------------------------------------------------------
    d = f.openstream('Vias6/Data').read()
    vias = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if t != 3:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        lo, hi = b[29], b[30]                # start / end layer ids (1 = Top, 32 = Bottom on every via today)
        assert lo in LAYER and hi in LAYER and lo != 74 and hi != 74, ('via layer bytes', lo, hi)
        i0, i1 = sorted((STACK.index(LAYER[lo]), STACK.index(LAYER[hi])))
        vias.append(dict(span=STACK[i0:i1 + 1],
                         x=round(struct.unpack('<i', b[13:17])[0] * U, 4), y=round(struct.unpack('<i', b[17:21])[0] * U, 4),
                         size=round(struct.unpack('<i', b[21:25])[0] * U, 4), hole=round(struct.unpack('<i', b[25:29])[0] * U, 4),
                         net=nets.get(net) if net >= 0 else None))

    # ---- tracks -------------------------------------------------------------
    d = f.openstream('Tracks6/Data').read()
    tracks = []
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if t != 4 or b[0] not in LAYER or b[0] == 74 or b[0] in PLANE_IDS:
            continue
        net = struct.unpack('<h', b[3:5])[0]
        tracks.append(dict(layer=LAYER[b[0]], net=nets.get(net) if net >= 0 else None,
                           x1=round(struct.unpack('<i', b[13:17])[0] * U, 4), y1=round(struct.unpack('<i', b[17:21])[0] * U, 4),
                           x2=round(struct.unpack('<i', b[21:25])[0] * U, 4), y2=round(struct.unpack('<i', b[25:29])[0] * U, 4),
                           width=round(struct.unpack('<i', b[29:33])[0] * U, 4)))
    classes = {}
    for kv in kvs(f, 'Classes6/Data', 'NAME=').values():
        if kv.get('KIND') == '0':
            classes[kv['NAME']] = [v for k, v in kv.items() if k[:1] == 'M' and k[1:].isdigit()]
    width_rules = [kv for kv in kvs(f, 'Rules6/Data', 'RULEKIND=').values() if kv.get('RULEKIND') == 'Width']
    keepouts = []
    fd = f.openstream('Fills6/Data').read()
    j = 0
    while j + 5 <= len(fd):
        ln = struct.unpack('<I', fd[j + 1:j + 5])[0]
        b = fd[j + 5:j + 5 + ln]
        j += 5 + ln
        if b and b[0] in LAYER and b[0] != 74 and b[0] not in PLANE_IDS:
            xs = sorted((struct.unpack('<i', b[13:17])[0] * U, struct.unpack('<i', b[21:25])[0] * U))
            ys = sorted((struct.unpack('<i', b[17:21])[0] * U, struct.unpack('<i', b[25:29])[0] * U))
            keepouts.append(dict(layer=LAYER[b[0]], x0=round(xs[0], 4), x1=round(xs[1], 4), y0=round(ys[0], 4), y1=round(ys[1], 4),
                                 keepout=bool(b[1] & 0x08) or (b[1:3] == bytes.fromhex('0c02'))))
    rules = {}
    for kv in kvs(f, 'Rules6/Data', 'RULEKIND=').values():
        # EVERY Width rule is kept, not just Width and Width_SDRAM.  Until 2026-09-29 the power Width
        # rules were left out, so route_emit.width_ok() -- which falls back to the global 0.0762 for
        # any net that is not one of the 67 modelled ones -- could not see them.  NODE_P0 and NODE_P1
        # are in the PWR_SWITCH class (Width_PWR_SWITCH, 0.2 mm minimum) but are not modelled nets, so
        # a stage-8 plan routed NODE_P1 at 0.0762 and route_emit passed it; Altium's DRC then reported
        # 11 Width Constraint violations on copper that was already saved.
        if kv.get('RULEKIND') == 'Width' or kv.get('NAME') in (
                'Clearance', 'Clearance_SDRAM_INNER', 'Clearance_SDRAM_CLK', 'RoutingVias',
                'HoleToHoleClearance', 'PlaneClearance'):
            rules[kv['NAME']] = {k: v for k, v in kv.items() if k not in (
                'SELECTION', 'LAYER', 'LOCKED', 'POLYGONOUTLINE', 'USERROUTED', 'KEEPOUT', 'UNIONINDEX', 'UNIQUEID',
                'DEFINEDBYLOGICALDOCUMENT', 'COMMENT')}
    f.close()

    fan = json.load(io.open(FAN, encoding='utf-8'))
    ball_action = {b['name']: b for b in fan['balls']}
    u1 = [p for p in pads if p['ref'] == 'U1']
    ball_by_net = {}
    for p in u1:
        if p['net']:
            ball_by_net.setdefault(p['net'], []).append(p)
    lf = dict(x0=min(p['x'] for p in u1) - 0.1125, x1=max(p['x'] for p in u1) + 0.1125,
              y0=min(p['y'] for p in u1) - 0.1125, y1=max(p['y'] for p in u1) + 0.1125)

    def inside(x, y):
        return lf['x0'] <= x <= lf['x1'] and lf['y0'] <= y <= lf['y1']

    out_nets = {}
    for n in DATA + ADDR + CTRL + XADC + POWER + CHARGER:
        u3p = [dict(pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy']) for p in pads if p['ref'] == 'U3' and p['net'] == n]
        # every non-U1 pad of the net, with its layer: what the route must join
        dest = [dict(ref=p['ref'], pad=p['pad'], layer=p['layer'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'])
                for p in pads if p['net'] == n]      # U1 balls included: every pad must join
        ends = []
        for b in ([] if CLS[n] in ('POWER', 'CHARGER') else ball_by_net.get(n, [])):
            act = ball_action.get(b['pad'], {}).get('action')
            e = dict(ball=b['pad'], ring=ball_action.get(b['pad'], {}).get('ring'), action=act, ball_x=b['x'], ball_y=b['y'])
            if act == 'dogbone-in' or act == 'dogbone-out':
                v = [w for w in vias if w['net'] == n and abs(w['x'] - b['x']) <= 1.6 and abs(w['y'] - b['y']) <= 1.6]
                e.update(kind='via', span=v[0]['span'], x=v[0]['x'], y=v[0]['y']) if v else e.update(kind='via-missing')
            elif act == 'gap':
                # the fan-out stub's free end, taken from tools/fanout_plan.json -- NOT from the board's
                # tracks, where later routing adds Top copper of the same net outside the land field
                # (2026-09-15: AIN16_N's filter hop was picked up as its 'stub end')
                seg = [t for t in fan['tracks'] if t['net'] == n and t['layer'] == 'Top' and
                       (not inside(t['x1'], t['y1']) or not inside(t['x2'], t['y2']))]
                if seg:
                    t = seg[0]
                    fx, fy = (t['x1'], t['y1']) if not inside(t['x1'], t['y1']) else (t['x2'], t['y2'])
                    e.update(kind='stub-end', x=fx, y=fy, layer='Top')
                else:
                    e.update(kind='stub-missing')
            elif act == 'direct':
                e.update(kind='ball', x=b['x'], y=b['y'], layer='Top')
            else:
                e.update(kind=act or 'unknown')
            ends.append(e)
        cls = CLS[n]
        width = width_table(n, width_rules, classes)
        if cls.startswith('SDRAM'):
            old = dict(top_min=0.0762, top_pref=0.0762, top_max=0.15, inner_min=0.10, inner_pref=0.125, inner_max=0.15, bottom_min=0.10, bottom_pref=0.125, bottom_max=0.15)
            assert all(abs(width[k] - v) < 1e-3 for k, v in old.items()), (n, width)
            clearance = dict(top=0.09, bottom=0.09, inner=0.20 if n == 'SDRAM-CLK' else 0.10)
        else:
            clearance = dict(top=0.09, bottom=0.09, inner=0.09)
        out_nets[n] = dict(cls=cls, u3=u3p, pads=dest, u1=ends, width=width, clearance=clearance)

    inreg = lambda p: REGION['x0'] <= p['x'] <= REGION['x1'] and REGION['y0'] <= p['y'] <= REGION['y1']
    u3pads = [p for p in pads if p['ref'] == 'U3']
    out = dict(
        source=os.path.normpath(PCB), region=REGION, land_field=lf,
        nets=out_nets,
        vias=vias,
        tracks=[t for t in tracks],
        th_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], hole=p['hole'], net=p['net'],
                      shape=p['shape'], cr=p['cr'])
                 for p in pads if p['layer'] == 'Multi' and inreg(p)],
        bottom_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], net=p['net'],
                          shape=p['shape'], cr=p['cr'])
                     for p in pads if p['layer'] == 'Bottom' and inreg(p)],
        top_pads=[dict(ref=p['ref'], pad=p['pad'], x=p['x'], y=p['y'], sx=p['sx'], sy=p['sy'], net=p['net'],
                       shape=p['shape'], cr=p['cr'])
                  for p in pads if p['layer'] == 'Top' and inreg(p)],
        u3=dict(rows_y=sorted(set(round(p['y'], 3) for p in u3pads)), x_min=min(p['x'] for p in u3pads), x_max=max(p['x'] for p in u3pads),
                pad_sx=u3pads[0]['sx'], pad_sy=u3pads[0]['sy'], east_copper=max(p['x'] + p['sx'] / 2 for p in u3pads),
                pocket=dict(y0=max(p['y'] + p['sy'] / 2 for p in u3pads if p['y'] < 10), y1=min(p['y'] - p['sy'] / 2 for p in u3pads if p['y'] > 10))),
        rules=rules,
        outline=OUTLINE, edge_clearance=EDGE_CLEARANCE,
        keepouts=[k for k in keepouts if k['keepout']],
        classes=classes,
    )
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, indent=1))
    kinds = {}
    for n, v in out_nets.items():
        for e in v['u1']:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print('nets %d; U1 ends by kind: %s' % (len(out_nets), kinds))
    print('vias %d, tracks %d (%s), th pads in region %d, bottom pads %d, top pads %d' % (
        len(vias), len(tracks), {L: sum(1 for t in tracks if t['layer'] == L) for L in ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')},
        len(out['th_pads']), len(out['bottom_pads']), len(out['top_pads'])))
    # the spans the board actually has, against the model in tools/hdi.json (a span the model does
    # not list is written all the same -- the board is the truth -- but every gate will refuse it)
    listed = {tuple(s['span']) for s in json.load(io.open(HDI, encoding='utf-8'))['spans']}
    listed |= {s[::-1] for s in listed}
    by_span = {}
    for v in vias:
        by_span['/'.join(v['span'])] = by_span.get('/'.join(v['span']), 0) + 1
    unlisted = sorted(k for k in by_span if tuple(k.split('/')) not in listed)
    print('via spans: %s%s' % (by_span, ('; NOT LISTED in tools/hdi.json: %s' % ', '.join(unlisted)) if unlisted else ''))
    print('U3: pad rows y %s, x %.4f..%.4f, pad %.3f x %.3f, east copper %.4f, pocket y %.4f..%.4f' % (
        out['u3']['rows_y'], out['u3']['x_min'], out['u3']['x_max'], out['u3']['pad_sx'], out['u3']['pad_sy'], out['u3']['east_copper'],
        out['u3']['pocket']['y0'], out['u3']['pocket']['y1']))
    missing = [(n, e['ball'], e['kind']) for n, v in out_nets.items() for e in v['u1'] if 'missing' in e['kind'] or e['kind'] == 'unknown']
    print('unresolved U1 ends:', missing)
    print('power nets: %s' % ', '.join('%s(%d pads, %s)' % (n, len(out_nets[n]['pads']), out_nets[n]['width']['rule']) for n in POWER))
    print('keep-outs on signal layers: %d; outline %s, edge clearance %.2f' % (len(out['keepouts']), OUTLINE, EDGE_CLEARANCE))
    print('wrote', os.path.normpath(OUT))


if __name__ == '__main__':
    main()
