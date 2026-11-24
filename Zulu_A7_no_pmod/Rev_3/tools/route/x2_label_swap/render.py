"""Render top-side silk boxes (after edits), pad mask openings, bodies. python render.py geom edits out.png x0 x1 y0 y1 [highlight idx,...]"""
import json, sys, math
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import os
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
G = json.load(open(sys.argv[1])); E = json.load(open(sys.argv[2])) if sys.argv[2] != '-' else {'delete': [], 'set': {}}
out = sys.argv[3]; x0, x1, y0, y1 = map(float, sys.argv[4:8])
src = open(os.path.join(HERE, 'check_silk.py')).read()
ns = {}
exec('import math\n' + src[src.index('def box_of'):src.index('def bgap')], ns); box_of = ns['box_of']
texts = {t['idx']: dict(t) for t in G['texts']}
dele = set(int(i) for i in E.get('delete', []))
for k, v in E.get('set', {}).items(): texts[int(k)].update(v)
for k, v in enumerate(E.get('add', [])): t = dict(v); t.update(idx=100000 + k, kind='free', shown=True, ref=None); texts[t['idx']] = t
fig, ax = plt.subplots(figsize=((x1 - x0) / 1.4, (y1 - y0) / 1.4), dpi=100)
ax.add_patch(Rectangle((0, 0), G['board']['w'], G['board']['h'], fc='#14361f', ec='k'))
for r, bs in G['bodies'].get('Top', {}).items():
    for b in bs:
        ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc='#333333', ec='#888888', lw=0.6, alpha=0.8))
        ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, r, color='#aaaaaa', fontsize=6, ha='center', va='center', clip_on=True)
for p in G['pads']:
    if p['side'] != 'Top': continue
    m = p['mask']
    if p['shape'] == 'circle': ax.add_patch(Circle((p['x'], p['y']), (m[2] - m[0]) / 2, fc='#c9a94a', ec='none'))
    else: ax.add_patch(Rectangle((m[0], m[1]), m[2] - m[0], m[3] - m[1], fc='#c9a94a', ec='none'))
for a in G['arcs']:
    if a['layer'] == 33: ax.add_patch(Circle((a['cx'], a['cy']), a['r'] + a['w'] / 2, fc='w', ec='none'))
for s in G['tracks']:
    if s['layer'] == 33: ax.plot([s['x1'], s['x2']], [s['y1'], s['y2']], color='w', lw=s['w'] * 30)
hl = set(int(i) for i in (sys.argv[8].split(',') if len(sys.argv) > 8 else []))
for i, t in texts.items():
    if i in dele or not t.get('shown') or t['layer'] != 33: continue
    b = box_of(t)
    c = '#ff5050' if (i in hl or str(i) in E.get('set', {}) or i >= 100000) else 'w'
    ax.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fc='none', ec=c, lw=0.8))
    ax.text((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, t['text'], color=c, fontsize=7, ha='center', va='center', rotation=round(t['rot']) % 360, clip_on=True)
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.grid(True, lw=0.3, alpha=0.4)
ax.set_xticks([x0 + i for i in range(int(x1 - x0) + 1)]); ax.set_yticks([y0 + i for i in range(int(y1 - y0) + 1)]); ax.tick_params(labelsize=6)
fig.subplots_adjust(0.03, 0.04, 0.99, 0.99); fig.savefig(out); print(out)
