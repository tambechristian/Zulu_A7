"""Compare the copper on the saved asar_feather.PcbDoc (read through KiCad's Altium importer) with routing plans.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/verify_copper.py tools/route/stage1_u1.json [more plans]

Every plan via (net, x, y, span, size, hole) and track (net, layer, width, ends either way round) must be on the
board within 0.002 mm, and the board must carry no via or track that is in no plan. A plan's 'remove' tracks are taken out of the tracks
expected from the plans before it. Coordinates board-relative,
from the board-edge box centre (the board is 50.8 x 22.86 mm).
"""
import json
import os
import sys

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')
NAMES = {'Top Layer': 'Top Layer', 'Bottom Layer': 'Bottom Layer'}


def main():
    app = wx.App(False)  # noqa: F841
    wx.Log.SetActiveTarget(wx.LogStderr())
    b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
    mm = pcbnew.ToMM
    bb = b.GetBoardEdgesBoundingBox()
    cx, cy = mm(bb.GetCenter().x), -mm(bb.GetCenter().y)
    def rel(p):
        return round(mm(p.x) - cx + 25.4, 3), round(-mm(p.y) - cy + 11.43, 3)
    bv, bt = [], []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            x, y = rel(t.GetPosition())
            bv.append((t.GetNetname(), x, y, b.GetLayerName(t.TopLayer()), b.GetLayerName(t.BottomLayer()),
                       round(mm(t.GetWidth(pcbnew.F_Cu)), 3), round(mm(t.GetDrillValue()), 3)))
        else:
            a, c = rel(t.GetStart()), rel(t.GetEnd())
            bt.append((t.GetNetname(), b.GetLayerName(t.GetLayer()), round(mm(t.GetWidth()), 3), tuple(sorted([a, c]))))
    pv, pt = [], []
    for path in sys.argv[1:]:
        P = json.load(open(path))
        for r in P.get('remove', []):          # a later plan's removals take tracks out of the expected set
            key = (r['net'], r['layer'], round(r['w'], 3),
                   tuple(sorted([(round(r['x1'], 3), round(r['y1'], 3)), (round(r['x2'], 3), round(r['y2'], 3))])))
            hit = [i for i, q in enumerate(pt) if q[:3] == key[:3] and all(
                abs(a - b) <= 0.003 for P_, Q_ in zip(q[3], key[3]) for a, b in zip(P_, Q_))]
            if len(hit) != 1:
                sys.exit('%s: removal %s matches %d expected tracks' % (path, key, len(hit)))
            del pt[hit[0]]
        pv += [(v['net'], round(v['x'], 3), round(v['y'], 3), v['from'], v['to'], round(v['size'], 3), round(v['hole'], 3))
               for v in P['vias']]
        pt += [(t['net'], t['layer'], round(t['w'], 3),
                tuple(sorted([(round(t['x1'], 3), round(t['y1'], 3)), (round(t['x2'], 3), round(t['y2'], 3))]))) for t in P['tracks']]
    def match(a, b, tol=0.003):
        if a[0] != b[0] or len(a) != len(b):
            return False
        for u, w in zip(a[1:], b[1:]):
            if isinstance(u, float):
                if abs(u - w) > tol:
                    return False
            elif isinstance(u, tuple):
                if any(abs(p - q) > tol for P_, Q_ in zip(u, w) for p, q in zip(P_, Q_)):
                    return False
            elif u != w:
                return False
        return True
    def diff(plan, board):
        left = list(board)
        missing = []
        for p in plan:
            for i, q in enumerate(left):
                if match(p, q):
                    del left[i]
                    break
            else:
                missing.append(p)
        return missing, left
    mv, xv = diff(pv, bv)
    mt, xt = diff(pt, bt)
    print('vias: plan %d, board %d, missing %d, extra %d' % (len(pv), len(bv), len(mv), len(xv)))
    print('tracks: plan %d, board %d, missing %d, extra %d' % (len(pt), len(bt), len(mt), len(xt)))
    for x in (mv + mt)[:10]:
        print('  MISSING', x)
    for x in (xv + xt)[:10]:
        print('  EXTRA', x)
    print('PASS' if not (mv or xv or mt or xt) else 'FAIL')


if __name__ == '__main__':
    main()
