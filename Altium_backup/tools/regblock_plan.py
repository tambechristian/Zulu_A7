# -*- coding: utf-8 -*-
"""Zulu A7 regulator/charger block: re-placement and its local loop copper (2026-09-15, power feeds).

Writes tools/regblock_placement.json and tools/regblock_route.json.   python tools/regblock_plan.py
Checked by tools/block_place.py (see docs/regulator_block.md for the five gates and the record).

Chosen by a judge from three strategies (row / column / exits), each attacked by a power-integrity
and a manufacturing/routability reviewer; this is "exits" with the judge's repairs R1-R7, plus
R8 (2026-09-15, main session): the LD3_K / LD4_K cathode escapes inside the EN2 ring are placed
NOW -- the judge found those two pockets routable only one net at a time and order-dependent.

Base: blk_exits/gen.py (pinwheel of three SC189 cells round one VU node, bq24232 cell south-east).
Repairs made here, each for a verified review finding (see the judge's verdict):
  R1  COUT pads sat 0.002 mm from the SOT23-5 MAXIMUM body (assembly collision at tolerance):
      every COUT moved 0.20 mm outward (COUT805 2.50, COUT603 2.25); U6's 4th GND via, now under
      X3's Top G2 pad, moves beyond the outer end of C82's GND pad.
  R2  L3's pads and body ran 0.06-0.13 mm under U3's moulded TSOP-II body (x >= 17.175 at max D,
      y 6.705-16.995): N and E cells moved 0.30 mm west (s 1.00 -> 0.70, U7 EN column XE 9.05 -> 8.75).
  R3  bq24232 VSS (pin 8) reached ground only through the thermal pad (SLUS821J pin table: "Do not
      use the thermal pad as the primary ground input ... VSS must be connected to ground"): C78 is
      turned (GND pad west over the pin 8/9 corner, VU pad over OUT 10/11) and pin 8 runs 0.50 mm
      Bottom copper straight to C78 GND with its own plane via on the way.
  R4  the 0.14 mm GND spoke through the IN(13)/ILIM(12) corner (0.093 mm to the USB 5 V pin) is gone.
      C150 GND gets two plane vias of its own; its copper join to the U8 GND island (the gate asks
      for direct copper) is a 0.30 mm L4-SIG GND jumper between its west via and C78's GND via.
  R5  ILIM (NetR103_2) ran under C78's body and 0.10 mm from the OUT pin-11 toe: with C78 turned it
      leaves pin 12 north-east, clear of C78, to R103 re-seated at (12.80, 10.10), GND pad east and
      tied by copper to C150's GND pad -- which also clears U7's maximum body (it was 0.037 mm).
  R6  thermal pad: a GND via in the SW package corner on pin 4 (land 0.55 mm from the pad edge),
      the pin 8 via and C78's via -- nearest plane via to U8-17 was 1.99 mm.
  R7  U8 pin tracks necked to the 0.24 mm pin width for their first ~0.35 mm (exposed-copper gaps
      between VBATT/GND, VU/GND at 0.5 mm pitch restored); C151 GND vias pulled off the pad edge;
      SC189 EN stubs 0.25 -> 0.20 (0.115 -> 0.14 mm from the CIN GND pads).
"""
import io, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = HERE
sys.path.insert(0, TOOLS)
import block_place as bp
import route_emit as rem

# The moves are relative to the board BEFORE placement.  PlaceRegBlock was run and saved on
# 2026-09-15, so tools/route_inputs.json now describes the moved board; re-running needs the
# pre-placement inputs:  git show 328a55e:Zulu_Altrium/tools/route_inputs.json > PRE.json
#                        python tools/regblock_plan.py --inputs PRE.json
_ri = sys.argv[sys.argv.index('--inputs') + 1] if '--inputs' in sys.argv else os.path.join(TOOLS, 'route_inputs.json')
inp = json.load(io.open(_ri, encoding='utf-8'))
_u5 = [p for p in inp['bottom_pads'] if p['ref'] == 'U5' and p['pad'] == '1'][0]
if abs(_u5['x'] - 1.5) > 1e-3 or abs(_u5['y'] - 7.0499) > 1e-3:
    sys.exit('regblock_plan.py: %s is not the pre-placement board (U5-1 at %.4f, %.4f); pass --inputs '
             'with tools/route_inputs.json from commit 328a55e' % (_ri, _u5['x'], _u5['y']))
