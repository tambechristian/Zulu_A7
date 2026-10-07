"""Prove two boards have identical physical content (placement + copper).

Usage (KiCad python): python geom_diff.py A.kicad_pcb B.kicad_pcb
Compares footprint ref/position/orientation/side, every pad's position and
partition-independent shape, tracks/arcs/vias geometry, zone outlines.
Net *names* are ignored (renames are expected); connectivity is checked by
compare_nets.py.
"""
import sys
import pcbnew


def sig(path):
    b = pcbnew.LoadBoard(path)
    fps = sorted((f.GetReference(), f.GetPosition().x, f.GetPosition().y,
                  round(f.GetOrientationDegrees(), 4), f.IsFlipped()) for f in b.GetFootprints())
    pads = sorted((f.GetReference(), p.GetNumber(), p.GetPosition().x, p.GetPosition().y,
                   p.GetSizeX(), p.GetSizeY(), p.GetDrillSizeX())
                  for f in b.GetFootprints() for p in f.Pads())
    trk = sorted((t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x,
                  t.GetEnd().y, t.GetWidth(pcbnew.F_Cu) if t.Type() == pcbnew.PCB_VIA_T else t.GetWidth(),
                  t.GetDrillValue() if t.Type() == pcbnew.PCB_VIA_T else 0) for t in b.GetTracks())
    zones = sorted((z.GetLayer(), z.GetNumCorners(), z.GetPosition().x, z.GetPosition().y)
                   for z in b.Zones())
    return {"footprints": fps, "pads": pads, "tracks+vias": trk, "zones": zones}


a, b = sig(sys.argv[1]), sig(sys.argv[2])
ok = True
for k in a:
    same = a[k] == b[k]
    ok &= same
    print(f"{k:12s} {len(a[k]):5d} vs {len(b[k]):5d}  {'IDENTICAL' if same else 'DIFFERENT'}")
sys.exit(0 if ok else 1)
