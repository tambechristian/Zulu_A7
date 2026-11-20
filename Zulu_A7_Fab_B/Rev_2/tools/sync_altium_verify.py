# -*- coding: utf-8 -*-
"""Verify the SAVED Fab B Rev 2 board against the no-PMOD sync (2026-11-20).  Read-only; olefile only.

    python tools/sync_altium_verify.py [--pcb PcbDoc] [--stage place|rules|bodies|all]

Altium script messages are not proof (a pad net, a designator move and a rule priority have each failed silently on
this project), so after every save in docs/sync_altium_steps.md this re-reads the PcbDoc and compares it with
tools/route/sync_altium/sync_data.json (the no-PMOD board at 427960e) and tools/route/sync_altium/bodies.json:

  place   U2 X4 U10 R119-R134 U4 R34 C87 C88 C94 C99 C106 R1: footprint, side, rotation, origin (0.001 mm), every pad
          position (0.001 mm) and net; NAMEON / COMMENTON and the designator position (0.005 mm) of those parts and U1;
          U3's 16 DQ pads on SDRAM-D0..D15; the outline still 69.85 x 25.40 mm. SOURCELIBREFERENCE /
          FOOTPRINTDESCRIPTION that differ from the no-PMOD board are WARN (the ECO's design-item changes set them).
  rules   ComponentClearance_X2 / _R131R132 and SolderMaskExpansion_U2 with the no-PMOD scope, gap, vertical gap,
          expansion, collision mode and PRIORITY; the no-PMOD priorities of ComponentClearance and the other
          SolderMaskExpansion rules; the six Schematic Supply Nets voltages; SDRAM_DATA = the no-PMOD 32 nets.
  bodies  every part in bodies.json carries exactly its bodies (X2 4, others 1), on Mechanical 13, projected to
          the right side, outline box within 0.02 mm and OVERALLHEIGHT within 0.001 mm of bodies.json; no other body.
Exit 1 on any FAIL.
"""
import argparse
import json
import os
import struct
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sync_altium_read as R  # noqa: E402
import sync_altium_emit as E  # noqa: E402

BODIES = os.path.join(HERE, 'route', 'sync_altium', 'bodies.json')


def body_boxes(path, comps):
    """{ref: [(x0, y0, x1, y1, height, layer, projection), ...]} from ComponentBodies6."""
    import olefile
    f = olefile.OleFileIO(path)
    out = defaultdict(list)
    if f.exists('ComponentBodies6/Data'):
        for t, subs in R.records(f.openstream('ComponentBodies6/Data').read()):
            b = subs[0]
            ci = R.u16(b, 7)
            pl = struct.unpack('<I', b[18:22])[0]
            props = R.kvparse(b[22:22 + pl].decode('latin-1', 'replace').rstrip(chr(0)))
            j = 22 + pl
            n = struct.unpack('<I', b[j:j + 4])[0]
            j += 4
            pts = [(R.dbl(b, j + 16 * k) * R.U, R.dbl(b, j + 16 * k + 8) * R.U) for k in range(n)]
            ref = comps[ci]['ref'] if ci < len(comps) else None
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            out[ref].append((min(xs), min(ys), max(xs), max(ys),
                             R.mil(props['OVERALLHEIGHT']) if 'OVERALLHEIGHT' in props else None,
                             props.get('V7_LAYER'), props.get('BODYPROJECTION')))
    f.close()
    return out


def check_place(B, D, fail, warn):
    comps = {c['ref']: c for c in B['comps']}
    pads = defaultdict(dict)
    for p in B['pads']:
        pads[p['ref']][p['pad']] = p
    texts = {t['comp']: t for t in B['texts'] if t['designator'] and t['comp']}
    for ref, e in sorted(D['parts'].items()):
        s, c = e['src'], comps.get(ref)
        if c is None:
            fail('%s is not on the board' % ref)
            continue
        if e['group'] != 'desig':
            if (c['pattern'], c['side']) != (s['pattern'], s['side']):
                fail('%s is %s/%s, no-PMOD %s/%s' % (ref, c['pattern'], c['side'], s['pattern'], s['side']))
            d = abs((c['rot'] - s['rot'] + 180) % 360 - 180)
            if d > 0.01 or abs(c['x'] - s['x']) > 0.001 or abs(c['y'] - s['y']) > 0.001:
                fail('%s at (%.4f, %.4f) rot %g, no-PMOD (%.4f, %.4f) rot %g' % (ref, c['x'], c['y'], c['rot'], s['x'], s['y'],
                                                                              s['rot']))
            got = pads[ref]
            if sorted(got) != sorted(q[0] for q in s['pads']):
                fail('%s pads %s, no-PMOD %s' % (ref, sorted(got), sorted(q[0] for q in s['pads'])))
            for q in s['pads']:
                p = got.get(q[0])
                if p is None:
                    continue
                if abs(p['x'] - q[1]) > 0.001 or abs(p['y'] - q[2]) > 0.001:
                    fail('%s-%s at (%.4f, %.4f), no-PMOD (%.4f, %.4f)' % (ref, q[0], p['x'], p['y'], q[1], q[2]))
                if (p['net'] or '') != q[3]:
                    fail('%s-%s net %r, no-PMOD %r' % (ref, q[0], p['net'], q[3]))
            for k in ('libref', 'fpdesc'):
                if c[k] != s[k]:
                    warn('%s %s %r, no-PMOD %r' % (ref, k, c[k], s[k]))
        if (c['name_on'], c['comment_on']) != (s['name_on'], s['comment_on']):
            fail('%s NAMEON/COMMENTON %s/%s, no-PMOD %s/%s' % (ref, c['name_on'], c['comment_on'], s['name_on'],
                                                                s['comment_on']))
        t = texts.get(ref)
        if t is None or abs(t['x'] - s['desig']['x']) > 0.005 or abs(t['y'] - s['desig']['y']) > 0.005:
            fail('%s designator at %s, no-PMOD (%.4f, %.4f)' % (ref, None if t is None else '(%.4f, %.4f)' % (t['x'], t['y']),
                                                               s['desig']['x'], s['desig']['y']))
    for pad, net in D['u3_dq']:
        p = pads['U3'].get(pad)
        if p is None or p['net'] != net:
            fail('U3-%s net %r, expected %s' % (pad, None if p is None else p['net'], net))
    box = (min(v[0] for v in B['outline']), min(v[1] for v in B['outline']), max(v[0] for v in B['outline']),
           max(v[1] for v in B['outline']))
    if any(abs(a - b) > 0.0005 for a, b in zip(box, (0, 0, E.BOARD_W, E.BOARD_H))):
        fail('board outline %s is not 0,0 - %g,%g' % (box, E.BOARD_W, E.BOARD_H))