M = 0.0015          # land-gap margin over 0.30 (saved pad centres are not on a clean grid)


class Frame:
    def __init__(self, ox, oy, rot):
        self.ox, self.oy, self.rot = ox, oy, rot % 360

    def pt(self, x, y):
        dx, dy = bp.rot_vec(x, y, self.rot)
        return (round(self.ox + dx, 4), round(self.oy + dy, 4))


moves = []


def place(ref, fr, prot, pad, lx, ly):
    gx, gy = fr.pt(lx, ly)
    moves.append(dict(ref=ref, rot=(prot + fr.rot) % 360, pad=str(pad), x=gx, y=gy))


# ------------------------------------------------------------------ placement: SC189 cells
CIN_Y = 1.60 + M          # CIN pad centres above the 1-2-3 row
L_Y = -4.50 - M
COUT_OUT = 0.20           # R1: COUT clear of the SOT23-5 maximum body
COUT805 = (2.30 + COUT_OUT + M, -0.70)
COUT603 = (2.05 + COUT_OUT + M, -0.80)


def sc189_cell(ic, L, cin, cout, big, fr):
    place(ic, fr, 0, '2', 0.0, 0.0)
    place(L, fr, 0, '1', -1.175, L_Y)
    place(cin, fr, 180, '1', 0.06, CIN_Y)
    cx, cy = COUT805 if big else COUT603
    place(cout, fr, 270, '1', cx, cy)


X, s, Y, t = 8.30, 0.70, 11.0, 0.6      # R2: s 1.00 -> 0.70 moves the N and E cells 0.30 west
W = Frame(X - 2.35 + 0.004, Y + t - 2.29, 270)
N = Frame(X + s - 2.29 - 0.302, Y + t + 2.35 + 0.302, 180)
E = Frame(X + s + 2.35, Y + 2.29, 90)
sc189_cell('U6', 'L2', 'C148', 'C82', False, W)
sc189_cell('U5', 'L1', 'C147', 'C80', True, N)
sc189_cell('U7', 'L3', 'C149', 'C84', False, E)

# ------------------------------------------------------------------ placement: bq24232 cell
EX, EY = 11.50, 5.90
U = Frame(EX, EY, 0)              # U8 frame: final orientation, EP centre at the origin
place('U8', U, 90, '17', 0, 0)
place('C78', U, 0, '1', -1.70, 2.75 + M)           # R3: GND pad west over the VSS/CHG corner, VU pad over OUT 10/11
place('C150', U, 270, '1', 2.50 + M, 2.80)         # IN pad south beside pin 13, GND pad north
place('C151', U, 0, '1', -1.70, -2.50 - M)         # BAT pad over pins 2/3, GND pad west
place('R103', Frame(0, 0, 0), 180, '2', 12.80, 10.10)  # R5: ILIM north-east of C78 (GND pad east), clear of U7's body
place('R104', U, 180, '2', 3.65 + 2 * M, 0.85 + M)  # TMR, east of C150's IN pad
place('R105', U, 180, '2', 2.35 + M, -0.35)        # ITERM, beside pins 14-16
place('R102', U, 180, '2', 2.35 + M, -1.55 - M)    # ISET, under R105
place('R106', U, 180, '2', 1.20 + M, -2.75 - 2 * M)  # TS, under pin 1
# LED resistors south-west of the node, on the VU ring
RY = 6.45
place('R107', Frame(0, 0, 0), 90, '2', 7.85, RY)   # VU pad north
place('R108', Frame(0, 0, 0), 90, '2', 6.50, RY)
place('R78', Frame(0, 0, 0), 0, '1', 6.20, 3.90)     # GND pad west

