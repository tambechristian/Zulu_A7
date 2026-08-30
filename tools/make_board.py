# -*- coding: utf-8 -*-
"""Generate zulu_a7.brd from zulu_a7.sch, placed to the board plan.

    python tools/make_board.py [--fab jlcpcb|pcbway]

WHAT THIS PRODUCES. A complete, placed, UNROUTED board: the 2.750 x 1.000 in
outline on layer 20, a six-layer stack, the chosen fab's design rules loaded, an
element for every part that has a package, and a signal for every net with a
contactref for every pad. Opening it in Eagle or Fusion should show a
consistent board with a full ratsnest and nothing routed.

TWO FABS. --fab jlcpcb (the default) writes the root pair at a 0.225 mm ball
land; --fab pcbway writes board/pcbway/ at the same 0.225 -- PCBWay confirmed an
8 mil BGA pad on 2026-08-27, so both fabs take the same footprint and the two
boards now differ ONLY in the rules file. See the FABS table below and
board/STACKUP.md.

It also lifts the footprint provenance notes off the board. Three ctambe
packages carry prose on layer 51; left in the package it travels with the
element, and X1's and U8's landed inside the outline. They are stripped from the
board's copy of each package and re-emitted once, above the outline, where
nothing else lives. The schematic library keeps the originals.

It is a forward annotation done in Python rather than by clicking "Switch to
Board", and the reason to do it that way is that the placement from
tools/board_plan.py comes with it. Eagle would drop all 167 elements in a heap
outside the outline; this puts the fourteen blocks that were planned where they
were planned, and parks the rest in a tidy grid below the board.

WHAT IT DOES NOT DO. No traces, no vias, no polygons, no ground pour. The BGA
escape described in board/STACKUP.md is still yours to draw. Nor does this
place the ~110 remaining passives -- they are parked, not positioned, because
where a decoupling capacitor goes is a routing decision, not a plan decision.

CONSISTENCY. Eagle decides a board and schematic agree by comparing parts to
elements and nets to signals, so those two mappings are what the checks at the
bottom verify exhaustively: every part with a package has exactly one element
of the right package, every part without one has none, and every net's set of
(element, pad) pairs matches what the deviceset's <connect> entries say it
should be -- including the pins that map to several pads, like the microSD's
shield tabs and the USB shell.
"""

import re, io, os, sys, shutil, collections

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SRC = os.path.join(ROOT, "zulu_a7.sch")          # the one schematic, for both fabs

# --- the two fabs -----------------------------------------------------------
# One schematic, two boards. The nets are identical; what differs is the BGA
# land diameter and the design rules, and the land is the whole argument -- see
# board/STACKUP.md, "What the research found". The solder mask opening is NOT
# set here: it falls out of the .dru's mlMinStopFrame of 0.05 mm, so a 0.225
# land gets a 0.325 opening and a 0.275 land gets UG475's 0.375 by itself.
FABS = {
    "jlcpcb": dict(
        dru="zulu_a7-6layer-jlcpcb.dru", land=0.225, out=ROOT,
        why="active. 3 mil trace at 3.5 mil clearance clears the 0.275 gap by 0.0188"),
    # PCBWay answered on 2026-08-27: 8 mil BGA pad, 0.4 mm pitch, 0.5 oz or 1 oz
    # outer, HDI ruled out on cost. So this is Plan A, conventional through-hole,
    # and the land is the same 0.225 as JLCPCB -- 0.275 is gone, because at 0.275
    # the gap between lands is 0.225 mm and their finest rigid geometry needs
    # 0.2667. The two boards now differ ONLY in the rules file.
    "pcbway": dict(
        dru="zulu_a7-6layer-pcbway.dru", land=0.225, out=os.path.join(ROOT, "board", "pcbway"),
        why="Plan A, conventional through-hole. 8 mil BGA pad confirmed, HDI ruled "
            "out on cost; the escape line/space is still unconfirmed"),
}
FAB = "jlcpcb"
for a in sys.argv[1:]:
    if a.startswith("--fab="):
        FAB = a.split("=", 1)[1]
    elif a == "--fab":
        FAB = sys.argv[sys.argv.index(a) + 1]
if FAB not in FABS:
    sys.exit("usage: make_board.py [--fab %s]" % "|".join(sorted(FABS)))
CFG = FABS[FAB]
DRU = os.path.join(ROOT, "board", CFG["dru"])
SCH = os.path.join(CFG["out"], "zulu_a7.sch")
BRD = os.path.join(CFG["out"], "zulu_a7.brd")
if not os.path.isdir(CFG["out"]):
    os.makedirs(CFG["out"])
print("fab: %s -- %s" % (FAB, CFG["why"]))
print("     land %.3f mm, rules board/%s, output %s"
      % (CFG["land"], CFG["dru"], os.path.relpath(CFG["out"], ROOT)))

BGA = "XC7A35T-CPG236"


def set_land(text, land):
    """Resize every ball land in the CPG236 package, and nowhere else.

    Scoped to the one package on purpose: the schematic still carries the old
    Spartan-6 FT256 footprint, whose 1.0 mm pitch balls are 0.4 mm and must not
    move. Asserts the count, because a silent zero here would ship the wrong
    land to the fab.
    """
    m = re.search(r'<package name="%s">.*?</package>' % BGA, text, re.S)
    assert m, "no %s package in this file" % BGA
    body, n = re.subn(r'(<smd name="[^"]+" x="[^"]*" y="[^"]*" )dx="[^"]*" dy="[^"]*"',
                      r'\g<1>dx="%s" dy="%s"' % (land, land), m.group(0))
    assert n == 238, "expected 238 ball lands in %s, rewrote %d" % (BGA, n)
    return text[:m.start()] + body + text[m.end():], n


t = open(SRC, encoding="utf-8").read()
t, _n = set_land(t, ("%.4f" % CFG["land"]).rstrip("0").rstrip("."))
open(SCH, "w", encoding="utf-8").write(t)
old = open(BRD, encoding="utf-8").read() if os.path.exists(BRD) else \
    open(os.path.join(ROOT, "zulu_a7.brd"), encoding="utf-8").read()


