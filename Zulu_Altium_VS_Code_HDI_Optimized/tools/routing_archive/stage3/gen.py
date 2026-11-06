# -*- coding: utf-8 -*-
"""Stage 3 (VCC3V3 and the FT2232H rails): rebuild tools/stage3_route.json from the nine parts.

    python tools/stage3/gen.py            re-runs every part's gen.py in order and merges the outputs
    python tools/stage3/gen.py --check    the same, then compares the md5 with plan_md5.txt (exit 1 on a mismatch)
    python tools/stage3/gen.py --no-run   only merges the parts' plan.json files as they lie on disk
    python tools/stage3/gen.py --inputs PRE.json     once the stage is placed: the board before it
                                          (git show 2ba657f:Zulu_Altrium/tools/route_inputs.json > PRE.json)

The plan was built on 2026-09-21 in three steps (docs/stage3_vcc3v3.md): a trunk (parts/s3_trunk, judged from
three designs) that carries VCC3V3 from the regulator block to seven taps; seven regions in parallel, each
closing its own pads from its tap with the trunk as base copper (parts/r_west, r_sdled, r_north, r_south,
r_u1field, r_northbank, r_east; regions.json names their pads and boxes); the FT rails after the south region
(parts/r_ft, base = trunk + west + sdled + north + south); then a merge, two reviews and a final judge.  Each
part's gen.py records its own base plans and every merge/judge repair as a note.

Order: s3_trunk; r_west, r_sdled, r_north, r_south (base: trunk); r_ft (base: trunk + the four); r_u1field,
r_northbank, r_east (base: trunk).  The whole-board gates were run on the concatenation, so the parts' widths
stand as their own gen.py measured them.
"""
import hashlib, io, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, 'parts')
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import merge as M

ORDER = ['s3_trunk', 'r_west', 'r_sdled', 'r_north', 'r_south', 'r_ft', 'r_u1field', 'r_northbank', 'r_east']
ARGS = sys.argv[1:]
OUT = ARGS[ARGS.index('--out') + 1] if '--out' in ARGS else os.path.join(TOOLS, 'stage3_route.json')
EXTRA = ['--inputs', ARGS[ARGS.index('--inputs') + 1]] if '--inputs' in ARGS else []


def main():
    if '--no-run' not in ARGS:
        os.makedirs(os.path.join(HERE, 'gen_out'), exist_ok=True)
        for part in ORDER:
            gen = os.path.join(PARTS, part, 'gen.py')
            log = os.path.join(HERE, 'gen_out', part + '.txt')
            with io.open(log, 'w', encoding='utf-8', newline='\n') as f:
                r = subprocess.run([sys.executable, gen] + EXTRA, cwd=os.path.dirname(TOOLS), stdout=f, stderr=subprocess.STDOUT)
            if r.returncode != 0:
                raise SystemExit('%s/gen.py failed (exit %d), see %s' % (part, r.returncode, log))
            print('ran %-11s -> parts/%s/plan.json' % (part, part))
    paths = [os.path.join(PARTS, part, 'plan.json') for part in ORDER]
    plan, dup = M.merge(paths)
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(json.dumps(plan, indent=1))
    md5 = hashlib.md5(io.open(OUT, 'rb').read()).hexdigest()
    print('wrote %s: %d vias, %d tracks from %d parts, %d duplicate(s) dropped, md5 %s' % (OUT, len(plan['vias']), len(plan['tracks']), len(paths), dup, md5))
    if '--check' in ARGS:
        want = io.open(os.path.join(HERE, 'plan_md5.txt'), encoding='utf-8').read().split()[0]
        if want != md5:
            print('MISMATCH: plan_md5.txt records %s' % want)
            return 1
        print('matches plan_md5.txt (the gated plan)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
