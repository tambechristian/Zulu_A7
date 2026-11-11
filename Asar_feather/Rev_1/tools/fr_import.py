"""Routing stage 2 (2026-10-23): Freerouting's session -> a plan for tools/emit_copper.py.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/fr_import.py <workdir> <session.ses> <plan.json>

Loads <workdir>/feather.kicad_pcb (written by fr_prepare.py, every pre-existing track and via locked), imports
the session into it, and writes every track and via that is NOT locked -- Freerouting's new copper -- as a plan:
board-relative mm (origin at the board's lower-left corner, from the board-edge box centre; the board is
50.8 x 22.86 mm), KiCad layer names as the Altium layer names, via span = its top and bottom layer.
Also reports how many connections the board still has unrouted after the import (KiCad's connectivity).
"""
import json
import os
import sys
from collections import Counter

import pcbnew


def main():
    wd, ses, out = sys.argv[1], sys.argv[2], sys.argv[3]
    b = pcbnew.LoadBoard(os.path.join(wd, 'feather.kicad_pcb'))
    before = sum(1 for t in b.GetTracks())
    if not pcbnew.ImportSpecctraSES(b, ses):
        sys.exit('session import failed')
    mm = pcbnew.ToMM
    c = b.GetBoardEdgesBoundingBox().GetCenter()
    cx, cy = mm(c.x), -mm(c.y)
    def rel(p):
        return round(mm(p.x) - cx + 25.4, 4), round(-mm(p.y) - cy + 11.43, 4)
    vias, tracks, locked = [], [], 0
    for t in b.GetTracks():
        if t.IsLocked():
            locked += 1
            continue
        if t.GetClass() == 'PCB_VIA':
            x, y = rel(t.GetPosition())
            vias.append({'net': t.GetNetname(), 'x': x, 'y': y, 'size': round(mm(t.GetWidth(pcbnew.F_Cu)), 4),
                         'hole': round(mm(t.GetDrillValue()), 4), 'from': b.GetLayerName(t.TopLayer()),
                         'to': b.GetLayerName(t.BottomLayer())})
        elif t.GetClass() == 'PCB_TRACK':
            (x1, y1), (x2, y2) = rel(t.GetStart()), rel(t.GetEnd())
            if (x1, y1) == (x2, y2):
                continue
            tracks.append({'net': t.GetNetname(), 'layer': b.GetLayerName(t.GetLayer()), 'w': round(mm(t.GetWidth()), 4),
                           'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
        else:
            sys.exit('unexpected ' + t.GetClass())
    b.BuildConnectivity()
    unrouted = b.GetConnectivity().GetUnconnectedCount(False)
    json.dump({'source': os.path.basename(ses), 'vias': vias, 'tracks': tracks, 'unrouted_after': unrouted},
              open(out, 'w'), indent=0)
    print('board before import: %d copper objects; locked after: %d' % (before, locked))
    print('new: %d vias %s, %d tracks' % (len(vias), dict(Counter((v['from'], v['to']) for v in vias)), len(tracks)))
    print('track layers', dict(Counter(t['layer'] for t in tracks)))
    print('KiCad connectivity: %d unrouted connections after the import' % unrouted)


if __name__ == '__main__':
    main()