placement = dict(moves=moves,
                 roles={'U5': dict(l='L1', cin='C147', cout='C80'), 'U6': dict(l='L2', cin='C148', cout='C82'),
                        'U7': dict(l='L3', cin='C149', cout='C84'), 'U8': dict(cin='C150', cout='C78', cbat='C151')},
                 net_fixes=[dict(ref='R78', pad='1', net='GND')],
                 # 2026-09-15 DRC after placement: U5's designator lands on L1-1 (Silk To Solder Mask)
                 hide_designators=['U5'])
moved, probs = bp.apply_moves(inp, placement)
probs += bp.legality(inp, moved, placement)
PADS = {(p['ref'], p['pad']): p for p in moved['bottom_pads']}


def P(ref, pad):
    p = PADS[(ref, str(pad))]
    return (p['x'], p['y'])


# ------------------------------------------------------------------ copper
tracks, vias = [], []


def T(net, pts, w, layer='Bottom'):
    pts = [tuple(round(v, 4) for v in q) for q in pts]
    for a, b in zip(pts, pts[1:]):
        if a != b:
            tracks.append(dict(net=net, layer=layer, x1=a[0], y1=a[1], x2=b[0], y2=b[1], width=w))


def V(net, q):
    vias.append(dict(net=net, x=round(q[0], 4), y=round(q[1], 4)))
    return (round(q[0], 4), round(q[1], 4))


def top_ok(q):
    """a via at q keeps 0.09 from every Top pad and keep-out fill (and Bottom pads)"""
    for pl in (moved['top_pads'], moved['bottom_pads'], moved['th_pads']):
        for p in pl:
            if rem.pt_rect(q[0], q[1], p['x'], p['y'], p['sx'], p['sy']) - 0.175 < 0.09 + 1e-6:
                return False
    for k in moved['keepouts']:
        if rem.pt_rect(q[0], q[1], (k['x0'] + k['x1']) / 2, (k['y0'] + k['y1']) / 2, k['x1'] - k['x0'], k['y1'] - k['y0']) - 0.175 < 0.09 + 1e-6:
            return False
    return True


RAIL_W = {'VCC3V3': 1.0, 'VCC1V8': 0.8, 'VCC1V0': 1.0}


def sc189_copper(ic, L, cin, cout, big, fr, nvia=3):
    rail = PADS[(ic, '4')]['net']
    sw = PADS[(ic, '5')]['net']
    # LX: pin 5 straight to the inductor pad
    T(sw, [P(ic, 5), P(L, 1)], 0.80)
    # hot loop: VIN -> CIN VU, GND -> CIN GND
    T('VU', [P(ic, 1), P(cin, 2)], 0.80)
    T('GND', [P(ic, 2), P(cin, 1)], 0.50)
    # output: L out -> COUT out, sense pin 4 -> COUT out
    T(rail, [P(L, 2), P(cout, 2)], RAIL_W[rail])
    T(rail, [P(ic, 4), P(cout, 2)], 0.40)
    # GND channel under the body: pin 2 -> vias -> COUT GND
    cx = (COUT805 if big else COUT603)[0]
    cand = [0.0, 0.44, -0.44, 0.88, -0.88, 1.10, -1.30]
    got = []
    for lx in cand:
        q = fr.pt(lx, -1.25)
        if top_ok(q) and all(abs(lx - g) >= 0.44 - 1e-9 for g in got):
            got.append(lx)
        if len(got) >= nvia:
            break
    xs = sorted(set(got + [0.0]))
    pts = [fr.pt(x, -1.25) for x in xs] + [fr.pt(cx, -1.25)]
    T('GND', pts, 0.50)
    T('GND', [fr.pt(cx, -1.25), P(cout, 1)], 0.50)
    T('GND', [P(ic, 2), fr.pt(0.0, -1.25)], 0.50)
    for x in got:
        V('GND', fr.pt(x, -1.25))
    # one more beside the COUT GND pad, past the EN pin (or beyond the pad's outer end when a Top
    # X3 pad is over that spot -- U6 after R1)
    for lq in ((cx, 0.30), (cx + 1.28, -0.50)):
        q = fr.pt(*lq)
        if top_ok(q):
            V('GND', q)
            T('GND', [P(cout, 1), q], 0.40)
            got = got + ['cout']
            break
    return got


