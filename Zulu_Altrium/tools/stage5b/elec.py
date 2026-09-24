# -*- coding: utf-8 -*-
"""The return path a reference-plane crossing actually takes, in nanohenries.

Distance alone mis-ranks the capacitors on this board, and both electrical reviewers said so.  The
path a crossing's return current takes to get from L2-GND to L5-VCC3V3 is

    L = L_spread(d)                    the plane pair, as a radial spreading term
      + 0.233 nH/mm  x  tie            the capacitor's own pad-to-via copper, BOTH pads
      + L_barrel + ESL                 the same for every capacitor, so it does not rank them

with, from l5_facts.md and the stack, h(L2..L5 centre to centre) = 1.3512 mm and a 0.10 mm barrel
radius, so L_spread(d) = (mu0 h / 2 pi) ln(d / 0.10) = 0.27024 ln(10 d) nH with d in mm.
0.233 nH/mm is a 0.25-0.30 mm microstrip 0.0994 mm over its own plane.

The point of the formula is that the plane term is LOGARITHMIC in distance while the capacitor's own
tie is LINEAR: 1 mm of extra tie costs 0.233 nH, which is as much as moving a crossing from 10 mm to
4.3 mm.  A well-tied capacitor a long way off beats a badly-tied one close by.

Ties are measured the way tools/stage5/tie_check.py measures them: straight-line from each land to
the nearest via or through-hole pad of that land's own net.
"""
import io, json, math, os, sys

REPO = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium'
L5DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INP = json.load(io.open(os.path.join(REPO, 'tools', 'route_inputs.json'), encoding='utf-8'))
F = json.load(io.open(os.path.join(L5DIR, 'stitch_facts.json'), encoding='utf-8'))

H_CAV = 1.3512
R_VIA = 0.10
K_CAV = 4e-7 * H_CAV * 1e-3 / 2 * 1e9 * math.pi / math.pi      # mu0*h/2pi in nH per ln unit
K_CAV = (4e-7 * math.pi) * (H_CAV * 1e-3) / (2 * math.pi) * 1e9
K_TIE = 0.233


def _pads():
    out = {}
    for key, L in (('top_pads', 'Top'), ('bottom_pads', 'Bottom')):
        for p in INP[key]:
            out.setdefault(p['ref'], {})[str(p['pad'])] = (p['x'], p['y'], p['net'], L)
    return out


PADS = _pads()
VIA = {'VCC3V3': [(v['x'], v['y']) for v in INP['vias'] if v['net'] == 'VCC3V3']
                 + [(p['x'], p['y']) for p in INP['th_pads'] if p['net'] == 'VCC3V3'],
       'GND': [(v['x'], v['y']) for v in INP['vias'] if v['net'] == 'GND']
              + [(p['x'], p['y']) for p in INP['th_pads'] if p['net'] == 'GND']}


def tie_of(ref):
    d = PADS.get(ref, {})
    t = 0.0
    for k, (x, y, net, L) in d.items():
        if net not in VIA:
            return None
        t += min(math.hypot(x - a, y - b) for a, b in VIA[net])
    return t


CAPS0 = []
for c in F['existing_caps']:
    t = tie_of(c['ref'])
    CAPS0.append(dict(ref=c['ref'], x=c['x'], y=c['y'], tie=t if t is not None else 3.0))

SD = [c for c in F['crossings'] if c['cls'].startswith('SDRAM')]


def Lpath(d, tie):
    return K_CAV * math.log(max(d, 0.2) / R_VIA) + K_TIE * tie


def evaluate(new=(), label='', show=0):
    """new: [dict(ref,x,y,tie)]"""
    caps = CAPS0 + list(new)
    rows = []
    for c in SD:
        best = min(((Lpath(math.hypot(c['x'] - k['x'], c['y'] - k['y']), k['tie']), k['ref'],
                     math.hypot(c['x'] - k['x'], c['y'] - k['y']), k['tie']) for k in caps))
        rows.append((best[0], c['net'], best[1], best[2], best[3]))
    v = sorted(r[0] for r in rows)
    med = v[len(v) // 2]
    print('%-26s L_return  worst %.3f nH  median %.3f  mean %.3f' % (
        label, max(v), med, sum(v) / len(v)))
    if show:
        for r in sorted(rows, reverse=True)[:show]:
            print('      %-8s %.3f nH  via %-6s at %.3f mm, its own tie %.3f mm' % (r[1], r[0], r[2], r[3], r[4]))
    return rows


if __name__ == '__main__':
    ties = sorted(c['tie'] for c in CAPS0)
    print('K_cav = %.5f nH per ln unit, K_tie = %.3f nH/mm' % (K_CAV, K_TIE))
    print('the 46 existing VCC3V3<->GND capacitors, own tie (both lands to their nearest same-net via):')
    print('   best %.3f  median %.3f  mean %.3f  worst %.3f mm' % (
        ties[0], ties[len(ties) // 2], sum(ties) / len(ties), ties[-1]))
    print('   worst five: ' + ', '.join('%s %.3f' % (c['ref'], c['tie'])
                                        for c in sorted(CAPS0, key=lambda k: -k['tie'])[:5]))
    evaluate(label='board as saved', show=6)