def g(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# --- model from the schematic ----------------------------------------------
LIBSRC = {m.group(1): m.group(2) for m in re.finditer(r'<library name="([^"]+)">(.*?)</library>', t, re.S)}
PKGSRC = {}
for lib, body in LIBSRC.items():
    pm = re.search(r"<packages>(.*?)</packages>", body, re.S)
    if pm:
        for p in re.finditer(r'<package name="([^"]+)">.*?</package>', pm.group(1), re.S):
            PKGSRC[(lib, p.group(1))] = p.group(0)
DEV = {}
for lib, body in LIBSRC.items():
    for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', body, re.S):
        for dv in re.finditer(r'<device name="([^"]*)"(?: package="([^"]+)")?>(.*?)</device>', dm.group(2), re.S):
            DEV[(lib, dm.group(1), dv.group(1))] = (
                dv.group(2), {(gt, pn): pd.split() for gt, pn, pd in
                              re.findall(r'<connect gate="([^"]+)" pin="([^"]+)" pad="([^"]+)"/>', dv.group(3))})
PARTS = collections.OrderedDict()
for m in re.finditer(r'<part name="([^"]+)" library="([^"]+)" deviceset="([^"]+)" device="([^"]*)"([^>]*)>', t):
    val = (re.search(r'value="([^"]*)"', m.group(5)) or [None, ""])[1]
    PARTS[m.group(1)] = (m.group(2), m.group(3), m.group(4), val)
NETS = collections.OrderedDict()
NETCLASS = {}
# ANY CLASS, NOT JUST ZERO. This read `class="0"` literally, so the moment a net
# was given a class -- which is the only way Eagle can be told two nets are a
# differential pair with a gap -- make_board stopped seeing that net and it
# vanished from the board entirely. Silently: the signal simply was not emitted.
for m in re.finditer(r'<net name="([^"]+)" class="(\d+)">(.*?)</net>', t, re.S):
    NETS.setdefault(m.group(1), set()).update(
        re.findall(r'<pinref part="([^"]+)" gate="([^"]+)" pin="([^"]+)"/>', m.group(3)))
    NETCLASS[m.group(1)] = m.group(2)
# the schematic's own class table, carried across rather than re-invented here
CLASSES = re.search(r"<classes>(.*?)</classes>", t, re.S).group(1).strip()
PLACEABLE = [p for p, (l, d, dv, v) in PARTS.items() if DEV.get((l, d, dv), (None,))[0]]


def pkg_of(p):
    l, d, dv, _v = PARTS[p]
    return DEV[(l, d, dv)][0]


def bbox(lib, pk):
    src = PKGSRC[(lib, pk)]
    xs, ys = [], []
    for m in re.finditer(r'<smd name="[^"]*" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', src):
        x, y, dx, dy = map(float, m.groups()); xs += [x - dx / 2, x + dx / 2]; ys += [y - dy / 2, y + dy / 2]
    for m in re.finditer(r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', src):
        x, y, d = map(float, m.groups()); r = d / 2 + 0.254; xs += [x - r, x + r]; ys += [y - r, y + r]
    for m in re.finditer(r"<(?:wire|rectangle) ([^>]*)/>", src):
        if re.search(r'layer="(?:21|51)"', m.group(1)):
            xs += [float(v) for v in re.findall(r'\bx[12]="([-\d.]+)"', m.group(1))]
            ys += [float(v) for v in re.findall(r'\by[12]="([-\d.]+)"', m.group(1))]
    xs, ys = _round_bits(src, xs, ys)
    if not xs:
        for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"', src):
            x, y = map(float, m.groups()); xs += [x, x + 1.0]; ys += [y, y + 1.0]
    if not xs:
        xs, ys = [0.0, 1.0], [0.0, 1.0]
    return (min(xs), min(ys), max(xs), max(ys))


def _round_bits(src, xs, ys):
    """circles and polygons on 21/51 -- the shapes the wire scan cannot see.

    Silk is not always drawn with wires. A pin-1 dot is a <circle>, and several
    packages fill their outline with a <polygon>, and reading neither meant three
    real parts measured smaller than they are:

        DM3AT-SF-PEJM5   X3, microSD     15.95 -> 16.60 tall
        MOLEX-105017-0001 X1, USB         5.84 ->  6.34 tall
        LTC3569-QFN20    U8, regulator    3.50 ->  3.85 wide

    All three by a 0.15 mm pin-1 dot sitting just outside the body outline. A
    pin-1 dot exists to be looked at, so covering it with the next part along is
    a real defect even though it is only ink -- and the placer could not see it
    to avoid it.

    Of the 194 packages this changes 17, and the other 177 have their circles
    and polygons inside the outline already, so nothing moves for them.
    """
    for m in re.finditer(r'<circle x="([-\d.]+)" y="([-\d.]+)" radius="([\d.]+)"'
                         r' width="[\d.]+" layer="(?:21|51)"', src):
        x, y, r = map(float, m.groups()); xs += [x - r, x + r]; ys += [y - r, y + r]
    for pm in re.finditer(r'<polygon [^>]*layer="(?:21|51)"[^>]*>(.*?)</polygon>', src, re.S):
        for v in re.finditer(r'<vertex x="([-\d.]+)" y="([-\d.]+)"', pm.group(1)):
            xs.append(float(v.group(1))); ys.append(float(v.group(2)))
    return xs, ys


def obst_box(lib, pk):
    """like bbox(), but counting layer 39 keepouts as part of the body.

    bbox() ignores them on purpose -- it sizes a part for placement, and X3's
    keepout is the microSD card plus 21.55 mm of eject stroke, which is not how
    big X3 is. But when a part is an OBSTACLE, or is being placed against other
    obstacles, the keepout is exactly what has to be respected: an 0402
    resistor's layer-39 box is 0.473 mm wider than its copper on every side, and
    leaving it out walked twenty-eight parts into each other.
    """
    r = list(bbox(lib, pk))
    for tag in re.findall(r"<(?:wire|rectangle|circle|polygon)[^>]*>",
                          PKGSRC[(lib, pk)]):
        if 'layer="39"' not in tag:
            continue
        xs = [float(v) for v in re.findall(r'\sx\d*="([-\d.]+)"', tag)]
        ys = [float(v) for v in re.findall(r'\sy\d*="([-\d.]+)"', tag)]
        if not xs or not ys:
            continue
        r[0], r[2] = min(r[0], min(xs)), max(r[2], max(xs))
        r[1], r[3] = min(r[1], min(ys)), max(r[3], max(ys))
    return tuple(r)


# What a part actually claims when it is being placed. Two separate rules, and
# the box is the wider of the two ON EACH AXIS -- they do not bind on the same
# one.
#
#   courtyard   the layer-39 box, which already IS a clearance envelope, so it
#               only has to abut its neighbour, not stand off from it. This is
#               also the rule check_board.py enforces: its shape() unions layers
#               21/39/51 and asks that no two same-side bodies overlap.
#   copper      pad against pad, far enough apart that reflow cannot bridge two
#               different parts. Nothing in the courtyard guarantees this.
#
# tile() used to take the courtyard and add 0.35 mm around it, which is stricter
# than the checker on every side and double-counts. It matters because the stock
# rcl keepout is deliberately ANISOTROPIC: an 0402 carries 0.473 mm at the ends,
# where the terminations and the solder fillets are, and 0.033 mm at the sides,
# because chip parts are meant to be packed shoulder to shoulder in rows. Adding
# a uniform 0.35 turned that 0.033 into 0.416 mm of dead lane between every row.
# The two-rule box costs an 0402 3.60 mm2 where the old one cost 6.07 -- and it
# is the correct 2.996 x 1.200, near enough IPC-7351 density level N.
CY_GAP = 0.05                       # courtyards abut, with a hair for float ties
CU_GAP = 0.30                       # land to foreign land, vs 0.09 mm electrical


def pad_box(lib, pk):
    c, o = bbox(lib, pk), obst_box(lib, pk)
    return (min(o[0] - CY_GAP / 2, c[0] - CU_GAP / 2),
            min(o[1] - CY_GAP / 2, c[1] - CU_GAP / 2),
            max(o[2] + CY_GAP / 2, c[2] + CU_GAP / 2),
            max(o[3] + CY_GAP / 2, c[3] + CU_GAP / 2))


def rp(x, y, rot):
    r = re.sub(r"^M", "", rot)
    x, y = {"R0": (x, y), "R90": (-y, x), "R180": (-x, -y), "R270": (y, -x)}[r]
    return (-x, y) if rot.startswith("M") else (x, y)


def rbbox(bb, rot):
    pts = [rp(x, y, rot) for x in (bb[0], bb[2]) for y in (bb[1], bb[3])]
    return (min(p[0] for p in pts), min(p[1] for p in pts),
            max(p[0] for p in pts), max(p[1] for p in pts))


def shift(bb, dx, dy):
    return (bb[0] + dx, bb[1] + dy, bb[2] + dx, bb[3] + dy)


def origin_for(part, bx, by, rot):
    """element origin that lands the footprint's min corner on (bx, by)"""
    lib = PARTS[part][0]
    r = rbbox(bbox(lib, pkg_of(part)), rot)
    return bx - r[0], by - r[1]


# --- placement, from tools/board_plan.py ------------------------------------
BX1, BY1 = 69.85, 25.40
# The board went 0.800 in -> 1.000 in wide and kept its 2.750 in length. See
# board/STACKUP.md: at 0.800 the parts did not fit, 44 of them parked, and the
# escape's fan-out ring was pinned at half-width 6.20 by the decoupling that had
# nowhere else to go.
#
# THE PIN ROWS WIDENED WITH THE BOARD, 0.700 in -> 0.900 in, and stayed 0.050 in
# inside each edge exactly as they were at 0.800 in. They are in ZULU-DIP37 in
# the schematic, at y 1.27 and 24.13.
#
# Leaving them at 0.700 was the first attempt and it was wrong twice over. It put
# the rows 0.150 in inside the edges instead of 0.050, so the pins landed in
# breadboard columns d and i rather than c and j; and it split the interior into
# a 16.256 mm channel plus two 3.05 mm strips outside the rows instead of one
# 21.336 mm channel, which is less usable area AND fragmented.
#
#     pin span   channel   strips     usable/side   parked
#     0.700 in   16.256    2 x 3.05        1590        4
#     0.900 in   21.336    none            1529        2
#
# On a wide 6+6 breadboard the pins now sit in c and j and the board covers c
# through j, leaving a b | k l and both power rails patchable; on a standard 5+5
# it is b and i, covering b through i.
#
# The board grew 2.54 mm at each edge and the assembly stays centred in it. Every
# y in the tables below is written against the old 0.800 in outline -- and the
# comments explaining them cite those numbers -- so the offset is applied here
# rather than by rewriting forty coordinates and stranding their reasoning.
YOFF = (BY1 - 20.32) / 2.0


def yb(x0, y0, x1, y1, *rest):
    """a box written against the old outline, moved onto the new one"""
    return (x0, y0 + YOFF, x1, y1 + YOFF) + rest


PLACE = {}                                   # part -> (x, y, rot)

# The FPGA, per side. tile() picks whichever one matches the rotation it is
# laying parts at, so both have to exist before the first call.
#
# FRONT: the package and its escape corridors. The right-hand side needs
# half-width 6.24 and the other three need 4.85, so this covers the worst case
# plus a margin. What is already inside it -- the FPGA decoupling -- stays;
# tile() treats placed parts as obstacles.
NOFPGA = yb(40.00, 3.40, 53.00, 16.00)
# BACK: only the moat, because that is the only thing the escape leaves on L6.
# The ball field is x 42.000..51.000, y 5.200..14.200 about a centre of
# (46.500, 9.700); the outer via ring sits at half-width 3.1975 and a via land
# plus clearance reaches 3.4375, i.e. 43.062..49.938. Rounded out to 3.60 for
# the stage-3 vias that are not drawn yet. Everything outside it and inside the
# package outline is ordinary back-side copper and the best place on the board
# for a bypass capacitor -- shortest possible loop to the power balls.
NOVIA = yb(42.90, 6.10, 50.10, 13.30)
# ...and the ring stage 3 fans out to. That one is a THROUGH hole as well, so it
# has to clear back-side copper too, and escape.py's fanout_h() looks for the
# largest half-width in 4.90..6.20 where a whole ring still clears the board.
# Freeing the whole back of the package blocked every candidate: fanout_h
# returned None and stage 3 died with a TypeError, taking the write of stages 1
# and 2 with it. So reserve the ring itself, and reserve enough of it.
#
# HOW FAR OUT. The ring was pinned at half-width 6.20, and it was never the
# board that pinned it -- the edge allows 9.46 and X2's pad rows allow 7.43. It
# was the decoupling capacitors, sitting in the annulus the fan wants. That cap
# is what left stage 3 with a 1.20 mm band to fan 103 escapes through, and the
# fan angle is the whole of what remains wrong with it:
#
#     ring h      6.20  6.60  7.00  7.40  7.80  8.20
#     fan band    1.20  1.60  2.00  2.40  2.80  3.20
#     conflicts     28    16    11     6     6     6
#
# It plateaus at 6, so 7.40 is the whole prize; further out buys nothing and
# costs area. Reserve to 7.40 + VIA_L/2 + clr = 7.64.
#
# BOTH SIDES, because a via is a through hole. On the old 0.800 in board this
# reservation cost 18 more parked parts on top of the 44 already parked, which
# is why it was not made. At 1.000 in there is room for it.
_C, _I, _O = 46.50, 5.70, 7.64                   # ball-field centre, half-widths
RING = [yb(_C - _O, 9.70 - _O, _C - _I, 9.70 + _O),    # left
        yb(_C + _I, 9.70 - _O, _C + _O, 9.70 + _O),    # right
        yb(_C - _O, 9.70 - _O, _C + _O, 9.70 - _I),    # bottom
        yb(_C - _O, 9.70 + _I, _C + _O, 9.70 + _O)]    # top
# Front, left to right: microSD, BTN turned on its side, FT2232, FPGA, then the
# crystal and JTAG stacked at the far end. The FPGA moving right of the FT2232
# drags the whole back side with it -- see the two tile() calls below.
SINGLE = [# X3 must be R270, not R90. The DM3AT's layer-39 keepout runs 8.70 mm past
          # its copper on the slot side -- that is the card-withdrawal travel, and it
          # says which way the slot faces. At R90 it pointed +x, into the board and
          # straight through BTN, so the card could only have been inserted from the
          # middle of the board. R270 turns the slot to -x, off the near edge, which
          # is what board/STACKUP.md always described.
          ("X3", 0.60, 3.23, "R270"), ("BTN", 17.55, 5.83, "R90"),
          # U2 drops 0.12 mm. X1's rebuilt footprint carries Molex's recommended
          # courtyard on layer 39, and its rear edge landed 0.020 mm inside U2's
          # copper. Physically nothing, but it is a real courtyard and 0.12 mm
          # buys 0.10 of margin. U2 stays x-centred on X1 at 33.02.
          ("U2", 28.008, 4.568, "R0"), ("U1", 41.00, 4.20, "R0"),
          # X1 is NOT in this list -- see PLACE["X1"] below. It is placed by its
          # PCB EDGE line, not by its bounding box, because the shell overhangs.
          # Q1 sits 0.45 mm further from the FPGA than the pocket's centre, and
          # that 0.45 is the fan-out ring's. Its nearest copper was at chebyshev
          # 7.19 from the ball-field centre and the ring's outer edge reaches
          # h + VIA_L/2 + clr, so Q1 alone capped the ring at 6.94. At 54.04 its
          # copper starts at 7.64 and the ring can go to 7.40, which the measured
          # curve puts at 6 stage-3 conflicts against 11 at 6.94.
          ("Q1", 54.04, 8.26, "R0"),
          # JP3 is six PLATED HOLES: copper on all six layers, so whatever sits
          # behind it on the back is displaced. At 53.50..60.10 it punched through
          # C114, C115, C119 and C120. Turned R90 it is 4.06 wide instead of 6.60
          # and fits the corridor between the decoupling field and the Pmod, which
          # is the only span on this board with BOTH sides clear for the full
          # channel height. It stays one standard 2x3 JTAG header.
          ("JP3", 58.79, 6.86, "R90"),
          # J1 moves 1.00 mm towards the +x edge. Its BODY is 5.08 wide and started at
          # 62.87; JP3's body ends at 63.36, so at the old position the two plastic
          # shrouds fouled each other by 0.11 mm even though the holes cleared by
          # 0.91. This leaves 0.51 mm each side of JP3 and still 0.90 mm of board
          # outboard of the Pmod.
          ("J1", 63.865, 2.54, "R90"),
          # FLASH and EEPROM as a pair: they spanned y 2.60..14.10, centre 8.35, so
          # both rise 1.81 mm to put the stack on the board axis at 10.16.
          ("U4", 0.80, 4.41, "MR0"), ("U10", 0.80, 10.81, "MR0"),
          # U3 drops 1.20 mm, and this one COSTS something. X1's two rear shell
          # nails are PLATED HOLES -- copper on every layer -- at y 15.454..16.904,
          # and U3's upper pad row ended at 16.440, so the drills went through it.
          # The old footprint had four SMD tabs and no holes, so nothing on the
          # back could ever collide; the rebuild is what exposed it.
          #
          # The cost: U3 and J1 were both y-centred on 10.160, the board axis,
          # which is what "centre the SDRAM with the Pmod" meant. U3 is now at
          # 9.060 and J1 is not. Moving J1 down to match would leave it 1.77 mm
          # off the bottom edge. Left as a decision, see board/STACKUP.md.
          ("U3", 17.20, 2.68, "MR90")]
for p, bx, by, rot in SINGLE:
    PLACE[p] = origin_for(p, bx, by + YOFF, rot) + (rot,)

# X2 IS the board. Its package carries the outline on layer 21 as the rectangle
# (0, 0) to (69.85, 20.32) and all 44 pads in that same frame, so its element
# origin has to sit exactly on the board origin, unrotated. It cannot go through
# SINGLE: origin_for() slides a part until its bounding box corner reaches the
# target, and X2's bbox starts at the first pad's outer edge, which would put
# every header hole about half a millimetre off the grid the board is built on.
# Left out of the table entirely it fell through to PARK, which is how the whole
# header ended up 20 mm below the board with its outline drawn down there too.
PLACE["X2"] = (0.0, 0.0, "R0")

# X1 is placed by the drawing, not by its bounding box. Molex SD-105017-001
# sheet 1 marks a PCB EDGE line 4.141 mm in front of the rear-row centreline and
# puts the CONNECTOR FRONT INTERFACE 0.70 mm beyond that, so the shell overhangs
# the board. origin_for() would slide the bounding box -- which now includes the
# overhanging body on layer 51 -- until its corner met a block, and the edge line
# would land wherever it fell. Put the edge line on the outline instead and let
# the overhang fall outside, which is the whole point of the part.
#
# The footprint carries that line on layer 48 and check_board.py asserts it lands
# on the outline, so this number and the footprint cannot drift apart.
X1_PCB_EDGE = 4.141
PLACE["X1"] = (33.02, BY1 - X1_PCB_EDGE, "R0")


def tile(parts, x0, y0, x1, y1, rot, gap=0.55, avoid=()):
    """lay parts in rows inside a block, left to right then upward.

    Tallest first: in schematic order the 1210 bulk caps land in the middle of
    a row of 0402s and every row inherits their height, which wasted enough
    space to push seven capacitors out of the decoupling window.

    `avoid` is a list of rectangles the parts must not touch. The FPGA
    decoupling window sits over the ball field, and the one part of that field
    where a via can go -- the empty moat -- is also the only place the escape
    can put its vias. A capacitor there is a drill through a capacitor.
    """
    parts = sorted(parts, key=lambda q: -(lambda r: r[3] - r[1])(
        rbbox(pad_box(PARTS[q][0], pkg_of(q)), rot)))
    # Anything already placed on this side inside this window is an obstacle
    # too, which is what lets the same field be filled by more than one call.
    # Without it a second pass restarts at the origin and lays a row straight on
    # top of the first. X2 is skipped because X2 IS the board -- its bounding
    # box is the outline, and treating that as an obstacle parks everything.
    # The FPGA reservation is per side, and which side matters more than anything
    # else on this board. On the FRONT the whole NOFPGA box is out: the ball
    # field, and the escape corridors that leave it on L1. On the BACK there is
    # no ball land at all -- U1's pads are layer-1 SMD -- and the only copper the
    # escape leaves down there is the ring of via lands in the moat. Reserving
    # the full box on both sides was costing 117 mm2 of the best decoupling real
    # estate on the board, directly opposite the power balls, which is where a
    # bypass capacitor is supposed to go.
    avoid = list(avoid) + [NOVIA] + RING + ([] if rot.startswith("M") else [NOFPGA])
    for q, (qx, qy, qrot) in PLACE.items():
        if q == "X2" or qrot.startswith("M") != rot.startswith("M"):
            continue
        box = shift(rbbox(pad_box(PARTS[q][0], pkg_of(q)), qrot), qx, qy)
        if box[0] < x1 and x0 < box[2] and box[1] < y1 and y0 < box[3]:
            avoid.append(box)
    # First fit, one part at a time, and a part that does not fit is SKIPPED
    # rather than ending the field. The old loop returned every remaining part
    # the moment one failed, so three 1206 at the head of the queue -- they sort
    # first, being tallest -- shut the door on eleven 0603 behind them that had
    # room. Each part gets its own scan from the origin; the avoid list carries
    # everything already down, so first fit cannot overlap.
    failed = []
    for p in parts:
        # size AND position by the keepout box, not the silk. Placing by silk and
        # testing against keepouts put twenty-six parts inside each other's
        # keep-out areas: a 0402 resistor's layer-39 box is 0.92 mm wider than
        # its outline on every side.
        r = rbbox(pad_box(PARTS[p][0], pkg_of(p)), rot)
        w, h = r[2] - r[0], r[3] - r[1]
        cx, cy, put = x0, y0, False
        while cy + h <= y1 + 1e-9:
            if cx + w > x1 + 1e-9:
                # next row: jump to the lowest obstacle top above the current
                # line rather than creeping up in gap-sized steps. Creeping lost
                # 0.45 mm at every inductor in the regulator block and pushed
                # C78 off the board by the fifth part.
                ups = [a[3] for a in avoid if a[3] > cy + 1e-9 and a[0] < x1 and a[2] > x0]
                cx, cy = x0, (min(ups) if ups else cy + gap)
                continue
            # Step to the NEAREST right edge among everything blocking here, not
            # to whichever blocker the list happened to hold first. next() picked
            # an arbitrary one, so a wide obstacle overlapping a narrow one threw
            # cx past the free lane between them and the scan never came back --
            # first fit is only first fit if it advances by the smallest step
            # that can change the answer.
            hits = [a[2] for a in avoid if cx < a[2] and a[0] < cx + w
                    and cy < a[3] and a[1] < cy + h]
            if hits:
                cx = min(hits) + 1e-6
                continue
            PLACE[p] = (cx - r[0], cy - r[1], rot)
            avoid.append((cx, cy, cx + w, cy + h))
            put = True
            break
        if not put:
            failed.append(p)
    return failed


def hole_zones(margin=0.20):
    """keep-out rectangles for every plated hole already placed.

    A plated hole is copper on every layer, so it does not care which side a
    part is on. tile() had no idea they existed: widening the bulk belt dropped
    a capacitor straight onto X1's shell nail, which check_board caught and
    tile() never would have.
    """
    out = []
    for p, (px, py, rot) in PLACE.items():
        src = PKGSRC[(PARTS[p][0], pkg_of(p))]
        for m in re.finditer(r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*'
                             r'drill="([\d.]+)"(?:[^>]*diameter="([\d.]+)")?', src):
            x, y, dr = float(m.group(1)), float(m.group(2)), float(m.group(3))
            di = float(m.group(4)) if m.group(4) else dr + 0.5
            dx, dy = rp(x, y, rot)
            r = di / 2 + margin
            out.append((px + dx - r, py + dy - r, px + dx + r, py + dy + r))
    return out


# The regulator's core, on the back. This block was 6.00 x 10.50 while L1-L3
# were 0603 and C78 an 0402. Repackaging them -- IND2520 at 3.40 x 2.30 and
# C0805 at 3.00 x 1.50, because the old packages could not hold their values --
# means only one part fits per row across the 6.00 width, so the block runs up
# to the decoupling field's top edge at 18.10 instead of stopping at 13.00.
tile(["U8", "L1", "L2", "L3", "C78"], *yb(10.60, 2.50, 16.60, 18.10, "MR0"))
# The FPGA's decoupling, on the back directly under the ball field. The window
# is 18.00 x 15.80 rather than the old 20.00 x 15.80: the back now has to hold
# the SDRAM as well between the regulator block and the Pmod strip, 22.35 + 18.00
# in the 44.36 mm available, and U3 went left because the ball field's shadow is
# where it used to sit.
sheet7 = re.search(r'<sheet name="FPGA POWER">(.*?)</sheet>', t, re.S).group(1)
C7 = sorted({m.group(1) for m in re.finditer(r'<instance part="(C\d+)"', sheet7)},
            key=lambda s: int(s[1:]))
# THE FPGA DECOUPLING IS LAID OUT IN THREE BANDS WITH THE PACKAGE LEFT CLEAR.
#
# It used to be one 18.65 x 16.08 window tiled solid, which put capacitors under
# the ball field, through the moat, and hard against all four edges of the
# package. Under the field they are useless -- there is no room for a via there,
# so they cannot be connected -- and against the edges they take the only space
# the escape has for its own vias. Stage 3 measured what that cost: back-side
# copper reaching 0.629 mm PAST the package edge on the right, and 38 of 103
# escapes with nowhere to go.
#
# So the window is gone. Three bands instead, none of which touches the package
# or the 0.98 mm belt around it, and the left side left entirely alone:
#
#   right   x 51.99..58.70   the big one, two columns of 0402 by eleven rows
#   above   x 40.05..51.99   between the package and X2's top hole row
#   below   x 40.05..51.99   between the package and X2's bottom hole row
#   left    NOTHING          x 39.55..42.00 is 2.45 mm of clear board between
#                            U3 and the package, and the escape needs all of it
#
# Highest frequency first: the 0.47 uF parts are placed before the 4.7 uF, so
# they take the bands nearest the package and the bulk never crowds them out.
BULK = [c for c in C7 if pkg_of(c) == "C1206"]      # 47 uF, bulk
MID = [c for c in C7 if pkg_of(c) == "C0603"]       # 4.7 uF
HF = [c for c in C7 if pkg_of(c) == "C0402"]        # 0.47 uF, the ones that matter

# The 47 uF bulk goes first and nowhere near the ball field. Bulk belongs at the
# regulator and gains nothing from sitting under the FPGA; the belt above U3 is
# clear of L3 and C78 on the left, above U3's top edge at 15.24 and below X2's
# top hole row, whose 1.52 lands reach down to 18.29.
spill = tile(BULK, *yb(14.60, 15.55, 38.36, 18.29, "MR0"), avoid=hole_zones())

# Then the 0.47 uF, into the three bands that touch the package, before anything
# else can take them. tile() sorts tallest-first inside a band to stop a 1206
# setting the height of a row of 0402s -- which also means that handing it a
# mixed list puts the big parts nearest the package and pushes the small ones
# out. Twelve 0.47 uF ended up parked below the board that way. Give each size
# its own call instead, smallest and most urgent first.
# The right-hand column stands off at 52.98, not 51.99. 30 of the 35 escapes on
# that side must leave L1 -- 17 of them to U3, which sits on the BACK at x 38.77,
# to the LEFT of the FPGA, so the SDRAM bus comes out of the right-hand column
# and crosses the whole package to reach it -- and 32 places at 0.39 pitch need a
# half-width of 6.24, which is x 52.98 once the via land and its clearance are
# taken off. See tools/needvia.py.
#
# ABOVE and BELOW step back from that corridor too. They are outside the
# package's own y range but not outside the via row's, which runs y 3.46..15.94
# at that half-width, so their end capacitors were setting the limit rather than
# the right-hand column itself.
ABOVE = yb(40.05, 15.95, 52.98, 18.29, "MR0")
BELOW = yb(40.05, 2.12, 52.98, 3.45, "MR0")
LEFT = yb(39.55, 5.20, 41.01, 14.20, "MR90")         # stood on end, 1.46 mm wide
# The two right-hand fields are 5.81 mm wide and 16 tall. Laid flat that is
# one column of 0402 by eleven rows; stood on end it is four by four. Tall
# narrow fields want the parts turned.
RIGHT = yb(52.98, 2.12, 58.79, 18.29, "MR90")        # the big one, out to JP3
# Q1 sits in the middle of the right-hand front field and is an avoid, not a
# boundary.
Q1BOX = yb(53.79, 8.01, 57.39, 12.31)
# JP3's SHROUD reaches x 58.28, half a millimetre further left than any of its
# copper or silk, and bbox() only measures copper and layers 21/51 -- so tile()
# walked three capacitors into it. Given explicitly, like Q1.
JP3BOX = yb(58.03, 6.10, 63.61, 14.22)
FIELDS = [ABOVE, BELOW, LEFT, RIGHT,
          yb(40.05, 15.95, 58.79, 18.29, "R0"),      # front, above U1
          yb(52.98, 3.45, 58.79, 15.95, "R90"),      # front, right of U1
          yb(38.35, 2.12, 40.26, 18.29, "R90")]      # front, left of U1, on end

# Two passes, smallest first. tile() sorts tallest-first WITHIN a field so a 1206
# cannot set the height of a row of 0402s, which also means a mixed list puts the
# big parts in first and pushes the small ones out -- nine 0.47 uF were parked
# that way. Run the 0.47 uF through every field before the 4.7 uF sees any of
# them. tile() treats anything already placed as an obstacle, so the second pass
# picks up where the first left off instead of laying a row on top of it.
left = HF
for pas in (0, 1):
    for x0, y0, x1, y1, rot in FIELDS:
        if not left:
            break
        left = tile(left, x0, y0, x1, y1, rot, gap=0.35,
                    avoid=hole_zones() + [Q1BOX, JP3BOX])
    if pas == 0:
        left = left + MID + spill
# LEDs, on the front
tile([p for p in ("LD0", "LD1", "LD2", "LD5") if p in PARTS], *yb(23.55, 7.27, 27.008, 14.00, "R0"))

# everything else parks below the board, on a 6 mm grid, for the user to place
# --- everything else, placed beside whatever it serves ----------------------
# 108 parts used to fall straight through to PARK: 64 resistors, 36 capacitors,
# the inductors, the diodes, the transistors and the Creative Commons artwork.
# They are not interchangeable and they are not a tiling job -- a series resistor
# belongs at its source pin, a decoupling capacitor beside the pin it decouples,
# the LTC3569's feedback divider tight to the regulator where trace length is
# part of the circuit. So each one is anchored to the DEVICE it serves and placed
# as near to it as there is room.
#
# The anchor comes from the nets. Ignore the power nets first, because they touch
# everything, and see which device the part shares a signal with. A part that has
# only power nets -- a decoupling capacitor -- has no signal to go on, so fall
# back to the schematic sheet it was drawn on, which is how the designer grouped
# it in the first place.
SHEET_ANCHOR = {"Memory": "U3", "FT2232 JTAG CLK": "U2", "Power Supplies": "U8",
                "FPGA POWER": "U1", "FPGA CONNECT": "U1", "General IO": "X2"}
# ANCHORED BY HAND, because the net count cannot tell these two apart. Every SD
# net touches U1 at one end and X3 at the other, so R34 (the DAT0-DAT3 pack) and
# R35 (CMD) tie 4-4 and 1-1, and the tie is broken alphabetically -- U1 beats X3
# on the letter. That put both packs at x~58 on a 69.85 mm board while the socket
# they pull up sits at x=15.95, and five of the six SD nets were dragged into
# full-width hauls straight through the SDRAM bus. microSD then routed 0 of 6 on
# the finished board where it routes 6 of 6 on a clear one. A pull-up belongs
# beside the part it pulls up.
#
# The alphabetical tie-break is the real defect and it is NOT fixed here. It
# reaches four more parts -- R2 (ties U1/U4), R4 and R93/R94 (U1/U2) -- which all
# lose to U1 the same way, while J1, LD1, LD2, BTN and Q1 win their ties only
# because their refdes sorts before "U1". Changing the rule moves six parts and
# re-flows the layout, so it is a separate measured decision.
ANCHOR = {"R34": "X3", "R35": "X3"}
DEVICE = re.compile(r"^(U\d|X\d|J\d|JP\d|Q\d|BTN|LD\d)")
POWERNET = re.compile(r"^(GND|VCC|VDD|\+|USB5V0|VU|VEXT)", re.I)

sheet_of = {}
for m in re.finditer(r'<sheet name="([^"]+)">(.*?)</sheet>', t, re.S):
    for i in re.finditer(r'<instance part="([^"]+)"', m.group(2)):
        sheet_of.setdefault(i.group(1), m.group(1))
netparts = collections.defaultdict(set)
for n, pins in NETS.items():
    for q, _g, _pin in pins:
        netparts[n].add(q)

# The four Creative Commons marks -- CC, BY, SA and the copyright line -- are
# decorative silk with no electrical function, and they are kept OFF the board.
#
# They also expose a real hole in bbox(), which reads <wire> and <rectangle> on
# layers 21 and 51 and nothing else. CC_SA is drawn as a circle and a polygon
# and measured 0.25 x 0.56 where it is really 3.56 x 3.56 -- a fourteenth of its
# area -- so the placer fitted it into a sliver against the FPGA, and CC_BY with
# it. CC_CC and CC_COPYRIGHT have no wire at all and only escaped the same fate
# because even the 1.00 x 1.00 fallback would not fit.
#
# Excluding them here is not a workaround for that. It is what was asked for,
# and it happens to make the artwork immune to it. The hole itself is still
# open and it reaches three real parts as well -- X3 by 0.65 mm, X1 by 0.50 and
# U8 by 0.35 -- which is a placement re-flow and a separate decision.
ARTWORK = {q for q in PLACEABLE if pkg_of(q).startswith("CC_")}
todo = [q for q in PLACEABLE if q not in PLACE and q not in ARTWORK]
group = collections.defaultdict(list)
for q in todo:
    cands = collections.Counter()
    for n, pins in NETS.items():
        if q not in {a for a, _g, _p in pins} or POWERNET.match(n):
            continue
        # sorted(), because netparts holds sets and Python randomises string
        # hashing per process. Counter ties are broken by insertion order, so an
        # unsorted walk picked a different anchor for the same part on different
        # runs and the whole layout moved -- two runs of this script over
        # identical inputs gave 33 parked and then 35. A board generator has to
        # be reproducible or none of the checks below mean anything.
        for other in sorted(netparts[n]):
            if other in PLACE and DEVICE.match(other) and other != "X2":
                cands[other] += 1
    # ties to the lowest refdes, again so the result does not depend on hashing
    a = ANCHOR.get(q) or (min(sorted(cands), key=lambda k: -cands[k]) if cands
                          else SHEET_ANCHOR.get(sheet_of.get(q, ""), ""))
    group[a if a in PLACE else "X2"].append(q)

REACHES = (3.0, 5.0, 7.5, 11.0, 16.0, 24.0)


def place_at(parts, anchor, reach, avoid):
    """one pass at one radius: own side first, then the other, turning each time

    Both orientations, because what is left by this point is not open field, it
    is the channels between things already down -- and an 0402 is 2.996 x 1.200
    one way round and 1.200 x 2.996 the other. Laying every part flat left
    446 mm2 of board free against 262 mm2 of parts that would not fit in it: the
    space was there, in strips too narrow to take a part sideways.
    """
    if anchor not in PLACE:
        return parts
    ax, ay, arot = PLACE[anchor]
    r = rbbox(bbox(PARTS[anchor][0], pkg_of(anchor)), arot)
    cx0, cy0 = ax + (r[0] + r[2]) / 2, ay + (r[1] + r[3]) / 2
    left = parts
    for side in (arot if arot.startswith("M") else "R0",
                 "R0" if arot.startswith("M") else "MR0"):
        for rot in (side, side.replace("R0", "R90")):
            if not left:
                return []
            left = tile(left, max(0.35, cx0 - reach), max(0.35, cy0 - reach),
                        min(BX1 - 0.35, cx0 + reach), min(BY1 - 0.35, cy0 + reach),
                        rot, gap=0.35, avoid=avoid)
    return left


# Radius outermost, group innermost: every group gets its shot at 3 mm before
# any group is allowed 5. Run to exhaustion one group at a time and the biggest
# group -- the FPGA's 37 -- reaches 24 mm and takes the whole board with it, and
# the ten SDRAM bypass capacitors whose turn came ninth were left with nowhere
# within 24 mm of U3 to sit. Nothing about a capacitor 24 mm from its own device
# is worth the one it displaced 3 mm from another.
AVOID = hole_zones() + [Q1BOX, JP3BOX]
rest = {a: list(group[a]) for a in group}
order = sorted(group, key=lambda k: -len(group[k]))
for reach in REACHES:
    for a in order:
        if rest[a]:
            rest[a] = place_at(rest[a], a, reach, AVOID)
NOFIT = [p for a in order for p in rest[a]]

PARK = [p for p in PLACEABLE if p not in PLACE]
# The licence mark goes below the board in reading order -- CC, BY, SA, then the
# copyright line -- so it stays legible as one thing instead of being scattered
# through the parking grid by refdes.
ORDER = {"CC_CC": 0, "CC_BY": 1, "CC_SA": 2, "CC_COPYRIGHT": 3}
art = sorted((p for p in PARK if p in ARTWORK), key=lambda p: ORDER.get(pkg_of(p), 9))
px = 2.0
for p in art:
    r = bbox(PARTS[p][0], pkg_of(p))
    PLACE[p] = origin_for(p, px, -9.5, "R0") + ("R0",)
    px += (r[2] - r[0]) + 1.0
px, py = 2.0, -18.0
for p in [q for q in PARK if q not in ARTWORK]:
    if px > 66.0:
        px, py = 2.0, py - 6.0
    PLACE[p] = origin_for(p, px, py, "R0") + ("R0",)
    px += 6.0

# --- emit -------------------------------------------------------------------
def keep(tag):
    return re.search(r"<%s>.*?</%s>" % (tag, tag), old, re.S).group(0)


dru_desc, dru_params = "", []
for line in open(DRU, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    k, _, v = line.partition("=")
    k, v = k.strip(), v.strip()
    if k.startswith("description"):
        dru_desc = v
    else:
        dru_params.append((k, v))

def layers():
    """the kept <layers> block, with every layer layerSetup names switched on.

    keep("layers") copies this verbatim from the previous board, which was the
    Spartan-6 four-layer layout: Route4 and Route5 are in it as active="no".
    The design rules declare (1*2*3*4*5*16), so the board claimed six copper
    layers while two of them were switched off and could not be routed on or
    given a plane. Derive the set from layerSetup instead of trusting the copy.
    """
    setup = dict(dru_params).get("layerSetup", "")
    want = {int(n) for n in re.findall(r"\d+", setup)}
    src = keep("layers")
    for n in sorted(want):
        m = re.search(r'<layer number="%d"[^>]*/>' % n, src)
        if not m:
            continue
        fixed = re.sub(r'visible="no"', 'visible="yes"',
                       re.sub(r'active="no"', 'active="yes"', m.group(0)))
        src = src.replace(m.group(0), fixed, 1)
    on = len(re.findall(r'<layer number="(?:%s)"[^>]*active="yes"'
                        % "|".join(str(n) for n in sorted(want)), src))
    assert on == len(want), "layerSetup names %d copper layers, %d are active" % (len(want), on)
    return src


libs = collections.defaultdict(set)
for p in PLACEABLE:
    libs[PARTS[p][0]].add(pkg_of(p))

# --- footprint provenance notes: keep them, but not on top of the board ------
# Three ctambe packages carry prose on layer 51 recording what was measured
# against which datasheet page. In the library that is exactly where it belongs
# -- you see it while editing the footprint. On the board it rides along with
# the element, and X1's three lines and U8's two landed inside the outline,
# straight across the layout. X3's six only escaped by being placed at the left
# edge, which is luck, not design.
#
# So: strip them out of the board's copy of each package and re-emit them once,
# as a block above the outline where nothing else lives. The schematic library
# keeps the originals untouched.
DOCNOTE = re.compile(r'\s*<text (x="[-\d.]+" y="[-\d.]+"[^>]*layer="51"[^>]*)>([^<]{25,})</text>')
notes, users = collections.OrderedDict(), collections.defaultdict(list)
for p in PLACEABLE:
    users[(PARTS[p][0], pkg_of(p))].append(p)


def strip_notes(lib, pk, xml):
    found = [m.group(2) for m in DOCNOTE.finditer(xml)]
    if found:
        notes[(lib, pk)] = found
    return DOCNOTE.sub("", xml)

o = ['<?xml version="1.0" encoding="utf-8"?>', '<!DOCTYPE eagle SYSTEM "eagle.dtd">',
     '<eagle version="9.7.0">', "<drawing>", keep("settings"),
     re.search(r"<grid [^>]*/>", old).group(0), layers(), "<board>", "<plain>"]
for a, b, c, d in ((0, 0, BX1, 0), (BX1, 0, BX1, BY1), (BX1, BY1, 0, BY1), (0, BY1, 0, 0)):
    o.append('<wire x1="%s" y1="%s" x2="%s" y2="%s" width="0" layer="20"/>' % (g(a), g(b), g(c), g(d)))
PLAIN_AT = len(o)          # the notes block is built below and spliced in here
o.append("</plain>")
o.append("<libraries>")
for lib in sorted(libs):
    o.append('<library name="%s">' % lib)
    o.append("<packages>")
    for pk in sorted(libs[lib]):
        o.append(strip_notes(lib, pk, PKGSRC[(lib, pk)]))
    o.append("</packages>")
    o.append("</library>")

# The block sits above the outline, growing upward from BY1 + 2.00. Nothing else
# is up there -- the placed parts top out at y 17.82 and everything parked is
# below y 0 -- so it cannot collide with the layout no matter how long it gets.
ordered = sorted(notes.items(), key=lambda kv: kv[0][1])
if ordered:
    # lay it out downward from a computed top, so it reads title-first
    h = 1.10 + sum(0.90 + 0.75 * len(v) + 0.60 for _, v in ordered)
    block, y = [], BY1 + 2.00 + h
    block.append('<text x="0" y="%s" size="0.7" layer="51" ratio="12">Footprint provenance'
                 ' -- moved off the board, originals live in the ctambe library'
                 '</text>' % g(y))
    y -= 1.10
    for (lib, pk), lines in ordered:
        block.append('<text x="0" y="%s" size="0.6" layer="51" ratio="10">%s -- %s</text>'
                     % (g(y), esc(", ".join(sorted(users[(lib, pk)]))), esc(pk)))
        y -= 0.90
        for ln in lines:
            block.append('<text x="2" y="%s" size="0.5" layer="51" ratio="10">%s</text>'
                         % (g(y), ln))
            y -= 0.75
        y -= 0.60
    o[PLAIN_AT:PLAIN_AT] = block

o += ["</libraries>", "<attributes>", "</attributes>", "<variantdefs>", "</variantdefs>",
      "<classes>", CLASSES, "</classes>",
      '<designrules name="Zulu A7 6 layer %s">' % FAB.upper(),
      "<description language=\"en\">%s</description>" % esc(dru_desc)]
for k, v in dru_params:
    o.append('<param name="%s" value="%s"/>' % (k, esc(v)))
o.append("</designrules>")
# THE AUTOROUTER'S OWN LAYER LIST, which is not the same thing as <layers>.
# check_board has always passed 'all 6 are active in <layers> and can be routed
# on', and that stayed true while the autorouter was configured for a TWO-layer
# board: PrefDir 1 and 16 enabled, everything else 0. keep() carried that
# forward from the original Zulu A7 unchanged, so Fusion greeted the six-layer
# stackup with 'Layer 2, 3, 4, 5 used but not enabled'.
#
# L3 and L4 are signal layers and are turned on ORTHOGONALLY -- L3 horizontal,
# L4 vertical -- which is what the stackup section of board/STACKUP.md asks for,
# and matters more than usual here because freeing L4 left L3 referencing L2
# across 0.5495 mm instead of a plane right beneath it.
#
# L2 and L5 STAY OFF. They are the GND and VCC3V3 pours; a router laying signals
# on a plane layer is not a feature. Fusion will still name them in that warning
# because they carry copper, and that is correct: it is telling you the pours
# are there, not that something is misconfigured.
PREFDIR = {1: '*', 2: '0', 3: '-', 4: '|', 5: '0', 16: '*'}
_ar = keep('autorouter')
for _n in range(1, 17):
    _ar = re.sub(r'(<param name="PrefDir\.%d" value=")[^"]*(")' % _n,
                 r'\g<1>%s\g<2>' % PREFDIR.get(_n, '0'), _ar)
o.append(_ar)
o.append("<elements>")
for p in PLACEABLE:
    x, y, rot = PLACE[p]
    o.append('<element name="%s" library="%s" package="%s" value="%s" x="%s" y="%s"%s/>'
             % (p, PARTS[p][0], pkg_of(p), esc(PARTS[p][3]), g(x), g(y),
                "" if rot == "R0" else ' rot="%s"' % rot))
o.append("</elements>")
o.append("<signals>")
for n, pins in NETS.items():
    _cls = NETCLASS.get(n, "0")
    o.append('<signal name="%s"%s>'
             % (esc(n), "" if _cls == "0" else ' class="%s"' % _cls))
    for part, gt, pn in sorted(pins):
        if part not in PLACEABLE:
            continue
        l, d, dv, _v = PARTS[part]
        for pad in DEV[(l, d, dv)][1].get((gt, pn), []):
            o.append('<contactref element="%s" pad="%s"/>' % (part, pad))
    o.append("</signal>")
o += ["</signals>", "</board>", "</drawing>", "</eagle>", ""]
brd = "\n".join(o)

# --- verify -----------------------------------------------------------------
print("[1] structure")
import xml.etree.ElementTree as ET
ET.fromstring(brd)
print("    XML parses; %d elements, %d signals" % (brd.count("<element name="), brd.count("<signal name=")))

print("[2] parts <-> elements")
el = {m.group(1): (m.group(2), m.group(3)) for m in
      re.finditer(r'<element name="([^"]+)" library="([^"]+)" package="([^"]+)"', brd)}
assert set(el) == set(PLACEABLE), set(el) ^ set(PLACEABLE)
for p in PLACEABLE:
    assert el[p] == (PARTS[p][0], pkg_of(p)), (p, el[p])
noelem = [p for p in PARTS if p not in el]
print("    %d parts -> %d elements; %d schematic-only parts correctly have none" % (len(PARTS), len(el), len(noelem)))

print("[3] nets <-> signals, pad by pad")
sig = {}
for m in re.finditer(r'<signal name="([^"]+)"[^>]*>(.*?)</signal>', brd, re.S):
    sig[m.group(1)] = set(re.findall(r'<contactref element="([^"]+)" pad="([^"]+)"/>', m.group(2)))
assert set(sig) == set(NETS), set(sig) ^ set(NETS)
multi = 0
for n, pins in NETS.items():
    want = set()
    for part, gt, pn in pins:
        if part in PLACEABLE:
            l, d, dv, _v = PARTS[part]
            pads = DEV[(l, d, dv)][1].get((gt, pn), [])
            multi += len(pads) > 1
            want |= {(part, pad) for pad in pads}
    assert sig[n] == want, (n, sig[n] ^ want)
print("    all %d signals match, %d contactrefs, %d from pins that map to several pads"
      % (len(sig), sum(len(v) for v in sig.values()), multi))

print("[4] every package an element names is in the board's libraries")
have = {(m.group(1), pk) for m in re.finditer(r'<library name="([^"]+)">(.*?)</library>', brd, re.S)
        for pk in re.findall(r'<package name="([^"]+)">', m.group(2))}
miss = {(PARTS[p][0], pkg_of(p)) for p in PLACEABLE} - have
assert not miss, miss
print("    %d packages across %d libraries, none missing" % (len(have), len(libs)))

print("[5] the placed blocks")
# Everything that ended up on the board, not just the parts named in a table.
# The group placement puts another sixty-odd down, and none of them were being
# checked for overlap while this list was hand-written.
placed = [q for q in PLACE if q not in PARK and q != "X2"]
boxes, body = {}, {}
for p in placed:
    x, y, rot = PLACE[p]
    boxes[p] = shift(rbbox(bbox(PARTS[p][0], pkg_of(p)), rot), x, y)
    body[p] = shift(rbbox(obst_box(PARTS[p][0], pkg_of(p)), rot), x, y)
# X1 hangs over the edge on purpose -- Molex SD-105017-001 puts the mating
# face 0.70 mm past the PCB EDGE, so a footprint that stayed inside would be
# the wrong one. check_board.py makes the same exception.
out = [p for p, b in boxes.items() if p != "X1"
       and (b[0] < -1e-6 or b[1] < -1e-6 or b[2] > BX1 + 1e-6 or b[3] > BY1 + 1e-6)]
assert not out, [(p, boxes[p]) for p in out]
# only parts on the SAME side can collide -- front and back are meant to overlap
#
# Measured on the KEEPOUT box, not the silk, so this assertion asks the same
# question check_board.py's shape() test does: no two same-side bodies drawn on
# 21, 39 or 51 may overlap. Testing the silk here and the keepout there let a
# placement leave make_board.py clean and fail the checker.
side = {p: PLACE[p][2].startswith("M") for p in boxes}
ov = []
for a in body:
    for b in body:
        if a < b and side[a] == side[b] \
           and body[a][0] < body[b][2] - 1e-6 and body[b][0] < body[a][2] - 1e-6 \
           and body[a][1] < body[b][3] - 1e-6 and body[b][1] < body[a][3] - 1e-6:
            ov.append((a, b))
assert not ov, ov[:6]
print("    %d parts placed on the board, none overlapping, none off the outline" % len(placed))
print("    %d parked below it for the user to position%s"
      % (len(PARK), "; %d decoupling caps did not fit the window" % len(left) if left else ""))

print("[6] every contactref names a pad that really exists in that package")
PADS = {}
for lib, pk in have:
    PADS[(lib, pk)] = set(re.findall(r'<(?:pad|smd) name="([^"]+)"', PKGSRC[(lib, pk)]))
bad = [(e, pd) for m in re.finditer(r'<signal name="[^"]+"[^>]*>(.*?)</signal>', brd, re.S)
       for e, pd in re.findall(r'<contactref element="([^"]+)" pad="([^"]+)"/>', m.group(1))
       if pd not in PADS[(PARTS[e][0], pkg_of(e))]]
assert not bad, bad[:6]
print("    all %d contactrefs resolve to a real pad" % sum(len(v) for v in sig.values()))

print("[7] stackup and rules")
ls = re.search(r'<param name="layerSetup" value="([^"]+)"/>', brd).group(1)
print("    layerSetup %s -> %d copper layers" % (ls, len(re.findall(r"\d+", ls))))
for k in ("mdWireWire", "msWidth", "msDrill", "rlMinViaOuter", "mdCopperDimension"):
    print("    %-18s %s" % (k, re.search(r'<param name="%s" value="([^"]+)"/>' % k, brd).group(1)))
assert len(re.findall(r"\d+", ls)) == 6

had = os.path.exists(BRD)
if had:
    shutil.copyfile(BRD, BRD + ".bak")
open(BRD, "w", encoding="utf-8").write(brd)
print("\nwrote %s%s" % (BRD, "  (previous board saved as zulu_a7.brd.bak)" if had else "  (new)"))
print("wrote %s  (%d ball lands set to %s mm)" % (SCH, 238, CFG["land"]))
sg = re.search(r"<signals>.*?</signals>", brd, re.S).group(0)
print("unrouted by design: %d wires, %d vias, %d polygons inside <signals>"
      % (sg.count("<wire"), sg.count("<via "), sg.count("<polygon")))