gv = {}
gv['U6'] = sc189_copper('U6', 'L2', 'C148', 'C82', False, W)
gv['U5'] = sc189_copper('U5', 'L1', 'C147', 'C80', True, N)
gv['U7'] = sc189_copper('U7', 'L3', 'C149', 'C84', False, E)

# ---- VU: U8's EN2 ring runs west of U8 at x SPX, picks up R107/R108 and U6's EN, and meets the
#      node A where C78 (1.0 mm) and the three CIN VU pads (0.8-1.0 mm) join
u5 = U.pt(-2.90, -0.75)            # ring corner west of U8 pin 5
SPX = u5[0]
c78vu = P('C78', 2)
w_en = P('U6', 3)
S1 = (SPX, w_en[1])
RV = (SPX, P('R107', 2)[1])
T('VU', [P('U8', 5), (P('U8', 5)[0] - 0.60, P('U8', 5)[1])], 0.24)          # R7 neck at the EN2 toe
T('VU', [(P('U8', 5)[0] - 0.60, P('U8', 5)[1]), u5], 0.30)
T('VU', [u5, RV], 0.30)
T('VU', [RV, S1], 0.30)
A = (10.25, 10.50)                 # the VU node (moved with R2/R3)
AY0 = 10.05
B = (SPX, P('C148', 2)[1])
T('VU', [S1, B], 0.30)
T('VU', [c78vu, (c78vu[0], AY0), A], 1.00)
T('VU', [A, P('C149', 2)], 1.00)
T('VU', [A, B, P('C148', 2)], 0.80)
T('VU', [A, P('C147', 2)], 0.80)
XE = 9.05 - 0.30
# EN pins
T('VU', [w_en, S1], 0.20)
n3 = P('U5', 3)
YN = 11.65
T('VU', [n3, (n3[0], YN), (P('C148', 2)[0], YN), P('C148', 2)], 0.20)
e3 = P('U7', 3)
T('VU', [e3, (XE, e3[1]), (XE, P('C149', 2)[1]), P('C149', 2)], 0.20)
# LED pull-up resistors on the ring
T('VU', [RV, P('R107', 2), P('R108', 2)], 0.30)

# ---- U8 cell
ep = P('U8', 17)
# OUT pins 10/11 -> C78 VU (pad centred over the two pins)
mid = (round((P('U8', 10)[0] + P('U8', 11)[0]) / 2, 4), P('U8', 10)[1])
T('VU', [P('U8', 10), mid, P('U8', 11)], 0.24)
T('VU', [mid, c78vu], 0.50)
# BAT pins 2/3 -> C151 BAT, necked to the pin width to just above the cap pad
yb = round(P('C151', 2)[1] + 0.55, 4)
T('VBATT', [P('U8', 2), (P('U8', 2)[0], yb)], 0.24)
T('VBATT', [(P('U8', 2)[0], yb), P('C151', 2)], 0.40)
T('VBATT', [P('U8', 3), (P('U8', 3)[0], yb)], 0.24)
T('VBATT', [(P('U8', 3)[0], yb), P('C151', 2)], 0.40)
# IN pin 13 -> C150 IN
xi = round(P('U8', 13)[0] + 0.55, 4)
T('USB5V0', [P('U8', 13), (xi, P('U8', 13)[1])], 0.24)
T('USB5V0', [(xi, P('U8', 13)[1]), P('C150', 2)], 0.40)
# GND straps under the package: pins 4, 6, 8 into the thermal pad (pin-width necks, 0.40 inside the pad)
J4 = U.pt(-0.75, -0.25)
J8 = U.pt(-0.75, 0.75)
p4, p6 = P('U8', 4), P('U8', 6)
T('GND', [p4, (p4[0], 4.95)], 0.24)
T('GND', [(p4[0], 4.95), J4], 0.40)
T('GND', [p6, (10.45, p6[1])], 0.24)
T('GND', [(10.45, p6[1]), J4], 0.40)
T('GND', [J4, ep], 0.40)
T('GND', [P('U8', 8), (10.45, P('U8', 8)[1])], 0.24)
T('GND', [(10.45, P('U8', 8)[1]), J8, ep], 0.40)
# R3: VSS pin 8 -> west -> north -> C78 GND pad, with a plane via on the way
p8 = P('U8', 8)
K8 = (9.50, p8[1])
V8 = V('GND', (9.50, 7.35))
c78g = P('C78', 1)
T('GND', [p8, K8], 0.24)
T('GND', [K8, V8, (9.50, c78g[1]), c78g], 0.50)
VC78 = V('GND', (c78g[0], 9.70))
T('GND', [c78g, VC78], 0.40)
# R6: SW package-corner via on pin 4, then on to C151 GND and its vias
VSW = V('GND', (10.15, 4.55))
T('GND', [P('U8', 4), VSW], 0.30)
T('GND', [VSW, P('C151', 1)], 0.40)
for q in ((9.80, 2.58), (8.92, 3.10), (8.92, 3.75)):
    V('GND', q)
    T('GND', [P('C151', 1), q], 0.40)
