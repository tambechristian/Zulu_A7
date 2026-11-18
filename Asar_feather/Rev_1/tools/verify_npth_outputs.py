"""Check a Gerber / NC drill re-export against the NPTH clearance plan (2026-11-16).

Compares the old and new Altium exports as geometry multisets (apertures resolved by their definition, so D-code
renumbering between Altium builds does not matter). The copper layers the plan edits (GTL, G2, G3, GBL) must differ
by exactly the plan's removed and added segments; every other Gerber and every drill file must be geometrically
identical; DRR and LDP must match apart from date and path lines.
    python tools/verify_npth_outputs.py OLD_OUTPUT_DIR NEW_OUTPUT_DIR tools/route/npth_clearance/plan.json
"""
import json
import os
import re
import sys
from collections import Counter

OLD, NEW, PLAN = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = 'asar_feather'
GERB = ['GTL', 'G1', 'G2', 'G3', 'G4', 'GBL', 'GTS', 'GBS', 'GTO', 'GBO', 'GTP', 'GBP', 'GM']
LAYER_OF = {'Top': 'GTL', 'L3-SIG': 'G2', 'L4-SIG': 'G3', 'Bottom': 'GBL'}


def parse(path):
    txt = open(path, encoding='latin-1').read()
    fs = re.search(r'%FSLAX(\d)(\d)Y(\d)(\d)\*%', txt)
    dec = int(fs.group(2))
    ap, macros = {}, {}
    for m in re.finditer(r'%AM(\w+)\*(.*?)%', txt, re.S):
        macros[m.group(1)] = re.sub(r'\s+', '', m.group(2))
    for m in re.finditer(r'%ADD(\d+)([A-Za-z_][\w.]*)(?:,([^*]*))?\*%', txt):
        name, params = m.group(2), m.group(3) or ''
        if name in macros:
            ap[int(m.group(1))] = ('MACRO', macros[name], params)
        else:
            ap[int(m.group(1))] = (name, params)
    body = re.sub(r'%.*?%', '', txt, flags=re.S)
    prims = Counter()
    x = y = 0.0
    cur = None
    region = False
    poly = []
    interp = 'G01'
    unknown = Counter()
    for cmd in body.split('*'):
        cmd = cmd.strip()
        if not cmd or cmd.startswith('G04'):
            continue
        if cmd == 'G36':
            region, poly = True, []
            continue
        if cmd == 'G37':
            region = False
            if poly:
                prims[('REGION', tuple(poly))] += 1
            poly = []
            continue
        dsel = re.match(r'^(?:G54)?D(\d+)$', cmd)
        if dsel and int(dsel.group(1)) >= 10:
            cur = ap[int(dsel.group(1))]
            continue
        m = re.match(r'^(G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?(D0?[123])?$', cmd)
        if not m:
            if cmd not in ('G75', 'G74', 'M02', 'G71', 'G90', 'G91'):
                unknown[cmd[:12]] += 1
            continue
        g, xs, ys, i_, j_, d = m.groups()
        if g:
            interp = 'G0' + g[-1]
        nx = int(xs) / 10 ** dec if xs is not None else x
        ny = int(ys) / 10 ** dec if ys is not None else y
        if d in ('D01', 'D1'):
            arc = ('G01',) if interp == 'G01' else (interp, round(int(i_ or 0) / 10 ** dec, 4), round(int(j_ or 0) / 10 ** dec, 4))
            if region:
                if not poly:
                    poly.append((round(x, 4), round(y, 4)))
                poly.append((round(nx, 4), round(ny, 4)) + (() if interp == 'G01' else arc))
            else:
                a, b = (round(x, 4), round(y, 4)), (round(nx, 4), round(ny, 4))
                key = tuple(sorted([a, b])) if interp == 'G01' else (a, b)
                prims[('DRAW', cur, key, arc)] += 1
        elif d in ('D02', 'D2'):
            if region and poly:
                prims[('REGION', tuple(poly))] += 1
                poly = []
        elif d in ('D03', 'D3'):
            prims[('FLASH', cur, (round(nx, 4), round(ny, 4)))] += 1
        x, y = nx, ny
    return prims, unknown


def drills(path):
    hits = Counter()
    tools = {}
    tool = None
    for line in open(path, encoding='latin-1'):
        line = line.strip()
        m = re.match(r'^T(\d+)F\d+S\d+C([\d.]+)', line) or re.match(r'^T(\d+)C([\d.]+)', line)
        if m:
            tools[m.group(1)] = float(m.group(2))
            continue
        m = re.match(r'^T(\d+)$', line)
        if m:
            tool = tools.get(m.group(1))
            continue
        if line.startswith(('X', 'Y')):
            hits[(tool, line)] += 1
    return hits, tools


