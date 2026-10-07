# KiCad copy: apply the X1 pad/clearance fix (2026-10-07), taking every new value from KiCad's own import of the
# corrected production Altium board. Guards: every object must match its post-slot-fix state, so a rerun stops.
import pcbnew, wx, sys, os
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
BOARD, ALTIUM, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F = pcbnew.FromMM; X0, Y0 = 113.5761, 117.7036
def kpt(x, y): return pcbnew.VECTOR2I(F(x + X0), F(Y0 - y))
def nr(p, q): return abs(p.x - q.x) <= 2000 and abs(p.y - q.y) <= 2000
K = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD)
N = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER, ALTIUM)
CU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)
n = 0
# 1. MS1/MS2 lands: copy padstack mode, per-layer shape and size from the import
kx, nx = K.FindFootprintByReference('X1'), N.FindFootprintByReference('X1')
for name in ('MS1', 'MS2'):
    kp = [p for p in kx.Pads() if p.GetNumber() == name][0]; np_ = [p for p in nx.Pads() if p.GetNumber() == name][0]
    assert kp.GetDrillShape() == pcbnew.PAD_DRILL_SHAPE_OBLONG and abs(kp.GetSize(pcbnew.B_Cu).y - F(0.89992)) < 2000, name
    assert kp.GetPosition() == np_.GetPosition() and kp.GetDrillSize() == np_.GetDrillSize()
    kp.Padstack().SetMode(np_.Padstack().Mode())
    for l in CU:
        kp.SetShape(l, np_.GetShape(l)); kp.SetSize(l, np_.GetSize(l))
    n += 1
# 2. CHAN12: tracks
TRK = [t for t in K.Tracks()]
def take(layer, a, b):
    h = [t for t in TRK if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'CHAN12' and t.GetLayer() == layer and
         ((nr(t.GetStart(), kpt(*a)) and nr(t.GetEnd(), kpt(*b))) or (nr(t.GetStart(), kpt(*b)) and nr(t.GetEnd(), kpt(*a))))]
    assert len(h) == 1, (layer, a, b, len(h)); return h[0]
B, L4 = pcbnew.B_Cu, pcbnew.In3_Cu
old = [take(B, (16.25, 23.15), (35.80, 23.15)), take(B, (35.80, 23.15), (35.80, 23.35)),
       take(L4, (35.80, 23.35), (36.25, 23.15)), take(L4, (36.25, 23.15), (46.45, 23.15))]
new = [(B, (16.25, 23.15), (27.95, 23.15)), (B, (27.95, 23.15), (28.72, 23.92)),
       (L4, (37.45, 24.40), (37.45, 23.15)), (L4, (37.45, 23.15), (46.45, 23.15))]
extra = [(B, (28.72, 23.92), (28.72, 24.62)), (B, (28.72, 24.62), (29.12, 25.02)),
         (B, (29.12, 25.02), (36.83, 25.02)), (B, (36.83, 25.02), (37.45, 24.40))]
NT = [t for t in N.Tracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetname() == 'CHAN12']
def ref(layer, a, b):
    h = [t for t in NT if t.GetLayer() == layer and ((nr(t.GetStart(), kpt(*a)) and nr(t.GetEnd(), kpt(*b))) or (nr(t.GetStart(), kpt(*b)) and nr(t.GetEnd(), kpt(*a))))]
    assert len(h) == 1, ('not in import', layer, a, b); return h[0]
for t, (layer, a, b) in zip(old, new):
    r = ref(layer, a, b); t.SetStart(r.GetStart()); t.SetEnd(r.GetEnd()); n += 1
for layer, a, b in extra:
    r = ref(layer, a, b); t = pcbnew.PCB_TRACK(K)
    t.SetStart(r.GetStart()); t.SetEnd(r.GetEnd()); t.SetWidth(r.GetWidth()); t.SetLayer(layer); t.SetNet(old[0].GetNet()); K.Add(t); n += 1
# 3. CHAN12 vias
kv = [v for v in TRK if v.GetClass() == 'PCB_VIA' and v.GetNetname() == 'CHAN12' and nr(v.GetPosition(), kpt(35.80, 23.35))]
nv = [v for v in N.Tracks() if v.GetClass() == 'PCB_VIA' and v.GetNetname() == 'CHAN12' and nr(v.GetPosition(), kpt(37.45, 24.40))]
assert len(kv) == 2 and len(nv) == 2
for v in kv: v.SetPosition(nv[0].GetPosition()); n += 1
# 4. plane fills
for net, layer in (('GND', pcbnew.In1_Cu), ('VCC3V3', pcbnew.In4_Cu)):
    kz = [z for z in K.Zones() if z.GetNetname() == net][0]; nz = [z for z in N.Zones() if z.GetNetname() == net][0]
    assert kz.Outline().Area() == nz.Outline().Area()
    kz.SetFilledPolysList(layer, pcbnew.SHAPE_POLY_SET(nz.GetFilledPolysList(layer))); kz.SetIsFilled(True); n += 1
print('changes applied:', n)
pcbnew.SaveBoard(OUT, K)
print('saved', OUT)