# R4: C150 GND -- two plane vias, and the L4 jumper to C78's GND via
c150g = P('C150', 1)
VCW = V('GND', (12.98, 8.60))
VCE = V('GND', (15.30, 8.60))
T('GND', [c150g, VCW], 0.40)
T('GND', [c150g, VCE], 0.30)
T('GND', [VCW, VC78], 0.30, layer='L4-SIG')
# resistors
T('NetR103_2', [P('U8', 12), (12.25, 7.75), (12.55, 8.05), (12.55, 9.75), P('R103', 2)], 0.10)
T('NetR104_2', [P('U8', 14), (13.30, 6.22), (14.60, 6.22), P('R104', 2)], 0.10)
T('NetR105_2', [P('U8', 15), P('R105', 2)], 0.15)
T('NetR102_2', [P('U8', 16), U.pt(1.85, -1.00), P('R102', 2)], 0.10)
T('NetR106_2', [P('U8', 1), P('R106', 2)], 0.15)
# R103 GND straight onto C150's GND pad: the ILIM ground returns on the charger's own GND copper
T('GND', [P('R103', 1), c150g], 0.30)
for rr, dq in (('R104', (0.65, 0)), ('R105', (0.665, 0)), ('R102', (0.665, 0)), ('R106', (0.665, 0))):
    g = P(rr, 1)
    q = V('GND', (g[0] + dq[0], g[1] + dq[1]))
    T('GND', [g, q], 0.30)
g = P('R78', 1)
q = V('GND', (g[0] - 0.665, g[1]))
T('GND', [g, q], 0.30)

# R8: LED cathode escapes out of the EN2 ring, reserved now (sites checked with route_emit.check)
for pin, q in (('7', (9.10, 6.10)), ('9', (10.25, 7.35))):
    net = PADS[('U8', pin)]['net']
    T(net, [P('U8', pin), V(net, q)], 0.10)

plan = dict(vias=vias, tracks=tracks)
io.open(os.path.join(HERE, 'regblock_placement.json'), 'w', encoding='utf-8').write(json.dumps(placement, indent=1))
io.open(os.path.join(HERE, 'regblock_route.json'), 'w', encoding='utf-8').write(json.dumps(plan, indent=1))

# ------------------------------------------------------------------ self-check
if __name__ == '__main__':
    print('placement problems: %d' % len(probs))
    for p in probs[:40]:
        print('   ', p)
    pr = rem.check(moved, plan)
    print('plan problems: %d' % len(pr))
    for p in pr[:60]:
        print('   ', p)
    res = bp.loop_joins(moved, plan, placement['roles'])
    bad = [r for r in res if not r[0]]
    print('joins %d/%d' % (len(res) - len(bad), len(res)))
    for ok, net, why, labels in bad:
        print('   MISSING', net, why, labels)
    print('GND vias per SC189:', {k: len(v) for k, v in gv.items()})
    print('plan: %d vias, %d tracks' % (len(vias), len(tracks)))
