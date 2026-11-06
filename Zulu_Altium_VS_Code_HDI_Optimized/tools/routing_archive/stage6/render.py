# -*- coding: utf-8 -*-
"""Render a routing plan over the whole board (any nets; colours for the stage-3/4 nets, black otherwise).

    python tools/stage4/render.py <plan.json> <out.png> [--inputs F] [--title T]

Grey is everything already on the board.  If the board model already contains the plan's copper (the
plan has been placed and route_inputs.json rebuilt), those primitives are drawn in colour, not grey.
"""
import collections, io, json, math, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, Patch

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import hdi
a = sys.argv[1:]
RI = a[a.index('--inputs') + 1] if '--inputs' in a else os.path.join(TOOLS, 'route_inputs.json')
plan_path, out = a[0], a[1]
inp = json.load(io.open(RI, encoding='utf-8'))
plan = json.load(io.open(plan_path, encoding='utf-8'))
COL = {'VCC3V3': '#c62828', 'FT-VCORE': '#00838f', 'FT-VPHY': '#6a1b9a', 'FT-VPLL': '#2e7d32', 'GND': '#1b5e20'}
TITLE = a[a.index('--title') + 1] if '--title' in a else 'Zulu A7 routing plan'
_pk = collections.Counter((t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)) for t in plan['tracks'])
_pk.update((t['net'], t['layer'], round(t['x2'], 3), round(t['y2'], 3), round(t['x1'], 3), round(t['y1'], 3)) for t in plan['tracks'])
_pv = collections.Counter((v['net'], round(v['x'], 3), round(v['y'], 3), hdi.span_of(v)) for v in plan.get('vias', []))
inp['tracks'] = [t for t in inp['tracks'] if (t['net'], t['layer'], round(t['x1'], 3), round(t['y1'], 3), round(t['x2'], 3), round(t['y2'], 3)) not in _pk]
inp['vias'] = [v for v in inp['vias'] if (v['net'], round(v['x'], 3), round(v['y'], 3), hdi.span_of(v)) not in _pv]
fig, ax = plt.subplots(figsize=(20, 7.6))
ax.set_xlim(-0.5, 70.35); ax.set_ylim(-0.5, 25.9); ax.set_aspect('equal')
ax.add_patch(Rectangle((0, 0), 69.85, 25.4, fill=False, ec='k', lw=1.2))
for t in inp['tracks']:
    al = {'Top': 0.30, 'Bottom': 0.22, 'L3-SIG': 0.13, 'L4-SIG': 0.13}[t['layer']]
    ax.plot([t['x1'], t['x2']], [t['y1'], t['y2']], color='#9e9e9e', lw=max(t['width'] * 2.2, 0.35), alpha=al, solid_capstyle='round')
for v in inp['vias']:
    ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fc='#bdbdbd', ec='none', alpha=0.5))
for p in inp['bottom_pads'] + inp['top_pads']:
    fc = COL.get(p.get('net'), '#cfd8dc')
    ax.add_patch(Rectangle((p['x'] - p['sx'] / 2, p['y'] - p['sy'] / 2), p['sx'], p['sy'], fc=fc, ec='none', alpha=0.55 if p.get('net') not in COL else 0.9))
for p in inp['th_pads']:
    fc = COL.get(p.get('net'), '#90a4ae')
    ax.add_patch(Rectangle((p['x'] - p['sx'] / 2, p['y'] - p['sy'] / 2), p['sx'], p['sy'], fc=fc, ec='#607d8b', lw=0.3))
for t in plan['tracks']:
    c = COL.get(t['net'], '#000000')
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / L * t['width'] / 2, dx / L * t['width'] / 2
    al = {'Top': 0.95, 'Bottom': 0.70, 'L3-SIG': 0.50, 'L4-SIG': 0.50}[t['layer']]
    ax.add_patch(Polygon([(t['x1'] + nx, t['y1'] + ny), (t['x2'] + nx, t['y2'] + ny),
                          (t['x2'] - nx, t['y2'] - ny), (t['x1'] - nx, t['y1'] - ny)], fc=c, ec='none', alpha=al))
    for q in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
        ax.add_patch(Circle(q, t['width'] / 2, fc=c, ec='none', alpha=al))
for v in plan.get('vias', []):
    # a microvia (any span but through) gets an orange ring so a plan picture shows it
    thru = hdi.is_through(hdi.span_of(v))
    ax.add_patch(Circle((v['x'], v['y']), 0.175, fc=COL.get(v['net'], '#000'), ec='k' if thru else '#ff6f00', lw=0.4 if thru else 1.0))
    ax.add_patch(Circle((v['x'], v['y']), 0.10, fc='white', ec='none'))
for x, y, s in ((5.2, 18.75, '3.3 V source'), (8.89, 24.13, 'X2-17'), (14.15, 12.37, 'X3-4 SD'), (31.5, 13.6, 'U2 FT2232HL'),
                (28.3, 11.9, 'U3 SDRAM (Bottom)'), (46.4, 12.0, 'U1'), (66.4, 19.05, 'J1 Pmod'), (66.84, 3.72, 'JP4-3')):
    ax.annotate(s, (x, y), (x, y + 2.4), fontsize=8, ha='center', color='#263238', arrowprops=dict(arrowstyle='-', color='#607d8b', lw=0.6))
nv, nt = len(plan.get('vias', [])), len(plan['tracks'])
byl = collections.Counter(t['layer'] for t in plan['tracks'])
present = sorted(set(t['net'] for t in plan['tracks']) | set(v['net'] for v in plan.get('vias', [])))
handles = [Patch(fc=COL.get(n, '#000'), label=n) for n in present][:8]
fig.legend(handles=handles, loc='lower center', ncol=4, fontsize=9, frameon=False)
ax.set_title('%s: %d vias, %d tracks (Top %d, Bottom %d, L3 %d, L4 %d); grey = copper already placed. Top solid, Bottom lighter, inner layers lightest.'
             % (TITLE, nv, nt, byl.get('Top', 0), byl.get('Bottom', 0), byl.get('L3-SIG', 0), byl.get('L4-SIG', 0)), fontsize=10)
ax.set_xlabel('x (mm)'); ax.set_ylabel('y (mm)')
ax.grid(True, lw=0.15)
plt.tight_layout(rect=(0, 0.05, 1, 1))
plt.savefig(out, dpi=115)
print('wrote', out)
