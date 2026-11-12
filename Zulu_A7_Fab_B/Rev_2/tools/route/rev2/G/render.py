"""render.py <board.json> <plan.json|-> <out.png> x0 x1 y0 y1 [layers comma] [highlight nets comma]
Draws the board model with the plan applied (compose_plan.apply); removed copper is drawn as a dashed outline,
plan copper outlined in black. One panel per layer."""
import json, sys, math, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools')
import compose_plan as CP

B = json.load(open(sys.argv[1]))
P = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'tracks': [], 'vias': []}
x0, x1, y0, y1 = map(float, sys.argv[4:8])
layers = sys.argv[8].split(',') if len(sys.argv) > 8 and sys.argv[8] else ['Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer']
layers = [{'T': 'Top Layer', '3': 'L3-SIG', '4': 'L4-SIG', 'B': 'Bottom Layer', '2': 'L2-GND', '5': 'L5-VCC3V3'}.get(l, l) for l in layers]
hl = set(sys.argv[9].split(',')) if len(sys.argv) > 9 and sys.argv[9] else set()
M = CP.apply(B, P)
rt = {CP.tkey(t) for t in P.get('remove', [])}
rv = {CP.vkey(v) for v in P.get('remove_vias', [])}
pt = {CP.tkey(t) for t in P['tracks']}
pv = {CP.vkey(v) for v in P['vias']}
STACK = CP.STACK
n = len(layers)
cols = 2 if n > 1 else 1
rows = (n + cols - 1) // cols
fw = 11
fig, axs = plt.subplots(rows, cols, figsize=(fw * cols, fw * (y1 - y0) / (x1 - x0) * rows + 0.5), squeeze=False)


def segpoly(t):
    dx, dy = t['x2'] - t['x1'], t['y2'] - t['y1']
    L = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / L * t['w'] / 2, dx / L * t['w'] / 2
    return [(t['x1'] + nx, t['y1'] + ny), (t['x2'] + nx, t['y2'] + ny), (t['x2'] - nx, t['y2'] - ny), (t['x1'] - nx, t['y1'] - ny)]


def colr(net):
    if net in hl:
        return 'magenta'
    if net == 'GND':
        return 'green'
    if net == 'VCC3V3':
        return 'red'
    return 'C%d' % (hash(net) % 10)


for k, L in enumerate(layers):
    ax = axs[k // cols][k % cols]
    ax.set_title(L)
    for p in M['pads']:
        if not (x0 - 2 < p['x'] < x1 + 2 and y0 - 2 < p['y'] < y1 + 2):
            continue
        ls = p['layers'] if p['layers'] else (STACK if p['drill'] else [])
        if L not in ls:
            continue
        c = colr(p['net'] or '')
        if p['shape'] == 'circle' or p['ref'] == 'U1':
            ax.add_patch(Circle((p['x'], p['y']), min(p['w'], p['h']) / 2, color=c, alpha=.35))
        else:
            ax.add_patch(Rectangle((p['x'] - p['w'] / 2, p['y'] - p['h'] / 2), p['w'], p['h'], color=c, alpha=.35))
        if p['drill']:
            ax.add_patch(Circle((p['x'], p['y']), p['drill'] / 2, color='k', alpha=.3))
        ax.text(p['x'], p['y'], '%s-%s\n%s' % (p['ref'], p['pad'], p['net']), fontsize=4, ha='center', va='center')
    for t in B['tracks']:
        if t['layer'] == L and CP.tkey(t) in rt:
            ax.add_patch(Polygon(segpoly(t), fill=False, ec=colr(t['net']), ls='--', lw=.5))
    for t in M['tracks']:
        if t['layer'] != L:
            continue
        if max(t['x1'], t['x2']) < x0 - 1 or min(t['x1'], t['x2']) > x1 + 1 or max(t['y1'], t['y2']) < y0 - 1 or min(t['y1'], t['y2']) > y1 + 1:
            continue
        new = CP.tkey(t) in pt
        ax.add_patch(Polygon(segpoly(t), color=colr(t['net']), alpha=.75 if new else .45, lw=.6 if new else 0, ec='k' if new else None))
        if math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) > 0.6 and x0 < (t['x1'] + t['x2']) / 2 < x1 and y0 < (t['y1'] + t['y2']) / 2 < y1:
            ax.text((t['x1'] + t['x2']) / 2, (t['y1'] + t['y2']) / 2, t['net'], fontsize=4)
    for v in M['vias']:
        sp = v.get('span') or CP.vspan(v)
        if L not in sp or not (x0 - 1 < v['x'] < x1 + 1 and y0 - 1 < v['y'] < y1 + 1):
            continue
        new = CP.vkey(v) in pv
        ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, color='k' if len(sp) == 6 else colr(v['net']), alpha=.5,
                            ec='k' if new else None, lw=.6))
        ax.text(v['x'], v['y'], '%s %s' % (v['net'], ''.join(s[1] if s[0] == 'L' else s[0] for s in sp)), fontsize=3.5)
    for v in B['vias']:
        sp = v.get('span')
        if L in sp and CP.vkey(v) in rv and x0 < v['x'] < x1 and y0 < v['y'] < y1:
            ax.add_patch(Circle((v['x'], v['y']), v['size'] / 2, fill=False, ec='k', ls='--', lw=.5))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.grid(True, lw=.3)
    ax.set_xticks([round(x0 + i * 0.5, 2) for i in range(int((x1 - x0) / 0.5) + 1)])
    ax.set_yticks([round(y0 + i * 0.5, 2) for i in range(int((y1 - y0) / 0.5) + 1)])
    ax.tick_params(labelsize=4)
plt.tight_layout()
plt.savefig(sys.argv[3], dpi=150)
