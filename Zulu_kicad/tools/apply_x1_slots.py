# Apply the X1 slot fix (2026-10-07) to the KiCad copy, taking every new value from KiCad's own import of the
# corrected production Altium board. Guards: every object must match its pre-fix state, so a second run stops.
# Ported from the Altium fix in Zulu_Altium_VS_Code/tools/ProdX1Slots*.pas (itself ported, unchanged in
# geometry, from Zulu_Altium_VS_Code_HDI_Optimized/tools/CorrectX1Slots.pas).
# Run with KiCad's python, with the PCB editor closed:  "C:/Program Files/KiCad/10.0/bin/python.exe" -u apply_x1_slots.py
import pcbnew, wx, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, '..', 'kicad_project', 'zulu_a7.kicad_pcb')
ALTIUM = os.path.join(HERE, '..', '..', 'Zulu_Altium_VS_Code', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
F = pcbnew.FromMM
K = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD)
N = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER, ALTIUM)
def near(a, b, tol=2): return abs(a - b) <= tol  # nm
def pt(x, y): return pcbnew.VECTOR2I(F(x), F(y))
changes = 0
# 1. X1 MS1/MS2 -> oval 0.6 x 1.3 drill, copied from the import
kx1 = K.FindFootprintByReference('X1'); nx1 = N.FindFootprintByReference('X1')
for name in ('MS1', 'MS2'):
    kp = [p for p in kx1.Pads() if p.GetNumber() == name]; np_ = [p for p in nx1.Pads() if p.GetNumber() == name]
    assert len(kp) == 1 and len(np_) == 1
    kp, np_ = kp[0], np_[0]
    assert kp.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_CIRCLE and near(kp.GetDrillSize().x, F(0.59995)), name
    assert np_.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_OBLONG
    assert kp.GetPosition() == np_.GetPosition()
    kp.SetDrillShape(np_.GetDrillShape()); kp.SetDrillSize(np_.GetDrillSize()); changes += 1
# 2. CHAN12: four tracks and two vias (pre-fix KiCad coordinates -> post-fix)
moves = [  # layer, old start, old end, new start, new end  (KiCad mm)
    (pcbnew.B_Cu,   (129.7261, 94.4036), (129.8261, 94.5036), (129.7261, 94.4036), (129.8261, 94.5536)),
    (pcbnew.B_Cu,   (129.8261, 94.5036), (149.6761, 94.5036), (129.8261, 94.5536), (149.3761, 94.5536)),
    (pcbnew.B_Cu,   (149.6761, 94.5036), (149.7261, 94.4536), (149.3761, 94.5536), (149.3761, 94.3536)),
    (pcbnew.In3_Cu, (149.7261, 94.4536), (149.8261, 94.5536), (149.3761, 94.3536), (149.8261, 94.5536)),
]
nt = [t for t in N.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetNetname() == 'CHAN12']
for lay, a, b, c, d in moves:
    hit = [t for t in K.GetTracks() if t.GetClass() != 'PCB_VIA' and t.GetNetname() == 'CHAN12' and t.GetLayer() == lay
           and ((t.GetStart() == pt(*a) and t.GetEnd() == pt(*b)) or (t.GetStart() == pt(*b) and t.GetEnd() == pt(*a)))]
    assert len(hit) == 1, (a, b, len(hit))
    ref = [t for t in nt if t.GetLayer() == lay and {(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)} == {(F(c[0]), F(c[1])), (F(d[0]), F(d[1]))}]
    assert len(ref) == 1, ('not in import', c, d)
    t = hit[0]
    if t.GetStart() == pt(*a): t.SetStart(pt(*c)); t.SetEnd(pt(*d))
    else: t.SetStart(pt(*d)); t.SetEnd(pt(*c))
    changes += 1
kv = [v for v in K.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetname() == 'CHAN12' and v.GetPosition() == pt(149.7261, 94.4536)]
nv = [v for v in N.GetTracks() if v.GetClass() == 'PCB_VIA' and v.GetNetname() == 'CHAN12' and v.GetPosition() == pt(149.3761, 94.3536)]
assert len(kv) == 2 and len(nv) == 2
for v in kv: v.SetPosition(pt(149.3761, 94.3536)); changes += 1
# 3. X1 designator, copied from the import
kr, nr = kx1.Reference(), nx1.Reference()
assert near(kr.GetPosition().x, F(143.087), 1000) and near(kr.GetPosition().y, F(90.0728), 1000), kr.GetPosition()
kr.SetPosition(nr.GetPosition()); changes += 1
# 4. Plane fills on L2 (In1) and L5 (In4), copied from the import
for net, lay in (('GND', pcbnew.In1_Cu), ('VCC3V3', pcbnew.In4_Cu)):
    kz = [z for z in K.Zones() if z.GetNetname() == net]; nz = [z for z in N.Zones() if z.GetNetname() == net]
    assert len(kz) == 1 and len(nz) == 1
    kz, nz = kz[0], nz[0]
    assert kz.Outline().Area() == nz.Outline().Area()
    kz.SetFilledPolysList(lay, pcbnew.SHAPE_POLY_SET(nz.GetFilledPolysList(lay))); kz.SetIsFilled(True); changes += 1
print('changes applied:', changes)
pcbnew.SaveBoard(BOARD, K)
print('saved', BOARD)
