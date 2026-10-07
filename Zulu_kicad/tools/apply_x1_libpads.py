# Update the KiCad library footprint MOLEX-105017-0001: MS1/MS2 take the padstack of X1 on the board (rotation 0).
# Usage: python -u apply_x1_libpads.py <copy of zulu_a7.pretty> ../kicad_project/zulu_a7.kicad_pcb
# NOTE: FootprintSave rewrites every UUID; on 2026-10-07 only the two resulting MS pad blocks were spliced into the
# original .kicad_mod (pad UUIDs kept), so the installed file differs from the old one only in those two blocks.
import pcbnew, wx, sys
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
LIB, BOARD = sys.argv[1], sys.argv[2]
CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)
fp = io.FootprintLoad(LIB, 'MOLEX-105017-0001')
x1 = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD).FindFootprintByReference('X1')
assert x1.GetOrientationDegrees() == 0 and not x1.IsFlipped()
for name in ('MS1', 'MS2'):
    lp = [p for p in fp.Pads() if p.GetNumber() == name][0]; bp = [p for p in x1.Pads() if p.GetNumber() == name][0]
    assert lp.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_CIRCLE and abs(lp.GetDrillSize().x - 599950) < 100, 'pre-state'
    assert lp.GetFPRelativePosition() == bp.GetFPRelativePosition()
    lp.Padstack().SetMode(bp.Padstack().Mode())
    for l in CU: lp.SetShape(l, bp.GetShape(l)); lp.SetSize(l, bp.GetSize(l))
    lp.SetDrillShape(bp.GetDrillShape()); lp.SetDrillSize(bp.GetDrillSize())
io.FootprintSave(LIB, fp)
print('saved', LIB)
