"""BTN 0.50 mm west, clear of X5's housing (2026-11-19 body gate, fix "btn").

Saved board (MD5 c4bf0b71): BTN pad 2 (VCC3V3) sat 0.10 mm south of X5's housing and BTN's body 0.35 mm west of it.
BTN moves rigidly 0.50 mm west (no rotation, no y change: the TX / D4 silk labels below it stay clear). Its three
laser via-in-pads (pad 1, pad 2 VCC3V3 stacks; pad 3 N$BTN Top>L2>L3) stay where they are: each land ends up wholly
inside its moved pad (before the move each land overhung its pad's west edge by 0.025 mm).

Copper (Top layer only, 0.0762 signal width, every new piece >= 0.09 from foreign copper):
  N$BTN   the north branch ran at x 40.85 straight through the moved pad 1 (VCC3V3). It now leaves the pad 3-4 link
          at x 41.70, runs north east of pad 1 (0.112 gap) and back to the old track end (40.85, 9.15).
          The pad 3-4 link (41.925 -> 45.275 at y 3.875) ended inside the OLD pad 3 only; a 0.625 mm stub joins it
          to the moved pad 3 again.
  N$LD0B  the LD0-1 -> R80-2 track ran under pad 3 and its diagonal crossed the moved pad 3. It keeps its 45-degree
          start on the same line, drops at x 40.35 (0.112 west of pad 3) and runs east at y 3.669 instead of 3.675
          (0.092 from pads 3/4, 0.093 from N$LD0G at y 3.5; the old run was 0.087 from the pads), ending exactly on
          the line of the kept (46.25, 3.675)-(46.325, 3.75) piece.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1'
M0 = json.load(open(os.path.join(ROOT, 'tools/route/body_gate/model.json')))
S = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
DX = float(sys.argv[1]) if len(sys.argv) > 1 else -0.50
W = 0.0762
TOP = 'Top Layer'

# ---- the move -------------------------------------------------------------------------------------------------
M1 = copy.deepcopy(M0)
btn = [p for p in M1['pads'] if p['ref'] == 'BTN']
assert len(btn) == 4
for p in btn:
    p['x'] = round(p['x'] + DX, 4)
json.dump(M1, open(os.path.join(HERE, 'model1.json'), 'w'))
pad = {p['pad']: p for p in btn}
west = pad['1']['x'] - pad['1']['w'] / 2          # pads 1/3 west edge
east = pad['1']['x'] + pad['1']['w'] / 2          # pads 1/3 east edge
XV = round(west - 0.15, 3)                        # N$LD0B drop, 0.15 - 0.0381 = 0.112 from pad 3
XB = round(east + 0.15, 3)                        # N$BTN north branch, 0.112 from pad 1
YL = 3.669                                        # N$LD0B run under pads 3/4


def find_t(net, layer, x1, y1, x2, y2):
    k = lambda a, b: (round(a, 3), round(b, 3))
    c = [t for t in M0['tracks'] if t['net'] == net and t['layer'] == layer and
         {k(t['x1'], t['y1']), k(t['x2'], t['y2'])} == {k(x1, y1), k(x2, y2)}]
    assert len(c) == 1, (net, layer, x1, y1, x2, y2, len(c))
    return c[0]


rm = [find_t('N$BTN', TOP, 40.85, 5.9, 40.85, 9.15),
      find_t('N$BTN', TOP, 40.85, 5.9, 41.125, 4.375),
      find_t('N$LD0B', TOP, 39.45, 5.175, 40.95, 3.675),
      find_t('N$LD0B', TOP, 40.95, 3.675, 46.25, 3.675)]
# N$LD0B: same 45-degree line x + y = 44.625 as before, then down and east; the run ends on the line x - y = 42.575
# of the kept piece (46.25, 3.675)-(46.325, 3.75)
xe = round(42.575 + YL, 4)
tracks = [
    dict(net='N$BTN', layer=TOP, w=W, x1=round(pad['3']['x'] + 0.275, 4), y1=3.875, x2=41.925, y2=3.875),
    dict(net='N$BTN', layer=TOP, w=W, x1=XB, y1=3.875, x2=XB, y2=6.65),
    dict(net='N$BTN', layer=TOP, w=W, x1=XB, y1=6.65, x2=40.85, y2=9.15),
    dict(net='N$LD0B', layer=TOP, w=W, x1=39.45, y1=5.175, x2=XV, y2=round(44.625 - XV, 4)),
    dict(net='N$LD0B', layer=TOP, w=W, x1=XV, y1=round(44.625 - XV, 4), x2=XV, y2=YL),
    dict(net='N$LD0B', layer=TOP, w=W, x1=XV, y1=YL, x2=xe, y2=YL),
]
vias = []
plan = dict(moves=[dict(ref='BTN', dx=DX, dy=0.0)], remove=[dict(t) for t in rm], remove_vias=[], tracks=tracks,
            vias=vias)
json.dump(plan, open(os.path.join(HERE, 'plan.json'), 'w'), indent=1)

ids_t = {id(t) for t in rm}
MF = copy.deepcopy(M1)
MF['tracks'] = [t for t, t0 in zip(MF['tracks'], M0['tracks']) if id(t0) not in ids_t] + [dict(t) for t in tracks]
MF['vias'] = MF['vias'] + [
    dict({k: v[k] for k in v if k not in ('from', 'to')}, span=S[S.index(v['from']):S.index(v['to']) + 1]) for v in vias]
json.dump(MF, open(os.path.join(HERE, 'model_final.json'), 'w'))
print('BTN dx %.3f: pads 1/3 x %.4f..%.4f; XV %.3f XB %.3f' % (DX, west, east, XV, XB))
print('plan: move BTN, remove %d tracks + %d vias, add %d tracks + %d vias; model_final %d tracks %d vias' % (
    len(rm), 0, len(tracks), len(vias), len(MF['tracks']), len(MF['vias'])))
