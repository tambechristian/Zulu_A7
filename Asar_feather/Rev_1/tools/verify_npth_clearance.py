"""Verify the NPTH clearance edit (2026-11-16) on the saved board against the board before it.

    python tools/verify_npth_clearance.py <before.PcbDoc> [after.PcbDoc]

Checks, each from the files alone:
  1. the copper-track difference is exactly the plan: every old segment of tools/route/npth_clearance/plan.json gone,
     every new one present (layer, net, width, end points), and no other track added, removed or changed;
  2. pads, vias and arcs are identical, and the only OLE streams that differ are the expected ones;
  3. the new rule Clearance_NPTH_Track exists with the planned gap and scopes;
  4. every non-plated hole: hole wall to the nearest track / via / arc on every copper layer (floor 0.127 mm);
  5. the five edited nets keep the same number of copper islands that hold a pad (connectivity unchanged).
Exit 0 only when all pass.
"""
import json
import math
import os
import struct
import sys
from collections import Counter

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fab_facts as FF  # noqa: E402

PLAN = os.path.join(HERE, 'route', 'npth_clearance', 'plan.json')
FLOOR = 0.127
EXPECTED_STREAMS = {'Tracks6/Data', 'Tracks6/Header', 'Rules6/Data', 'Rules6/Header'}


def key(layer, net, width, a, b):
    p, q = (round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))
    return (layer, net, round(width, 4)) + tuple(sorted((p, q)))


def tkey(t):
    return key(t['layer'], t['net'], t['width'], (t['x1'], t['y1']), (t['x2'], t['y2']))


def arcs_geom(path):
    f = olefile.OleFileIO(path)
    out = []
    for b in FF.simple_records(f.openstream('Arcs6/Data').read(), 1):
        if b[0] not in FF.COPPER_IDS:
            continue
        out.append(dict(layer=FF.LAYER[b[0]], x=FF.i32(b, 13) * FF.U, y=FF.i32(b, 17) * FF.U, r=FF.i32(b, 21) * FF.U,
                        a0=struct.unpack('<d', b[25:33])[0], a1=struct.unpack('<d', b[33:41])[0],
                        width=FF.i32(b, 41) * FF.U))
    f.close()
    return out


def arc_point_dist(a, px, py):
    """distance from a point to the arc's centre line (exact, with the end points when outside the sweep)"""
    ang = math.degrees(math.atan2(py - a['y'], px - a['x'])) % 360
    a0, a1 = a['a0'] % 360, a['a1'] % 360
    inside = (a0 <= ang <= a1) if a0 <= a1 else (ang >= a0 or ang <= a1)
    if inside:
        return abs(math.hypot(px - a['x'], py - a['y']) - a['r'])
    ends = [(a['x'] + a['r'] * math.cos(math.radians(t)), a['y'] + a['r'] * math.sin(math.radians(t))) for t in (a0, a1)]
    return min(math.hypot(px - x, py - y) for x, y in ends)


def streams(path):
    f = olefile.OleFileIO(path)
    out = {'/'.join(s): f.openstream(s).read() for s in f.listdir()}
    f.close()
    return out


def recs(data):
    out = []
    for r in data.decode('latin-1').split(chr(0)):
        out.append(dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv))
    return [r for r in out if r]