def segs(p):
    return [(tuple(a), tuple(b)) for a, b in zip(p, p[1:]) if tuple(a) != tuple(b)]


plan = json.load(open(PLAN))
exp = {}
for e in plan['edits']:
    g = LAYER_OF[e['layer']]
    exp.setdefault(g, [Counter(), Counter(), []])
    for a, b in segs(e['old']):
        exp[g][0][(e['width'], tuple(sorted([(round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))])))] += 1
    for a, b in segs(e['new']):
        exp[g][1][(e['width'], tuple(sorted([(round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))])))] += 1
    exp[g][2].append(e['net'])


def as_plan(c):
    out, other = Counter(), Counter()
    for k, n in c.items():
        if k[0] == 'DRAW' and k[1] and k[1][0] == 'C' and k[3] == ('G01',):
            out[(round(float(k[1][1].split('X')[0]), 4), k[2])] += n
        else:
            other[k] += n
    return out, other


def match(got, want, tol=6e-4):
    want = list(want.elements())
    un_g = []
    for g in got.elements():
        hit = None
        for i, w in enumerate(want):
            if abs(g[0] - w[0]) < 1e-4 and all(abs(p - q) < tol for P, Q in zip(g[1], w[1]) for p, q in zip(P, Q)):
                hit = i
                break
        if hit is None:
            un_g.append(g)
        else:
            want.pop(hit)
    return un_g, want


ok = True
tot_rm = tot_add = 0
for ext in GERB:
    a, ua = parse(os.path.join(OLD, '%s.%s' % (BASE, ext)))
    b, ub = parse(os.path.join(NEW, '%s.%s' % (BASE, ext)))
    if ua or ub:
        print('   %s unparsed commands old %s new %s' % (ext, dict(ua), dict(ub)))
    rm, add = a - b, b - a
    nrm, nadd = sum(rm.values()), sum(add.values())
    if ext not in exp:
        st = 'IDENTICAL' if not rm and not add else 'DIFFERS'
        ok &= not rm and not add
        print('%-4s %6d prims  removed %d added %d  %s' % (ext, sum(b.values()), nrm, nadd, st))
        for k in list(rm)[:5]:
            print('   -', k)
        for k in list(add)[:5]:
            print('   +', k)
        continue
    rmp, rmo = as_plan(rm)
    addp, addo = as_plan(add)
    e_rm, e_add, nets = exp[ext]
    ug1, uw1 = match(rmp, e_rm)
    ug2, uw2 = match(addp, e_add)
    good = not rmo and not addo and not ug1 and not uw1 and not ug2 and not uw2
    ok &= good
    tot_rm += nrm
    tot_add += nadd
    print('%-4s %6d prims  removed %d (plan %d) added %d (plan %d)  nets %s  %s' % (
        ext, sum(b.values()), nrm, sum(e_rm.values()), nadd, sum(e_add.values()), nets, 'MATCHES PLAN' if good else 'MISMATCH'))
    for lab, v in (('removed non-draw', list(rmo.items())), ('added non-draw', list(addo.items())), ('removed not in plan', ug1),
                   ('plan removal missing', uw1), ('added not in plan', ug2), ('plan addition missing', uw2)):
        if v:
            print('   %s (%d): %s' % (lab, len(v), v[:6]))
print('copper total removed %d added %d' % (tot_rm, tot_add))

dfiles = sorted(f for f in os.listdir(NEW) if re.search(r'\.(TXT|TX\d+)$', f) and f.startswith(BASE))
for f in dfiles:
    ha, ta = drills(os.path.join(OLD, f))
    hb, tb = drills(os.path.join(NEW, f))
    same = ha == hb and ta == tb
    ok &= same
    print('%-40s tools %s hits %d  %s' % (f, tb, sum(hb.values()), 'IDENTICAL' if same else 'DIFFERS'))
for f in ('asar_feather.DRR', 'asar_feather.LDP'):
    pat = r'\d{1,2}:\d\d:\d\d|\d+/\d+/\d{4}|Project Outputs|Users'
    A = [l for l in open(os.path.join(OLD, f), encoding='latin-1') if not re.search(pat, l)]
    B = [l for l in open(os.path.join(NEW, f), encoding='latin-1') if not re.search(pat, l)]
    print('%-40s %s (date/path lines ignored)' % (f, 'IDENTICAL' if A == B else 'DIFFERS'))
    if A != B:
        import difflib
        print(''.join(list(difflib.unified_diff(A, B, n=0))[:20]))
    ok &= A == B
print('ALL OK' if ok else 'NOT OK')
sys.exit(0 if ok else 1)
