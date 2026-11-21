"""widthcheck.py <PcbDoc> <plan.json> [extra class members json {class: [nets]}]
Checks every plan track's width against the board's enabled Width rules (highest priority = lowest PRIORITY number
whose scope matches: InNet('x'), InNetClass('c'), All, joined with Or), per-layer MINWIDTH keys honoured."""
import json
import re
import sys

import olefile

LAYKEY = {'Top Layer': 'TOPLAYER', 'L3-SIG': 'MIDLAYER1', 'L4-SIG': 'MIDLAYER2', 'Bottom Layer': 'BOTTOMLAYER'}
o = olefile.OleFileIO(sys.argv[1])


def recs(stream):
    return [r.decode('latin1') for r in o.openstream(stream).read().split(b'\x00') if b'|' in r]


def kv(s):
    return dict(p.split('=', 1) for p in s.split('|') if '=' in p)


def mil(v):
    return float(v.replace('mil', '')) * 0.0254 if v.endswith('mil') else float(v.replace('mm', ''))


classes = {}
for s in recs('Classes6/Data'):
    d = kv(s)
    if d.get('KIND') == '0':
        classes[d.get('NAME')] = {d[k] for k in d if k.startswith('M') and k[1:].isdigit()}
if len(sys.argv) > 3:
    for c, ns in json.load(open(sys.argv[3])).items():
        classes.setdefault(c, set()).update(ns)
rules = []
for s in recs('Rules6/Data'):
    d = kv(s)
    if d.get('RULEKIND') == 'Width' and d.get('ENABLED') == 'TRUE':
        rules.append(d)
rules.sort(key=lambda d: int(d['PRIORITY']))


def match(expr, net):
    for term in expr.split(' Or '):
        term = term.strip()
        if term == 'All':
            return True
        m = re.match(r"InNet\('(.*)'\)", term)
        if m and m.group(1) == net:
            return True
        m = re.match(r"InNetClass\('(.*)'\)", term)
        if m and net in classes.get(m.group(1), ()):
            return True
    return False


P = json.load(open(sys.argv[2]))
bad = 0
for t in P['tracks']:
    r = next(r for r in rules if match(r['SCOPE1EXPRESSION'], t['net']))
    lk = LAYKEY.get(t['layer'])
    mn = mil(r.get(lk + '_MINWIDTH', r['MINLIMIT'])) if lk else mil(r['MINLIMIT'])
    mx = mil(r.get(lk + '_MAXWIDTH', r['MAXLIMIT'])) if lk else mil(r['MAXLIMIT'])
    if t['w'] < mn - 1e-4 or t['w'] > mx + 1e-4:
        bad += 1
        print('WIDTH %s %s w=%.4f rule %s [%.4f, %.4f] (%.3f,%.3f)-(%.3f,%.3f)' % (
            t['net'], t['layer'], t['w'], r['NAME'], mn, mx, t['x1'], t['y1'], t['x2'], t['y2']))
print('width violations', bad, 'of', len(P['tracks']), 'tracks; classes', {k: len(v) for k, v in classes.items() if k.startswith('PWR')})