def save_artefact(name, a, b):
    """why a stream that the edit itself does not touch may still differ after an Altium save, or None"""
    if a is None or b is None:
        return None
    if name in ('FileHeaderSix', 'PrimitiveGuids/Data', 'PrimitiveGuids/Header'):
        return 'save id / primitive GUIDs'
    if name == 'Design Rule Checker Options6/Data':
        ra, rb = recs(a), recs(b)
        keys = {k for x, y in zip(ra, rb) for k in set(x) | set(y) if x.get(k) != y.get(k)}
        return 'DRC options %s' % sorted(keys) if keys <= {'REPORTFILENAME'} and len(ra) == len(rb) else None
    if name == 'Board6/Data':
        ra, rb = recs(a), recs(b)
        keys = {k for x, y in zip(ra, rb) for k in set(x) | set(y) if x.get(k) != y.get(k)}
        return 'board %s' % sorted(keys) if keys <= {'DATE', 'TIME'} and len(ra) == len(rb) else None
    if name == 'Nets6/Data':
        na, nb = [r for r in recs(a) if 'NAME' in r], [r for r in recs(b) if 'NAME' in r]
        if [r['NAME'] for r in na] != [r['NAME'] for r in nb]:
            return None
        keys = {k for x, y in zip(na, nb) for k in set(x) | set(y) if x.get(k) != y.get(k)}
        return 'cached net %s' % sorted(keys) if keys <= {'DELAYTOTAL', 'ROUTEDLENGTH'} else None
    if name == 'Texts/Data' and len(a) == len(b):
        # legacy text stream: only the unused tail of the 64-byte TrueType font-name buffer may change
        name16 = 'Arial'.encode('utf-16-le')
        bufs = [(i, i + 64) for i in range(len(b)) if b[i:i + 10] == name16 and a[i:i + 12] == name16 + b'\0\0']
        bad = [i for i in range(len(a)) if a[i] != b[i] and not any(s + 12 <= i < e for s, e in bufs)]
        return 'font-name buffer padding' if not bad else None
    return None


def islands(B, net):
    """copper islands of one net: tracks joined when they touch on a layer, vias join their span, pads their layers"""
    items = []
    for t in B['tracks']:
        if t['net'] == net:
            items.append(('t', t))
    for v in B['vias']:
        if v['net'] == net:
            items.append(('v', v))
    for p in B['pads']:
        if p['net'] == net:
            items.append(('p', p))
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def layers(it):
        k, o = it
        if k == 't':
            return {o['layer']}
        if k == 'v':
            return {L for L in FF.STACK if FF.span_has(o['span'], L)}
        return set(FF.STACK) if o['layer'] == 'Multi' else {o['layer']}

    def touch(A, B_, L):
        (ka, a), (kb, b) = A, B_
        if ka == 't' and kb == 't':
            return FF.seg_seg_dist((a['x1'], a['y1'], a['x2'], a['y2']), (b['x1'], b['y1'], b['x2'], b['y2'])) <= (a['width'] + b['width']) / 2 + 1e-4
        if ka != 't' and kb == 't':
            return touch(B_, A, L)
        if ka == 't':
            if kb == 'v':
                return FF.seg_point_dist(a['x1'], a['y1'], a['x2'], a['y2'], b['x'], b['y']) <= (a['width'] + b['size']) / 2 + 1e-4
            return FF.seg_pad_dist(dict(a), FF.pad_view(b, L)) <= a['width'] / 2 + 1e-4
        # via / pad pairs: centre distance against the sum of radii (pads by their reach)
        ra = a['size'] / 2 if ka == 'v' else 0.0
        rb = b['size'] / 2 if kb == 'v' else 0.0
        if ka == 'p':
            return FF.pad_point_dist(FF.pad_view(a, L), b['x'], b['y']) <= rb + 1e-4
        if kb == 'p':
            return FF.pad_point_dist(FF.pad_view(b, L), a['x'], a['y']) <= ra + 1e-4
        return math.hypot(a['x'] - b['x'], a['y'] - b['y']) <= ra + rb + 1e-4

    lay = [layers(it) for it in items]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            common = lay[i] & lay[j]
            if not common or find(i) == find(j):
                continue
            if any(touch(items[i], items[j], L) for L in common):
                parent[find(i)] = find(j)
    groups = Counter(find(i) for i, it in enumerate(items) if it[0] == 'p')
    return len(groups), len(items)


