# -*- coding: utf-8 -*-
"""SDRAM crossing metrics against the set of VCC3V3<->GND capacitors (centre-to-centre)."""
import io, json, math, os, sys
L5 = 'C:/Users/tambe/AppData/Local/Temp/claude/C--Users-tambe-Documents-Electronics-Zulu-A7-Zulu-Altrium/1e3d9c42-62fe-43bd-a170-baf7d18a0d60/scratchpad/l5'
F = json.load(io.open(os.path.join(L5, 'stitch_facts.json'), encoding='utf-8'))
CAPS0 = [(c['x'], c['y']) for c in F['existing_caps']]
SD = [c for c in F['crossings'] if c['cls'].startswith('SDRAM')]
XA = [c for c in F['crossings'] if c['cls'] == 'XADC']
CH = [c for c in F['crossings'] if c['cls'] == 'CHARGER']

def dists(cross, extra=()):
    caps = CAPS0 + list(extra)
    out = []
    for c in cross:
        d = min(math.hypot(c['x'] - a, c['y'] - b) for a, b in caps)
        out.append((d, c['net'], c['x'], c['y']))
    return sorted(out)

def med(v):
    v = sorted(v); n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0

def summarise(extra=(), cross=None, label=''):
    D = dists(cross if cross is not None else SD, extra)
    d = [x[0] for x in D]
    print('%-22s n=%d  beyond5=%d  worst=%.4f  median=%.4f  mean=%.4f' % (
        label, len(d), sum(1 for v in d if v > 5.0), max(d), med(d), sum(d) / len(d)))
    return D

if __name__ == '__main__':
    extra = []
    for p in sys.argv[1:]:
        j = json.load(io.open(p, encoding='utf-8'))
        if isinstance(j, dict) and 'moves' in j:
            extra += [(m['x'], m['y']) for m in j['moves']]   # NB pad-1 anchored
        else:
            extra += [(s['x'], s['y']) for s in j]
    D = summarise((), label='board as saved')
    print('   beyond 5.0:', ', '.join('%s %.4f' % (n, d) for d, n, x, y in D if d > 5.0))
    summarise((), XA, 'XADC as saved')
    summarise((), CH, 'CHARGER as saved')