def check_rules(B, D, fail, warn):
    rules = defaultdict(list)
    for r in B['rules']:
        rules[r.get('NAME')].append(r)
    keys = ('RULEKIND', 'SCOPE1EXPRESSION', 'SCOPE2EXPRESSION', 'GAP', 'VERTICALGAP', 'COLLISIONCHECKMODE', 'EXPANSION',
            'NETSCOPE', 'LAYERKIND', 'ENABLED', 'PRIORITY', 'ISTENTINGTOP')
    for name, s in sorted(D['src_rules'].items()):
        got = rules.get(name, [])
        if len(got) != 1:
            fail('rule %s: %d on the board' % (name, len(got)))
            continue
        g = got[0]
        if s.get('RULEKIND') == 'SupplyNets':
            if g.get('SCOPE1EXPRESSION') != s.get('SCOPE1EXPRESSION') or \
                    abs(float(g.get('VOLTAGE', 'nan')) - float(s['VOLTAGE'])) > 1e-6:
                fail('%s %s %s V, no-PMOD %s %s V' % (name, g.get('SCOPE1EXPRESSION'), g.get('VOLTAGE'),
                                                     s['SCOPE1EXPRESSION'], s['VOLTAGE']))
            continue
        diff = {k: (g.get(k), s.get(k)) for k in keys if (k in s or k in g) and g.get(k) != s.get(k)}
        if diff:
            fail('rule %s differs from the no-PMOD board: %s' % (name, diff))
    cls = {c.get('NAME'): sorted(R.class_members(c)) for c in B['classes'] if c.get('KIND') == '0'}
    if cls.get('SDRAM_DATA') != D['src_sdram_data']:
        fail('SDRAM_DATA %s != no-PMOD %s' % (cls.get('SDRAM_DATA'), D['src_sdram_data']))
    for n in E.SDRAM_NETS:
        if n not in B['nets']:
            fail('net %s is not on the board' % n)


def check_bodies(path, B, fail, warn):
    want = json.load(open(BODIES))['bodies']
    got = body_boxes(path, B['comps'])
    exp = defaultdict(list)
    for b in want:
        exp[b['ref']].append(b)
    for ref in sorted(set(got) - set(exp)):
        fail('%d unexpected bodies on %s' % (len(got[ref]), ref))
    for ref, bs in sorted(exp.items()):
        g = sorted(got.get(ref, []))
        if len(g) != len(bs):
            fail('%s carries %d bodies, expected %d' % (ref, len(g), len(bs)))
            continue
        for b in sorted(bs, key=lambda b: (b['x0'], b['y0'])):
            m = [x for x in g if max(abs(x[0] - b['x0']), abs(x[1] - b['y0']), abs(x[2] - b['x1']), abs(x[3] - b['y1'])) <= 0.02]
            if not m:
                fail('%s: no body at %.3f,%.3f-%.3f,%.3f' % (b['part'], b['x0'], b['y0'], b['x1'], b['y1']))
                continue
            x = m[0]
            if x[4] is None or abs(x[4] - b['h']) > 0.001:
                fail('%s body height %s mm, expected %.3f' % (b['part'], x[4], b['h']))
            if x[5] != 'MECHANICAL13':
                fail('%s body on %s, expected MECHANICAL13' % (b['part'], x[5]))
            if x[6] != ('1' if b['bottom'] else '0'):
                warn('%s body projection %s (0 Top, 1 Bottom expected %s)' % (b['part'], x[6], 'Bottom' if b['bottom'] else 'Top'))
            if b['provisional']:
                warn('%s body height %.3f mm is PROVISIONAL (tools/body_heights.json)' % (b['part'], b['h']))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pcb', default=E.TGT_PCB)
    ap.add_argument('--stage', choices=('place', 'rules', 'bodies', 'all'), default='all')
    a = ap.parse_args()
    D = json.load(open(E.DATA, encoding='utf-8'))
    B = R.read(a.pcb)
    fails, warns = [], []
    stages = ('place', 'rules', 'bodies') if a.stage == 'all' else (a.stage,)
    if 'place' in stages:
        check_place(B, D, fails.append, warns.append)
    if 'rules' in stages:
        check_rules(B, D, fails.append, warns.append)
    if 'bodies' in stages:
        check_bodies(a.pcb, B, fails.append, warns.append)
    for w in warns:
        print('WARN', w)
    for f in fails[:200]:
        print('FAIL', f)
    print('sync_altium_verify %s on %s (md5 %s): %d fail, %d warn' % ('+'.join(stages), os.path.basename(a.pcb),
                                                                      B['md5'][:8], len(fails), len(warns)))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