def main():
    before_path = sys.argv[1]
    after_path = sys.argv[2] if len(sys.argv) > 2 else FF.PCB
    plan = json.load(open(PLAN))
    A, B = FF.read_board(before_path), FF.read_board(after_path)
    ok = True

    # 1. track difference
    old = Counter(key(e['layer'], e['net'], e['width'], a, b) for e in plan['edits'] for a, b in zip(e['old'], e['old'][1:]) if a != b)
    new = Counter(key(e['layer'], e['net'], e['width'], a, b) for e in plan['edits'] for a, b in zip(e['new'], e['new'][1:]) if a != b)
    ca, cb = Counter(tkey(t) for t in A['tracks']), Counter(tkey(t) for t in B['tracks'])
    removed, added = ca - cb, cb - ca
    t1 = removed == old and added == new
    ok &= t1
    print('1. tracks: before %d, after %d; removed %d (plan %d), added %d (plan %d) -> %s' % (
        len(A['tracks']), len(B['tracks']), sum(removed.values()), sum(old.values()), sum(added.values()), sum(new.values()),
        'PASS' if t1 else 'FAIL'))
    if not t1:
        for k in (removed - old):
            print('   unexpected removal', k)
        for k in (old - removed):
            print('   planned removal missing', k)
        for k in (added - new):
            print('   unexpected addition', k)
        for k in (new - added):
            print('   planned addition missing', k)

    # 2. other objects and streams
    same = A['pads'] == B['pads'] and A['vias'] == B['vias']
    aa, ab = arcs_geom(before_path), arcs_geom(after_path)
    same &= aa == ab
    sa, sb = streams(before_path), streams(after_path)
    diff = sorted(k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k))
    benign = {k: why for k, why in ((k, save_artefact(k, sa.get(k), sb.get(k))) for k in diff) if why}
    unexpected = [k for k in diff if k not in EXPECTED_STREAMS and k not in benign]
    t2 = same and not unexpected
    ok &= t2
    print('2. pads %d / vias %d / arcs %d identical: %s; edit streams changed %s; save artefacts %s; unexpected %s -> %s' % (
        len(B['pads']), len(B['vias']), len(ab), same, [k for k in diff if k in EXPECTED_STREAMS], benign, unexpected,
        'PASS' if t2 else 'FAIL'))

    # 3. rule
    r = [kv for kv in B['rules'] if kv.get('NAME') == 'Clearance_NPTH_Track']
    t3 = len(r) == 1 and r[0].get('RULEKIND') == 'Clearance' and abs(float(r[0].get('GAP', '0mil').rstrip('mil')) * 0.0254 - 0.127) < 1e-3
    ok &= t3
    print('3. rule Clearance_NPTH_Track: %s -> %s' % (
        {k: r[0].get(k) for k in ('RULEKIND', 'GAP', 'SCOPE1EXPRESSION', 'SCOPE2EXPRESSION', 'NETSCOPE', 'LAYERKIND', 'PRIORITY', 'ENABLED')} if r else None,
        'PASS' if t3 else 'FAIL'))

    # 4. NPTH wall to copper
    t4 = True
    npth = [p for p in B['pads'] if p['hole'] > 0 and p['net'] is None]
    for h in npth:
        rad = h['hole'] / 2
        best = []
        for t in B['tracks']:
            g = FF.seg_point_dist(t['x1'], t['y1'], t['x2'], t['y2'], h['x'], h['y']) - t['width'] / 2 - rad
            best.append((g, 'track %s %s' % (t['layer'], t['net'])))
        for v in B['vias']:
            best.append((math.hypot(v['x'] - h['x'], v['y'] - h['y']) - v['size'] / 2 - rad, 'via %s %s-%s' % (v['net'], *v['span'])))
        for a in ab:
            best.append((arc_point_dist(a, h['x'], h['y']) - a['width'] / 2 - rad, 'arc %s' % a['layer']))
        best.sort()
        g, who = best[0]
        if g < FLOOR - 1e-4:
            t4 = False
        print('4. NPTH %s (%.4f, %.4f) d %.3f: nearest %.4f (%s)%s' % (h['ref'], h['x'], h['y'], h['hole'], g, who,
                                                                       '' if g >= FLOOR - 1e-4 else '  << below 0.127'))
    ok &= t4
    print('   -> %s' % ('PASS' if t4 else 'FAIL'))

    # 5. connectivity of the edited nets
    t5 = True
    for net in sorted({e['net'] for e in plan['edits']}):
        ib, nb = islands(A, net)
        ia, na = islands(B, net)
        t5 &= ia == ib
        print('5. %-9s pad islands before %d, after %d (objects %d -> %d)' % (net, ib, ia, nb, na))
    ok &= t5
    print('   -> %s' % ('PASS' if t5 else 'FAIL'))
    print('ALL PASS' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
