"""Gates for the merged body-fix plan (2026-11-19). READ-ONLY.

    python tools/route/bodyfix/gates.py

route_check (new copper, connectivity), hole_gate (every hole pair on the final board), pad_gate (every moved part),
moved pads against other-net tracks and vias on their layers (route_check judges new copper only), and body_check
on the final model (no overlap anywhere; the warnings listed).
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402
import route_conn as C  # noqa: E402

STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
CLR = 0.09


def run(*a):
    r = subprocess.run([sys.executable, *a], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def with_from_to(M, path):
    M = json.loads(json.dumps(M))
    for v in M['vias']:
        v['from'], v['to'] = v['span'][0], v['span'][-1]
    json.dump(M, open(path, 'w'))
    return path


def main():
    plan = os.path.join(HERE, 'plan.json')
    P = json.load(open(plan))
    MM = json.load(open(os.path.join(HERE, 'model_moved.json')))
    MF = json.load(open(os.path.join(HERE, 'model_final.json')))
    ok = True

    rc, out = run(os.path.join(TOOLS, 'route_check.py'), plan, os.path.join(HERE, 'model_moved.json'))
    print('route_check:', out.splitlines()[-1] if out else rc)
    ok &= rc == 0

    empty = os.path.join(HERE, 'empty_plan.json')
    json.dump({'vias': [], 'tracks': []}, open(empty, 'w'))
    rc, out = run(os.path.join(TOOLS, 'hole_gate.py'), empty, with_from_to(MF, os.path.join(HERE, 'model_final_ft.json')))
    print('hole_gate (whole final board):', out.splitlines()[-1] if out else rc)
    ok &= rc == 0

    refs = [m['ref'] for m in P['moves']]
    rc, out = run(os.path.join(TOOLS, 'pad_gate.py'), os.path.join(HERE, 'model_final.json'), *refs)
    print('pad_gate:', out.splitlines()[-1] if out else rc)
    ok &= rc == 0

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
    print('moved pads vs other-net copper: min %.4f (%s-%s %s %s), %d under %.2f' % (worst[0] + (len(bad), CLR)))
    ok &= not bad

    isl = C.islands(MF)
    oc = C.open_count(isl)
    print('route_conn open on the final model:', sum(oc.values()), dict(oc))
    ok &= sum(oc.values()) == 0

    comps = json.load(open(os.path.join(TOOLS, 'route', 'body_gate', 'comps.json')))
    res = body_check.check(body_check.build(MF, comps), None, 0.10)
    w = {}
    for r in res:
        k = r[:4]
        if k not in w or r[5] < w[k][5]:
            w[k] = r
    over = [r for r in w.values() if r[5] < 0]
    print('body_check on the final model: %d overlaps, %d warnings' % (len(over), len(w) - len(over)))
    for r in sorted(w.values(), key=lambda r: r[5]):
        print('   %-6s %-13s %-10s %-10s %-4s %7.3f' % r)
    ok &= not over
    print('GATES', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
