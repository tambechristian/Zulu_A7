"""Gates for the east JTAG block plan (adapted from tools/route/bodyfix/gates.py). READ-ONLY on the board.

    python gates.py > gates.txt

  1 route_check     plan.json on model_moved.json (new copper vs the board rules, connectivity recount)
  2 hole_gate       every hole pair on the final board (model_final, vias given from/to)
  3 pad_gate        JP3, JP4 pads vs every other SMD pad (copper 0.0762, mask web 0.10)
  4 moved pads vs other-net tracks / vias on their layer (route_check judges new copper only), rule 0.09
  5 route_conn      open connections on the final model
  6 dangling        track ends touching nothing and vias joining < 2 layers, on the touched nets, base vs final
  7 widths          per net and layer, the narrowest piece of every touched power net, base vs final
  8 body_check      final model vs the base model: no new or worse finding; JP3/JP4 neighbours listed
  9 probe access    nearest other body / pad / other-net copper / X2 housing to each of the six pads
 10 stub lengths    the test-point branch of each JTAG net, before and after
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
J = os.path.dirname(HERE)
TOOLS = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1/tools'
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
CLR = 0.09
TOUCHED = ['TCK', 'TMS', 'TDI', 'TDO', 'GND', 'VCC3V3', 'FT-VCORE', 'VCC1V0']
JT = ('JP3', 'JP4')


def run(*a):
    r = subprocess.run([sys.executable, *a], cwd=os.path.dirname(TOOLS), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def with_from_to(M, path):
    M = json.loads(json.dumps(M))
    for v in M['vias']:
        v['from'], v['to'] = v['span'][0], v['span'][-1]
    json.dump(M, open(path, 'w'))
    return path


def dangling(M, nets):
    T, V, Pd = M['tracks'], M['vias'], M['pads']
    planes = {l: n for l, n in M['planes'].items()}
    out = set()

    def touches(net, layer, x, y, w, skip):
        for j, t in enumerate(T):
            if j != skip and t['net'] == net and t['layer'] == layer and \
                    C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], x, y) <= t['w'] / 2 + 1e-4:
                return True
        for v in V:
            if v['net'] == net and layer in v['span'] and math.hypot(v['x'] - x, v['y'] - y) <= v['size'] / 2 + 1e-4:
                return True
        for p in Pd:
            if p['net'] == net and layer in (p['layers'] or STACK) and C.pad_point(p, x, y) <= w / 2 + 1e-4:
                return True
        return False
    for i, t in enumerate(T):
        if t['net'] not in nets:
            continue
        for x, y in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
            if not touches(t['net'], t['layer'], x, y, t['w'], i):
                out.add(('end', t['net'], t['layer'], round(x, 3), round(y, 3)))
    for v in V:
        if v['net'] not in nets:
            continue
        hit = 0
        for l in v['span']:
            if planes.get(l) == v['net']:
                hit += 1
                continue
            if l not in (v['span'][0], v['span'][-1]) and l in planes:
                continue
            if any(t['net'] == v['net'] and t['layer'] == l and
                   C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], v['x'], v['y']) <= t['w'] / 2 + v['size'] / 2 for t in T) or \
                    any(p['net'] == v['net'] and l in (p['layers'] or STACK) and C.pad_point(p, v['x'], v['y']) <= v['size'] / 2
                        for p in Pd) or \
                    any(w is not v and w['net'] == v['net'] and l in w['span'] and
                        math.hypot(w['x'] - v['x'], w['y'] - v['y']) <= (w['size'] + v['size']) / 2 for w in V):
                hit += 1
        if hit < 2:
            out.add(('via', v['net'], v['span'][0], v['span'][-1], round(v['x'], 3), round(v['y'], 3)))
    return out


def widths(M, nets):
    w = {}
    for t in M['tracks']:
        if t['net'] in nets:
            k = (t['net'], t['layer'])
            w[k] = min(w.get(k, 9), t['w'])
    return w


def body_rows(M, comps, refs=None, gap=0.10):
    res = body_check.check(body_check.build(M, comps), refs, gap)
    w = {}
    for r in res:
        k = r[:5]
        if k not in w or r[5] < w[k][5]:
            w[k] = r
    return w


def main():
    plan_p = os.path.join(HERE, 'plan.json')
    P = json.load(open(plan_p))
    M0 = json.load(open(os.path.join(J, 'model.json')))
    MM = json.load(open(os.path.join(HERE, 'model_moved.json')))
    MF = json.load(open(os.path.join(HERE, 'model_final.json')))
    comps0 = json.load(open(os.path.join(J, 'comps.json')))
    compsF = json.load(open(os.path.join(HERE, 'comps_final.json')))
    ok = True
    refs = [m['ref'] for m in P['moves']]
    print('plan: %d moves (%s), remove %d tracks + %d vias, add %d tracks + %d vias' % (
        len(P['moves']), ' '.join('%s d(%+.3f,%+.3f) rot %g' % (m['ref'], m['dx'], m['dy'], m['rotation'])
                                  for m in P['moves']), len(P['remove']), len(P['remove_vias']), len(P['tracks']),
        len(P['vias'])))

    print('\n== 1 route_check plan.json model_moved.json')
    rc, out = run(os.path.join(TOOLS, 'route_check.py'), plan_p, os.path.join(HERE, 'model_moved.json'))
    print('\n'.join('   ' + l for l in out.splitlines()))
    ok &= rc == 0

    print('\n== 2 hole_gate on the whole final board')
    empty = os.path.join(HERE, 'empty_plan.json')
    json.dump({'vias': [], 'tracks': []}, open(empty, 'w'))
    rc, out = run(os.path.join(TOOLS, 'hole_gate.py'), empty, with_from_to(MF, os.path.join(HERE, 'model_final_ft.json')))
    print('\n'.join('   ' + l for l in out.splitlines()))
    ok &= rc == 0
    rc0, out0 = run(os.path.join(TOOLS, 'hole_gate.py'), empty, with_from_to(M0, os.path.join(HERE, 'model_base_ft.json')))
    print('   (base board: %s)' % out0.splitlines()[0])

    print('\n== 3 pad_gate model_final.json %s' % ' '.join(refs))
    rc, out = run(os.path.join(TOOLS, 'pad_gate.py'), os.path.join(HERE, 'model_final.json'), *refs)
    print('\n'.join('   ' + l for l in out.splitlines()))
    ok &= out.strip().endswith('PASS')

    print('\n== 4 moved pads vs other-net tracks and vias on their layers (rule %.2f)' % CLR)
    worst = []
    for p in MF['pads']:
        if p['ref'] not in refs:
            continue
        for t in MF['tracks']:
            if t['net'] != p['net'] and t['layer'] in (p['layers'] or STACK):
                worst.append((C.pad_seg(p, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['w'] / 2, p['ref'], p['pad'], 'track', t['net']))
        for v in MF['vias']:
            if v['net'] != p['net'] and set(v['span']) & set(p['layers'] or STACK):
                worst.append((C.pad_point(p, v['x'], v['y']) - v['size'] / 2, p['ref'], p['pad'], 'via', v['net']))
    worst.sort()
    bad = [w for w in worst if w[0] < CLR - 1e-6]
    print('   min %.4f (%s-%s %s %s), %d under %.2f' % (worst[0] + (len(bad), CLR)))
    for w in worst[:5]:
        print('     %.4f %s-%s %s %s' % w)
    ok &= not bad

    print('\n== 5 route_conn on the final model')
    oc = C.open_count(C.islands(MF))
    print('   open connections:', sum(oc.values()), dict(oc))
    ok &= sum(oc.values()) == 0

    print('\n== 6 dangling ends / weak vias on %s' % ' '.join(TOUCHED))
    d0, d1 = dangling(M0, TOUCHED), dangling(MF, TOUCHED)
    new = sorted(d1 - d0)
    print('   base %d, final %d, new %d, gone %d' % (len(d0), len(d1), len(new), len(d0 - d1)))
    for d in sorted(d0):
        print('     base:', d)
    for d in new:
        print('     NEW:', d)
    ok &= not new

    print('\n== 7 narrowest piece per touched power net and layer (base -> final)')
    w0, w1 = widths(M0, ['VCC1V0', 'FT-VCORE', 'GND', 'VCC3V3']), widths(MF, ['VCC1V0', 'FT-VCORE', 'GND', 'VCC3V3'])
    narrower = []
    for k in sorted(set(w0) | set(w1)):
        if k in w0 and k in w1 and w1[k] < w0[k] - 1e-6:
            narrower.append(k)
        if k[0] == 'VCC1V0' or w0.get(k) != w1.get(k):
            print('   %-9s %-13s %s -> %s' % (k[0], k[1], w0.get(k), w1.get(k)))
    vc0 = sorted(t['w'] for t in M0['tracks'] if t['net'] == 'VCC1V0' and t['layer'] == 'Bottom Layer' and
                 18.5 < max(t['x1'], t['x2']) < 19.6 and min(t['y1'], t['y2']) > 4.5)
    vc1 = sorted(t['w'] for t in MF['tracks'] if t['net'] == 'VCC1V0' and t['layer'] == 'Bottom Layer' and
                 18.5 < max(t['x1'], t['x2']) < 19.6 and min(t['y1'], t['y2']) > 4.5)
    print('   VCC1V0 C86 -> C87 feed piece widths: base %s, final %s' % (vc0, vc1))
    print('   %d net/layer pairs got narrower' % len(narrower))
    ok &= not narrower

    print('\n== 8 body_check (full board, gap 0.10): final vs base')
    b0, b1 = body_rows(M0, comps0), body_rows(MF, compsF)
    newb = [b1[k] for k in b1 if k not in b0 or b1[k][5] < b0[k][5] - 1e-6]
    over = [r for r in b1.values() if r[5] < 0]
    print('   base %d findings, final %d findings, new or worse %d, overlaps in final %d (base %d)' % (
        len(b0), len(b1), len(newb), len(over), len([r for r in b0.values() if r[5] < 0])))
    for r in newb:
        print('     NEW %-6s %-13s %-10s %-10s %-4s %7.3f' % r)
    ok &= not newb
    near = body_rows(MF, compsF, set(JT), 1.0)
    print('   JP3 / JP4 within 1.0 mm (body_check --refs JP3,JP4 --gap 1.0):')
    for r in sorted(near.values(), key=lambda r: r[5])[:8]:
        print('     %-6s %-13s %-10s %-10s %-4s %7.3f' % r)
    from collections import Counter
    print('   mech_mismatch:', body_check.mech_mismatch(compsF) or 'none')

    print('\n== 9 probe access of the six pads (Bottom; pad copper is a 1.0 mm circle)')
    parts = body_check.build(MF, compsF)['Bottom']
    rows = []
    for p in sorted([p for p in MF['pads'] if p['ref'] in JT], key=lambda p: (-p['y'], p['x'])):
        box = (p['x'] - 0.5, p['y'] - 0.5, p['x'] + 0.5, p['y'] + 0.5)
        bod = min((body_check.gap(box, b), n) for n, Pt in parts.items() if n.split('[')[0] not in JT for b in Pt['body'])
        x2 = min((body_check.gap(box, b), n) for n, Pt in parts.items() if n.startswith('X2') for b in Pt['body'])
        opad = min((C.pad_point(q, p['x'], p['y']) - 0.5 if q['shape'] != 'circle' else
                    math.hypot(q['x'] - p['x'], q['y'] - p['y']) - 0.5 - min(q['w'], q['h']) / 2, '%s-%s' % (q['ref'], q['pad']))
                   for q in MF['pads'] if q['ref'] not in JT and 'Bottom Layer' in (q['layers'] or STACK))
        cu = min([(C.seg_dist(t['x1'], t['y1'], t['x2'], t['y2'], p['x'], p['y']) - 0.5 - t['w'] / 2, 'track ' + t['net'])
                  for t in MF['tracks'] if t['layer'] == 'Bottom Layer' and t['net'] != p['net']] +
                 [(math.hypot(v['x'] - p['x'], v['y'] - p['y']) - 0.5 - v['size'] / 2, 'via ' + v['net'])
                  for v in MF['vias'] if 'Bottom Layer' in v['span'] and v['net'] != p['net']])
        rows.append((p, bod, x2, opad, cu))
        print('   %s-%s %-6s (%.3f, %.3f): body %.3f (%s), other pad %.3f (%s), other-net Cu %.3f (%s), X2 housing %.3f' % (
            p['ref'], p['pad'], p['net'], p['x'], p['y'], bod[0], bod[1], opad[0], opad[1], cu[0], cu[1], x2[0]))
    mb = min(r[1][0] for r in rows)
    print('   nearest other part body to any of the six: %.3f mm (target >= 0.30)' % mb)
    ok &= mb >= 0.30 - 1e-9

    print('\n== 10 test-point branch lengths (mm)')

    def L(ts):
        return sum(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) for t in ts)
    rm = P['remove']
    newt = P['tracks']
    tdi0 = [t for t in rm if t['net'] == 'TDI']
    tdo0 = [t for t in rm if t['net'] == 'TDO']
    tck_l4 = [t for t in M0['tracks'] if t['net'] == 'TCK' and t['layer'] == 'L4-SIG' and
              abs(max(t['x1'], t['x2']) - 17.375) < 1e-3]
    tck_b = [t for t in M0['tracks'] if t['net'] == 'TCK' and t['layer'] == 'Bottom Layer']
    tms0 = [t for t in M0['tracks'] if t['net'] == 'TMS' and t['layer'] == 'Bottom Layer']
    tms1 = [t for t in MF['tracks'] if t['net'] == 'TMS' and t['layer'] == 'Bottom Layer']
    nv = lambda n: len([v for v in P['vias'] if v['net'] == n])
    print('   TDI  before %.2f (U2-17 Top run + through via + Bottom run to JP4-1 at (4.85, 3.15))' % L(tdi0))
    print('        after  %.2f (L4 from the R90/R4-3 stack at (12.35, 4.1), %d new lasers, Bottom into JP4-1)' % (
        L([t for t in newt if t['net'] == 'TDI']), nv('TDI')))
    print('   TDO  before %.2f (Bottom from R91-1 to JP4-2 at (6.12, 3.15))' % L(tdo0))
    print('        after  %.2f (L3 from the TDO run at (13.95, 5.275), %d new vias, Bottom into JP4-2)' % (
        L([t for t in newt if t['net'] == 'TDO']), nv('TDO')))
    print('   TCK  before %.2f (R4-6 -> L4 -> JP3-1)   after %.2f (+ %.2f Bottom link)' % (
        L(tck_l4 + tck_b), L(tck_l4 + tck_b) + L([t for t in newt if t['net'] == 'TCK']), L([t for t in newt if t['net'] == 'TCK'])))
    print('   TMS  before %.2f (Bottom from R4-5)       after %.2f' % (L(tms0), L(tms1)))
    print('   GND tie: %.2f mm of 0.25 track to its own through via; VCC3V3 tie: %.2f mm of 0.2 track to its own L5 laser' % (
        L([t for t in newt if t['net'] == 'GND']), L([t for t in newt if t['net'] == 'VCC3V3'])))

    print('\nGATES', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
