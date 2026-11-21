"""Dangling copper by KiCad's connectivity engine on the saved PcbDoc (2026-11-19). READ-ONLY.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route/drc20/dangling.py

Round 1 lists what KiCad calls dangling (to compare with Altium's 5 Net Antennae). Then removes dangling tracks and
vias in memory, repeats to a fixpoint, and reports the unconnected-pad count before and after: the removal is only
proposed if that count does not change. Writes tools/route/drc20/dangling.json.
"""
import json
import os

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BOARD = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
app = wx.App(False)  # noqa: F841
wx.Log.SetActiveTarget(wx.LogStderr())
b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
mm = pcbnew.ToMM
c = b.GetBoardEdgesBoundingBox().GetCenter()
cx, cy = mm(c.x), -mm(c.y)


def rel(p):
    return round(mm(p.x) - cx + 30.48, 4), round(-mm(p.y) - cy + 12.7, 4)


def desc(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        v = t.Cast()
        return dict(kind='via', net=t.GetNetname(), xy=rel(t.GetPosition()), size=round(mm(v.GetWidth(pcbnew.F_Cu)), 4),
                    top=b.GetLayerName(v.TopLayer()), bottom=b.GetLayerName(v.BottomLayer()))
    return dict(kind='track', net=t.GetNetname(), layer=b.GetLayerName(t.GetLayer()), w=round(mm(t.GetWidth()), 4),
                a=rel(t.GetStart()), b=rel(t.GetEnd()))


def dangling():
    b.BuildConnectivity()
    cn = b.GetConnectivity()
    out = []
    for t in b.GetTracks():
        if cn.TestTrackEndpointDangling(t, False):
            out.append(t)
    return out


b.BuildConnectivity()
before = b.GetConnectivity().GetUnconnectedCount(False)
removed, rnd = [], 0
while True:
    d = dangling()
    if not d:
        break
    rnd += 1
    if rnd == 1:
        print('round 1: %d dangling' % len(d))
        for t in d:
            print('  ', desc(t))
    for t in d:
        removed.append(desc(t))
        b.Remove(t)
b.BuildConnectivity()
after = b.GetConnectivity().GetUnconnectedCount(False)
print('rounds %d, removed %d objects; unconnected before %d after %d' % (rnd, len(removed), before, after))
by = {}
for r in removed:
    by.setdefault(r['net'], []).append(r)
for n, rs in by.items():
    print(n, len(rs))
    for r in rs:
        print('   ', r)
json.dump(dict(before=before, after=after, removed=removed), open(os.path.join(HERE, 'dangling.json'), 'w'), indent=1)
