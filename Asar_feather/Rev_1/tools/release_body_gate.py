"""Release gate: component bodies must not collide (2026-11-19, ported from Zulu_A7_no_pmod/Rev_2). READ-ONLY on the board.

    python tools/release_body_gate.py [--pcb PcbDoc] [--gap 0.10]

Altium's batch DRC said nothing about parts sitting on each other (the 2026-11-18 board pictures showed BTN against
X5's housing and U8's body over C151's pad), so every release runs this gate as well. It re-reads the saved PcbDoc
with KiCad's Altium reader (tools/route_model.py for the pads, tools/comps_from_board.py for side, rotation and
footprint of every part), builds each body with tools/body_check.py (datasheet sizes, the connector outlines in
tools/body_mech.json, X2 as two bottom-side header housings) and checks every pair on each side.

FAIL (exit 1, and the release scripts stop):
  * two bodies overlap, at nominal or at maximum package tolerance (body_body < 0, body_body_max < 0);
  * a body lies over another part's pad (body_pad < 0);
  * a part's footprint has no body model (not in body_check.BODY, not in body_mech.json, not exempt below), so a new
    part cannot slip through unchecked;
  * a connector in body_mech.json (X1, X3, X4, X5) has changed side, rotation or footprint since its outline was
    derived (body_check.mech_mismatch).
WARN (reported, release continues): bodies or body-to-pad closer than --gap but not touching, and a maximum-tolerance
body over another part's pad where the nominal body clears it (body_pad_max).

tools/generate_pcbway_assembly.py and tools/package_fabrication_release.py call gate() before writing anything.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import body_check  # noqa: E402

PCB = os.path.join(ROOT, 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')
KICAD_PY = os.environ.get('KICAD_PYTHON', r'C:\Program Files\KiCad\10.0\bin\python.exe')
OUT = os.path.join(HERE, 'route', 'body_gate')
# footprints with no body by design: the Creative Commons artwork (off the board) and the JTAG test pads JP3/JP4
EXEMPT = {'CC_BY', 'CC_CC', 'CC_COPYRIGHT', 'CC_SA', 'TP-1X03-SMD'}


def _kicad(script, *args, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([KICAD_PY, script, *args], env=e, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('%s failed:\n%s' % (os.path.basename(script), r.stderr[-2000:]))


def gate(pcb=PCB, gap=0.10, out=OUT, quiet=False):
    """Returns (failures, warnings) as lists of strings; raises RuntimeError if a FAIL is found."""
    os.makedirs(out, exist_ok=True)
    model, comps = os.path.join(out, 'model.json'), os.path.join(out, 'comps.json')
    _kicad(os.path.join(HERE, 'route_model.py'), env={'ASAR_PCB': pcb, 'ASAR_MODEL': model})
    _kicad(os.path.join(HERE, 'comps_from_board.py'), comps, env={'ASAR_PCB': pcb})
    M, D = json.load(open(model)), json.load(open(comps))
    fails, warns = list(body_check.mech_mismatch(D)), []
    for c in D['comps']:
        p = c['pattern']
        if p in body_check.BODY or c['ref'] in D['mech'] or p in EXEMPT or p in body_check.SPECIAL:
            continue
        fails.append('%s: footprint %s has no body model (add it to body_check.BODY or tools/body_mech.json)' % (c['ref'], p))
    worst = {}
    for r in body_check.check(body_check.build(M, D), None, gap):
        k = r[:4]
        if k not in worst or r[5] < worst[k][5]:
            worst[k] = r
    for side, kind, a, b, pad, g in sorted(worst.values(), key=lambda r: r[5]):
        what = '%-6s %-13s %-10s %-10s %-4s %7.3f mm' % (side, kind, a, b, pad, g)
        (fails if g < 0 and kind != 'body_pad_max' else warns).append(what)
    if not quiet:
        for f in fails:
            print('BODY GATE FAIL', f)
        for w in warns:
            print('BODY GATE warn', w)
        print('BODY GATE: %d fail, %d warn (gap %.2f mm) on %s' % (len(fails), len(warns), gap, os.path.basename(pcb)))
    if fails:
        raise RuntimeError('component-body gate failed: %d overlap(s) or unmodelled footprint(s); '
                           'see the BODY GATE FAIL lines' % len(fails))
    return fails, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--pcb', default=PCB)
    ap.add_argument('--gap', type=float, default=0.10)
    a = ap.parse_args()
    try:
        gate(a.pcb, a.gap)
    except RuntimeError as e:
        print(e)
        return 1
    print('BODY_GATE PASS')
    return 0


if __name__ == '__main__':
    sys.exit(main())
