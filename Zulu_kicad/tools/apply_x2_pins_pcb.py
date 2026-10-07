# KiCad copy: X2 power pins re-ordered (2026-10-07), board side. Every new value is taken from KiCad's own import of
# the corrected production Altium board (Zulu_Altium_VS_Code tools/X2PowerPins.pas):
#   X2-17 VCC3V3 -> GND, X2-18 VCC1V8 -> VCC3V3, X2-19 VCC1V0 -> VCC1V8, X2-20 GND -> VCC1V0;
#   the VCC1V8 In2 (L3) stub moves from pin 18 to pin 19; the VCC1V0 Bottom run is extended to pin 20 and its stub
#   moves there; the GND (In1) and VCC3V3 (In4) zone fills are replaced by the imported fills (no refill, see
#   CONVERSION.md). Guards: every object must be in its pre-change state, so a rerun stops.
#   python -u tools/apply_x2_pins_pcb.py kicad_project/zulu_a7.kicad_pcb <production zulu_a7.PcbDoc> <out.kicad_pcb>
import pcbnew, wx, sys
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
BOARD, ALTIUM, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
F = pcbnew.FromMM; X0, Y0 = 113.5761, 117.7036
def kpt(x, y): return pcbnew.VECTOR2I(F(x + X0), F(Y0 - y))
def nr(p, q): return abs(p.x - q.x) <= 2000 and abs(p.y - q.y) <= 2000
K = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD)
N = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER, ALTIUM)
n = 0
# 1. pad nets, from the import
OLD = {'17': 'VCC3V3', '18': 'VCC1V8', '19': 'VCC1V0', '20': 'GND'}
kx, nx = K.FindFootprintByReference('X2'), N.FindFootprintByReference('X2')
for num, was in OLD.items():
    kp = [p for p in kx.Pads() if p.GetNumber() == num][0]; np_ = [p for p in nx.Pads() if p.GetNumber() == num][0]
    assert kp.GetNetname() == was, (num, kp.GetNetname())
    assert kp.GetPosition() == np_.GetPosition()
    net = K.FindNet(np_.GetNetname()); assert net is not None, np_.GetNetname()
    kp.SetNet(net); n += 1
# the footprint's NOTE field carries the pin map (schematic parity compares it)
t = kx.GetFieldText('NOTE')
for a, b in (('pins 10-20 (26.67..1.27) = CHAN7..CHAN13, +3.3V, +1.8V, +1.0V, GND, in channel order since 2026-09-09;',
              'pins 10-20 (26.67..1.27) = CHAN7..CHAN13, GND, +3.3V, +1.8V, +1.0V (channel order since 2026-09-09, '
              'power pins re-ordered 2026-10-07);'),
             ('Three grounds (1, 20, 21); 3.3 V for the header is pin 17 alone;',
              'Three grounds (1, 17, 21); 3.3 V for the header is pin 18 alone;')):
    assert t.count(a) == 1, a[:40]; t = t.replace(a, b)
kx.SetField('NOTE', t); assert kx.GetFieldText('NOTE') == t; n += 1
# 2. VCC1V8 (In2) and VCC1V0 (B_Cu) tracks, from the import
TRK = [t for t in K.Tracks() if t.GetClass() == 'PCB_TRACK']
NT = [t for t in N.Tracks() if t.GetClass() == 'PCB_TRACK']
def find(pool, net, layer, a, b):
    h = [t for t in pool if t.GetNetname() == net and t.GetLayer() == layer and
         ((nr(t.GetStart(), kpt(*a)) and nr(t.GetEnd(), kpt(*b))) or (nr(t.GetStart(), kpt(*b)) and nr(t.GetEnd(), kpt(*a))))]
    assert len(h) == 1, (net, layer, a, b, len(h)); return h[0]
L3, B = pcbnew.In2_Cu, pcbnew.B_Cu
for net, layer, old, new in (('VCC1V8', L3, ((6.35, 23.05), (6.35, 24.13)), ((3.81, 23.05), (3.81, 24.13))),
                             ('VCC1V0', B, ((3.81, 23.05), (3.81, 24.13)), ((1.27, 23.05), (1.27, 24.13))),
                             ('VCC1V0', B, ((3.81, 23.05), (15.30, 23.05)), ((1.27, 23.05), (15.30, 23.05)))):
    t = find(TRK, net, layer, *old); r = find(NT, net, layer, *new)
    t.SetStart(r.GetStart()); t.SetEnd(r.GetEnd()); n += 1
# 3. plane fills, from the import
for net, layer in (('GND', pcbnew.In1_Cu), ('VCC3V3', pcbnew.In4_Cu)):
    kz = [z for z in K.Zones() if z.GetNetname() == net][0]; nz = [z for z in N.Zones() if z.GetNetname() == net][0]
    assert kz.Outline().Area() == nz.Outline().Area()
    kz.SetFilledPolysList(layer, pcbnew.SHAPE_POLY_SET(nz.GetFilledPolysList(layer))); kz.SetIsFilled(True); n += 1
print('changes applied:', n)
pcbnew.SaveBoard(OUT, K)
print('saved', OUT)
