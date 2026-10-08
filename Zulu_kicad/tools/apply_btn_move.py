# KiCad copy: BTN moved 0.5 mm west and X2's reference hidden (2026-10-07), copied from KiCad's own import of the
# production Altium board after Zulu_Altium_VS_Code/tools/BtnMove.pas (docs/btn_move.md):
#   BTN (PTS810) from x 20.3 to 19.8 mm (Altium coordinates); the LED0_B, N$BTN and FT-RESETN via stacks that stood in
#   its new pad field moved, BTN pad 1's VCC3V3 through via became a Top>L5 microvia stack, and the 17 tracks that end
#   on them were re-drawn or added; the GND (In1) and VCC3V3 (In4) zone fills are replaced by the imported fills
#   (no refill, see CONVERSION.md).
# The track/via change is taken as the exact difference between this board and the import. Guards: BTN must be at
# its old place, the difference must be 14 tracks out / 17 in and 13 vias out / 16 in, all inside BTN's area, and
# only on the four nets the move touches. A rerun stops at the first guard.
#   python -u tools/apply_btn_move.py kicad_project/zulu_a7.kicad_pcb <production zulu_a7.PcbDoc> <out.kicad_pcb>
import pcbnew, wx, sys
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
BOARD, ALTIUM, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F = pcbnew.FromMM; X0, Y0 = 113.5761, 117.7036
def kpt(x, y): return pcbnew.VECTOR2I(F(x + X0), F(Y0 - y))
def nr(p, q, tol=2000): return abs(p.x - q.x) <= tol and abs(p.y - q.y) <= tol
K = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD)
N = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER, ALTIUM)
NETS = {'VCC3V3', 'N$BTN', 'LED0_B', 'FT-RESETN'}
LO, HI = kpt(17.5, 16.5), kpt(23.0, 9.5)          # BTN's area (KiCad y grows downward)
def inside(p): return LO.x <= p.x <= HI.x and LO.y <= p.y <= HI.y

kb, nb = K.FindFootprintByReference('BTN'), N.FindFootprintByReference('BTN')
assert nr(kb.GetPosition(), kpt(20.3, 12.92)), 'BTN is not at its old place'
assert nr(nb.GetPosition(), kpt(19.8, 12.92)), 'the import does not have BTN moved'
assert kb.GetOrientationDegrees() == nb.GetOrientationDegrees()


# Geometry only: this copy names some nets from the schematic (Net-(LD3-PadA)) where the import has NetLD3_A.
def sig(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return ('via', t.GetPosition().x, t.GetPosition().y, t.TopLayer(), t.BottomLayer(), t.GetWidth(pcbnew.F_Cu),
                t.GetDrillValue())
    return (t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetWidth())


ks = {}
for t in K.Tracks():
    ks.setdefault(sig(t), []).append(t)
ns = {}
for t in N.Tracks():
    ns.setdefault(sig(t), []).append(t)
out = [s for s in ks if s not in ns]
new = [s for s in ns if s not in ks]
assert all(len(ks[s]) == 1 for s in out) and all(len(ns[s]) == 1 for s in new), 'duplicate objects in the difference'
cnt = lambda lst, kind: sum(1 for s in lst if (s[0] == 'via') == (kind == 'via'))
got = (cnt(out, 'trk'), cnt(new, 'trk'), cnt(out, 'via'), cnt(new, 'via'))
assert got == (14, 17, 13, 16), got
for s in out + new:
    t = (ks.get(s) or ns.get(s))[0]
    assert t.GetNetname() in NETS, s
    pts = [t.GetPosition()] if s[0] == 'via' else [t.GetStart(), t.GetEnd()]
    assert all(inside(p) for p in pts), s

for s in out:
    K.Remove(ks[s][0])
for s in new:
    src = ns[s][0]
    c = src.Duplicate()
    K.Add(c)
    net = K.FindNet(src.GetNetname()); assert net is not None, src.GetNetname()
    c.SetNet(net)
    assert sig(c) == s, (sig(c), s)

kb.SetPosition(nb.GetPosition())
kp = sorted((p.GetNumber(), p.GetPosition().x, p.GetPosition().y) for p in kb.Pads())
np_ = sorted((p.GetNumber(), p.GetPosition().x, p.GetPosition().y) for p in nb.Pads())
assert kp == np_, (kp, np_)
assert kb.Reference().GetPosition() == nb.Reference().GetPosition()

kx, nx = K.FindFootprintByReference('X2'), N.FindFootprintByReference('X2')
assert kx.Reference().IsVisible() and not nx.Reference().IsVisible(), 'X2 reference: board must show it, import must not'
kx.Reference().SetVisible(False)

for net, layer in (('GND', pcbnew.In1_Cu), ('VCC3V3', pcbnew.In4_Cu)):
    kz = [z for z in K.Zones() if z.GetNetname() == net][0]; nz = [z for z in N.Zones() if z.GetNetname() == net][0]
    assert kz.Outline().Area() == nz.Outline().Area()
    kz.SetFilledPolysList(layer, pcbnew.SHAPE_POLY_SET(nz.GetFilledPolysList(layer))); kz.SetIsFilled(True)

print('tracks out/in %d/%d, vias out/in %d/%d; BTN moved; X2 reference hidden; 2 plane fills replaced' % got)
pcbnew.SaveBoard(OUT, K)
print('saved', OUT)
