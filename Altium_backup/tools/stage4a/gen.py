# -*- coding: utf-8 -*-
"""Stage 4a, MERGE: rebuild plan.json from the six region plans and merge them.

    python gen.py            regenerate every region plan (its gen.py, in place), merge, write plan.json + plan_md5.txt
    python gen.py --no-regen merge the region plan.json files as they stand

Regions are generated north FIRST (belly's U2-47 tie ends on north's U3-54 via and loads r_north/plan.json as base
copper), then belly, south, u1, east, west; the merge order is the one the brief fixes: belly, south, u1, east,
north, west (tools/stage4/merge.py: exact duplicates kept once, a 'remove' key refused).  GND only."""
import hashlib, io, json, os, subprocess, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/tools/stage4')
import merge as M

HERE = os.path.dirname(os.path.abspath(__file__))
S4 = os.path.join(HERE, 'parts')          # the six region parts
TOOLS = os.path.dirname(HERE)
MERGE_ORDER = ['belly', 'south', 'u1', 'east', 'north', 'west']
GEN_ORDER = ['north', 'belly', 'south', 'u1', 'east', 'west']
ARGS = sys.argv[1:]
EXTRA = ['--inputs', ARGS[ARGS.index('--inputs') + 1]] if '--inputs' in ARGS else []   # once placed: git a7aa623 route_inputs


def regen():
    for r in GEN_ORDER:
        d = os.path.join(S4, 'r_' + r)
        res = subprocess.run([sys.executable, 'gen.py'] + EXTRA, cwd=d, capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit('r_%s/gen.py failed:\n%s' % (r, res.stderr[-2000:]))
        p = json.load(io.open(os.path.join(d, 'plan.json'), encoding='utf-8'))
        print('r_%-6s regenerated: %2d vias %3d tracks' % (r, len(p['vias']), len(p['tracks'])))


def main():
    if '--no-regen' not in sys.argv:
        regen()
    paths = [os.path.join(S4, 'r_' + r, 'plan.json') for r in MERGE_ORDER]
    plan, dup = M.merge(paths)
    assert all(v['net'] == 'GND' for v in plan['vias']) and all(t['net'] == 'GND' for t in plan['tracks'])
    out = ARGS[ARGS.index('--out') + 1] if '--out' in ARGS else os.path.join(TOOLS, 'stage4a_route.json')
    io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(plan, indent=1))
    md5 = hashlib.md5(io.open(out, 'rb').read()).hexdigest()
    want = io.open(os.path.join(HERE, 'plan_md5.txt'), encoding='utf-8').read().split()[0]
    if '--check' in ARGS and want != md5:
        sys.exit('MISMATCH: plan_md5.txt records %s, rebuilt %s' % (want, md5))
    print('wrote %s: %d vias, %d tracks from %d plans, %d duplicate(s) dropped; md5 %s%s' % (
        out, len(plan['vias']), len(plan['tracks']), len(paths), dup, md5, ' (matches plan_md5.txt)' if want == md5 else ''))


if __name__ == '__main__':
    main()
