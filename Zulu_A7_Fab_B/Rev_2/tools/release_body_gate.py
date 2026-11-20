"""Release gate: component bodies must not collide (Fab B Rev 2, 2026-11-20). READ-ONLY on the board.

    python tools/release_body_gate.py [--pcb PcbDoc] [--gap 0.10]

Ported from Zulu_A7_no_pmod/Rev_2/tools/release_body_gate.py (427960e), where it was added on 2026-11-19 because
Altium's DRC said nothing about parts sitting on each other (the 2026-11-14 audit found U4 on U1, R34 on U7 and
more). Every release runs it: tools/generate_jlcpcb_assembly.py and tools/package_fabrication_release.py call gate()
before writing anything. It re-reads the saved PcbDoc with KiCad's Altium reader (tools/route_model.py for the pads,
tools/route/illustration/comps_from_board.py for side, rotation and footprint of every part), builds each body with
tools/body_check.py (datasheet sizes, the connector outlines in tools/body_mech.json -- X1, X3, X4 and the Fab B-only
Pmod header J1 -- and X2 as four bottom-side 1x10 housings) and checks every pair on each side.

FAIL (exit 1, and the release scripts stop):
  * two bodies overlap, at nominal or at maximum package tolerance (body_body < 0, body_body_max < 0);
  * a body lies over another part's pad (body_pad < 0);
  * a part's footprint has no body model: not in body_check.BODY, no body_mech.json entry FOR THAT FOOTPRINT (the
    entry's 'pattern' must equal the part's footprint; new in this copy), not exempt below -- so a new or swapped
    part cannot slip through unchecked;
  * a body_mech.json entry names a part that is not on the board, or carries no 'pattern' (new in this copy).
WARN (reported, release continues): bodies or body-to-pad closer than --gap but not touching.
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

PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc')
KICAD_PY = os.environ.get('KICAD_PYTHON', r'C:\Program Files\KiCad\10.0\bin\python.exe')
OUT = os.path.join(HERE, 'route', 'release_gate')
# footprints with no body by design: Creative Commons artwork (off the board) and the do-not-stuff JTAG holes JP3/JP4
EXEMPT = {'CC_BY', 'CC_CC', 'CC_COPYRIGHT', 'CC_SA', '1X03-NOSILK'}
SPECIAL = {'ZULU-DIP37'}     # X2: body_check builds its four bottom-side housings itself


def _kicad(script, *args, env=None):
    e = dict(os.environ, **(env or {}))
    r = subprocess.run([KICAD_PY, script, *args], env=e, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('%s failed:\n%s' % (os.path.basename(script), r.stderr[-2000:]))


def unmodelled(D):
    """Parts the gate cannot model, and body_mech.json entries that do not fit the board (list of strings)."""
    out = []
    refs = {c['ref']: c for c in D['comps']}
    for c in D['comps']:
        p = c['pattern']
        if p in body_check.BODY or body_check.mech_for(D, c['ref'], p) is not None or p in EXEMPT or p in SPECIAL:
            continue
        m = D['mech'].get(c['ref'])
        why = (' (tools/body_mech.json has %s for a %s)' % (c['ref'], m.get('pattern'))) if m else ''
        out.append('%s: footprint %s has no body model%s (add it to body_check.BODY or tools/body_mech.json)'
                   % (c['ref'], p, why))
    for ref, m in sorted(D['mech'].items()):
        if 'pattern' not in m:
            out.append('tools/body_mech.json %s has no pattern' % ref)
        elif ref not in refs:
            out.append('tools/body_mech.json %s is not on the board' % ref)
    return out


def gate(pcb=PCB, gap=0.10, out=OUT, quiet=False):
    """Returns (failures, warnings) as lists of strings; raises RuntimeError if a FAIL is found."""
    os.makedirs(out, exist_ok=True)
    model, comps = os.path.join(out, 'model.json'), os.path.join(out, 'comps.json')
    _kicad(os.path.join(HERE, 'route_model.py'), env={'FABB_PCB': pcb, 'FABB_MODEL': model})
    _kicad(os.path.join(HERE, 'route', 'illustration', 'comps_from_board.py'), comps, env={'FABB_PCB': pcb})
    M, D = json.load(open(model)), json.load(open(comps))
    return judge(M, D, gap, os.path.basename(pcb), quiet)


def judge(M, D, gap=0.10, name='board', quiet=False):
    fails, warns = unmodelled(D), []
    worst = {}
    for r in body_check.check(body_check.build(M, D), None, gap):
        k = r[:4]
        if k not in worst or r[5] < worst[k][5]:
            worst[k] = r
    for side, kind, a, b, pad, g in sorted(worst.values(), key=lambda r: r[5]):
        what = '%-6s %-13s %-10s %-10s %-4s %7.3f mm' % (side, kind, a, b, pad, g)
        (fails if g < 0 else warns).append(what)
    if not quiet:
        for f in fails:
            print('BODY GATE FAIL', f)
        for w in warns:
            print('BODY GATE warn', w)
        print('BODY GATE: %d fail, %d warn (gap %.2f mm) on %s' % (len(fails), len(warns), gap, name))
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
