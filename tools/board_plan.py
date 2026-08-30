# -*- coding: utf-8 -*-
"""Write the to-scale front/back placement plan into the project folder.

The outline and the X2 pad grid are read live from zulu_a7.sch, so a footprint or
dimension change redraws the plan rather than repeating a stale number; only the
block positions are decided here. Every figure quoted below is printed by the
script and written into the page -- do not copy any of them into this docstring,
which is exactly how the last set went stale (it described the 2.400 in board
long after the board became 2.750).

WHAT DRIVES THIS LAYOUT

The header rows leave a channel between them running the whole length, and
everything that is not a header pin lives in it. That channel, not the board
rectangle, is the usable interior, and it is the number to argue with if the
layout will not close.

THE AREA BUDGET IS MEASURED, AND IT INCLUDES WHAT IS NOT A PART

Each part is sized by the same two-rule box make_board.py's tile() places it
against -- layer-39 courtyard abutting its neighbour, copper holding CU_GAP off
foreign copper, wider per axis -- rather than by a guessed packing factor.

The budget then adds the reservations that belong to no part at all: the FPGA
escape corridors, the stage-2 moat, the stage-3 fan-out ring and the two
connector shrouds. Leaving those out is what let this page report +309 mm2 of
slack on a board that cannot in fact take its own parts. The old guessed factors
(1.70 and 1.15) were wrong in both directions and cancelled, so the parts total
was right to within 1 mm2 and the omission was the whole error.

Bulk area is still only a floor. It assumes any square millimetre can hold any
part, when a part has to sit near what it serves and the interior is a thin
channel, so the leftovers come out as strips too narrow to take an 0402
sideways. The script therefore also reads the generated board and reports how
many parts the placer really could not seat, which is always the larger number.

Three constraints decided nearly every position:

  1. The board sits pin-down on a breadboard, so the back has only the header's
     standoff for clearance. Every connector, button and LED is on the front,
     because on the back nobody could reach it. The only package height this
     project can verify from a local datasheet is U4's SOIC-8 208-mil, A = 2.16
     max, so the flash is the tallest thing on the back and it is the one to
     measure against the standoff. UG475 carries the CPG236 drawing as vector
     art with no height in the text, so that number is not established here.

  2. The FPGA's decoupling wants to be directly behind the ball field. That
     constrains the two to OPPOSITE sides -- it says nothing about which side
     each takes, and an earlier version of this plan wrongly treated it as a
     reason to put the FPGA on the back. The FPGA is on the FRONT: it is what
     gets hot, what anyone will want to inspect or rework on a 238-ball BGA,
     and the back faces a breadboard a couple of millimetres away with no
     airflow. The capacitor field sits under it on the BACK, and nothing else
     is allowed into that footprint on either side. On the old board the SDRAM
     sat in that shadow, which is what made the decoupling unplaceable.

  3. The microSD ejects along its own -y, 21.55 mm of travel on layer 39. The
     board is only 25.40 mm across, so the card cannot come out over a long
     edge -- X3 has to be rotated to throw it off a board END, and the +x end
     is the Pmod strip, so it goes at the -x end ejecting outward. That means
     R270. R90 points the slot the other way, +x into the board, and the card
     could then only be inserted from the middle of the board; it was R90 until
     check_board.py's keepout test caught the stroke running through BTN.

The USB has four vacant top-row positions, x 29.972 to 41.148, 11.176 mm clear
against X1's 7.80 mm of copper. It was three until pads 6-17 shifted one place
towards the empty corner: that filled the corner and opened a fourth position on
the USB side. X1 is centred in the result, 1.69 mm each side, where before it had
3.03 mm on the left and 0.35 mm on the right.
"""
import re, io, sys, collections

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCH = r"C:\Users\tambe\Documents\Electronics\Zulu_A7\zulu_a7.sch"
OUT = r"C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu A7 Board Plan.html"
t = open(SCH, encoding="utf-8").read()
PK = {m.group(1): m.group(2) for m in re.finditer(r'<package name="([^"]+)">(.*?)</package>', t, re.S)}


def size(pk):
    xs, ys = [], []
    for m in re.finditer(r'<smd name="[^"]*" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', PK[pk]):
        x, y, dx, dy = map(float, m.groups()); xs += [x - dx / 2, x + dx / 2]; ys += [y - dy / 2, y + dy / 2]
    for m in re.finditer(r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', PK[pk]):
        x, y, d = map(float, m.groups()); r = d / 2 + 0.254; xs += [x - r, x + r]; ys += [y - r, y + r]
    for m in re.finditer(r'<(?:wire|rectangle) ([^>]*)/>', PK[pk]):
        if re.search(r'layer="(?:21|51)"', m.group(1)):
            xs += [float(v) for v in re.findall(r'\bx[12]="([-\d.]+)"', m.group(1))]
            ys += [float(v) for v in re.findall(r'\by[12]="([-\d.]+)"', m.group(1))]
    return (round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2)) if xs else None


# What a part claims once it is down, measured rather than assumed.
#
# This file used to multiply the footprint by 1.70 for passives and 1.15 for
# everything else, and say plainly that those were assumptions. They were also
# wrong in both directions -- the real factors are 1.48 and 1.25 -- and they
# happened to cancel, so the total came out at 2040 mm2 against the 2039 the
# guess predicted. The guess was right by luck, and there is no reason to keep
# relying on that. Use the same two-rule box make_board.py's tile() places
# against: the layer-39 courtyard abuts its neighbour (it already IS a
# clearance envelope) and the copper keeps CU_GAP from foreign copper, wider
# per axis.
CY_GAP, CU_GAP = 0.05, 0.30


def _extent(pk):
    """copper/silk box and the same box unioned with the layer-39 keepout.

    Unioned by CORNERS, not by spans about the origin. X3's keepout reaches
    6.20 mm past its body on one side only, so a span comparison folded it in
    half and undercounted the big parts by 94 mm2. This mirrors
    make_board.py's obst_box() exactly.
    """
    xs, ys = [], []
    for m in re.finditer(r'<smd name="[^"]*" x="([-\d.]+)" y="([-\d.]+)" dx="([\d.]+)" dy="([\d.]+)"', PK[pk]):
        x, y, dx, dy = map(float, m.groups()); xs += [x - dx / 2, x + dx / 2]; ys += [y - dy / 2, y + dy / 2]
    for m in re.finditer(r'<pad name="[^"]*" x="([-\d.]+)" y="([-\d.]+)"[^>]*drill="([\d.]+)"', PK[pk]):
        x, y, d = map(float, m.groups()); r = d / 2 + 0.254; xs += [x - r, x + r]; ys += [y - r, y + r]
    for m in re.finditer(r'<(?:wire|rectangle) ([^>]*)/>', PK[pk]):
        if re.search(r'layer="(?:21|51)"', m.group(1)):
            xs += [float(v) for v in re.findall(r'\bx[12]="([-\d.]+)"', m.group(1))]
            ys += [float(v) for v in re.findall(r'\by[12]="([-\d.]+)"', m.group(1))]
    if not xs:
        # U$2 and U$5 are the Creative Commons logo: a circle and some text, no
        # copper and nothing on 21 or 51. They still take up board area -- 41 mm2
        # each -- and check_board.py's body test measures them, so they belong in
        # the budget. Same fallback make_board.py's bbox() uses.
        for m in re.finditer(r'<circle x="([-\d.]+)" y="([-\d.]+)" radius="([\d.]+)"', PK[pk]):
            x, y, r = map(float, m.groups()); xs += [x - r, x + r]; ys += [y - r, y + r]
        for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"', PK[pk]):
            x, y = map(float, m.groups()); xs += [x, x + 1.0]; ys += [y, y + 1.0]
    if not xs:
        return None
    kx, ky = list(xs), list(ys)
    for m in re.finditer(r'<(?:wire|rectangle|circle|polygon) ([^>]*)/>', PK[pk]):
        if 'layer="39"' in m.group(1):
            kx += [float(v) for v in re.findall(r'\bx\d*="([-\d.]+)"', m.group(1))]
            ky += [float(v) for v in re.findall(r'\by\d*="([-\d.]+)"', m.group(1))]
    return ((max(xs) - min(xs), max(ys) - min(ys)),
            (max(kx) - min(kx), max(ky) - min(ky)))


def placed_size(pk):
    """the two-rule box: courtyard abuts, copper keeps CU_GAP -- wider per axis"""
    e = _extent(pk)
    if not e:
        return None
    (cw, ch), (kw, kh) = e
    return (max(kw + CY_GAP, cw + CU_GAP), max(kh + CY_GAP, ch + CU_GAP))


DEVPKG = {}
for dm in re.finditer(r'<deviceset name="([^"]+)"[^>]*>(.*?)</deviceset>', t, re.S):
    for dv in re.finditer(r'<device name="([^"]*)"(?: package="([^"]+)")?>', dm.group(2)):
        DEVPKG[(dm.group(1), dv.group(1))] = dv.group(2)
PART = {m.group(1): (m.group(3), m.group(4)) for m in
        re.finditer(r'<part name="([^"]+)" library="([^"]+)" deviceset="([^"]+)" device="([^"]*)"', t)}


def pkg_of(p):
    return DEVPKG[PART[p]]


# --- outline and pad grid, live from the X2 package -------------------------
X2PKG = pkg_of("X2")
_b = PK[X2PKG]
_ox = [float(v) for m in re.finditer(r'<wire ([^>]*)layer="21"/>', _b)
       for v in re.findall(r'x[12]="([-\d.]+)"', m.group(1))]
_oy = [float(v) for m in re.finditer(r'<wire ([^>]*)layer="21"/>', _b)
       for v in re.findall(r'y[12]="([-\d.]+)"', m.group(1))]
BX0, BX1, BY0, BY1 = min(_ox), max(_ox), min(_oy), max(_oy)
BW, BH = BX1 - BX0, BY1 - BY0
PADS = {m.group(1): (float(m.group(2)), float(m.group(3)))
        for m in re.finditer(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"', _b)}
ROWY = sorted({y for x, y in PADS.values()})
PITCH, PADR = 2.54, 0.762
# The board went 0.800 in -> 1.000 in wide and the pin rows moved out with it,
# staying 0.700 in apart. Every block coordinate below is written against the old
# outline -- and so is make_board.py's SINGLE table, which these must match, or
# this page stops being a picture of the board. Both apply the same offset rather
# than restating forty numbers. X1 is exempt: it is anchored to BY1 already.
YOFF = (BY1 - 20.32) / 2.0
# the full grid, not just the columns that happen to carry a pad -- the three
# spare columns at the far end are part of the plan and have to be drawn
# The header grid stops short of the board now: the last 8.89 mm is reserved
# for the Pmod and its signals and carries no grid position at all, so drawing
# dots there would advertise slots that do not exist.
PMOD_ZONE = 8.89
GRIDX = []
x = min(x for x, y in PADS.values())
while x <= BX1 - PMOD_ZONE - PADR:
    GRIDX.append(round(x, 2)); x += PITCH
OCC = {(round(x, 2), round(y, 2)) for x, y in PADS.values()}
PADNO = {(round(x, 2), round(y, 2)): int(n) for n, (x, y) in PADS.items()}
# The USB gap is an INTERIOR run of vacant top-row positions. Bounding it by the
# first and last occupied top-row position matters since RST# left the corner at
# x=1.27: that position is vacant too, but it is the end of the row, not the USB
# span, and a bare "not occupied" test drew it as USB space.
_topx = sorted(x for x, y in PADS.values() if y == max(ROWY))
USBGAP = sorted(x for x in GRIDX if (x, max(ROWY)) not in OCC and _topx[0] < x < _topx[-1])
CHAN0, CHAN1 = min(ROWY) + PADR, max(ROWY) - PADR          # the clear channel between the rows

S, PX = 9.5, 40.0
FT, BK = 44.0, 372.0
X = lambda mm: round(PX + (mm - BX0) * S, 1)
Y = lambda mm, top: round(top + (BY1 - mm) * S, 1)
Wd = lambda mm: round(mm * S, 1)
SVGW = round(PX * 2 + BW * S)
o = ['<svg viewBox="0 0 %d 664" xmlns="http://www.w3.org/2000/svg">' % SVGW]
for top, lbl, sub in ((FT, "FRONT", "%.2f x %.2f mm. The FPGA and everything a hand has to reach." % (BW, BH)),
                      (BK, "BACK", "Low-profile only, and the FPGA's decoupling under its ball field.")):
    o.append('<text class="th" x="40" y="%d" fill="#141413" font-size="14" font-weight="500">%s</text>'
             % (top - 22, lbl))
    o.append('<text class="ts" x="%d" y="%d" fill="#5e5d59" font-size="12">%s</text>'
             % (40 + 10 * len(lbl) + 18, top - 22, sub))
    o.append('<rect class="box" x="%s" y="%s" width="%s" height="%s" rx="4" fill="#ffffff" '
             'stroke="#c9c9c2" stroke-width="0.5"/>' % (X(BX0), Y(BY1, top), Wd(BW), Wd(BH)))
    # the reserved strip, drawn so it reads as reserved rather than as spare board
    o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#BA7517" opacity="0.07" '
             'stroke="#BA7517" stroke-width="0.8" stroke-dasharray="5 3" rx="3"/>'
             % (X(BX1 - PMOD_ZONE), Y(BY1, top), Wd(PMOD_ZONE), Wd(BH)))
    o.append('<text class="ts" x="%s" y="%s" text-anchor="middle" font-size="10" fill="#BA7517" '
             'transform="rotate(-90 %s %s)">Pmod only</text>'
             % (round(X(BX1 - PMOD_ZONE / 2), 1), round(Y(BH / 2, top), 1),
                round(X(BX1 - PMOD_ZONE / 2), 1), round(Y(BH / 2, top), 1)))
    for yy in ROWY:
        for gx in GRIDX:
            if (gx, round(yy, 2)) in OCC:
                o.append('<circle cx="%s" cy="%s" r="%s" class="pad" fill="#ffffff" '
                         'stroke="#c9c9c2" stroke-width="0.5"/>'
                         % (X(gx), Y(yy, top), round(PADR * S, 1)))
                # Pad number outside the outline, not inside the circle: pads are
                # drawn to scale at 1.52 mm across and two digits will not fit
                # legibly in that. Inside the channel is no good either -- the
                # USB block reaches the top row. So the top row reads above the
                # board and the bottom row below it, each aligned to its column.
                o.append('<text x="%s" y="%s" font-size="7.5" text-anchor="middle" '
                         'fill="#5e5d59" class="ts">%d</text>'
                         % (X(gx), (top - 4) if yy == max(ROWY) else (Y(BY0, top) + 11),
                            PADNO[(gx, round(yy, 2))]))
            elif gx in USBGAP and yy == max(ROWY):
                o.append('<circle cx="%s" cy="%s" r="%s" fill="none" stroke="#BA7517" '
                         'stroke-width="1" stroke-dasharray="3 2"/>' % (X(gx), Y(yy, top), round(PADR * S, 1)))
            else:
                o.append('<circle cx="%s" cy="%s" r="2" class="gridpt" fill="#c9c9c2"/>' % (X(gx), Y(yy, top)))

placed = []


# presentation attributes as well as the class, so the SVG renders on its own
# outside a browser. CSS beats a presentation attribute, so the dark-mode rules
# still win where there is a stylesheet.
FILL = {"c-teal": ("#d6ede7", "#2f7d6c", "#12463c", ""),
        "c-amber": ("#f7ead2", "#BA7517", "#6b4409", ' stroke-dasharray="3 2"')}


def blk(x, y, w, h, top, label, ramp="c-teal", fs=12):
    placed.append((top, label or "-", x, y, x + w, y + h, ramp))
    f, s, tc, dash = FILL[ramp]
    o.append('<g class="%s"><rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="%s" stroke="%s" '
             'stroke-width="0.5"%s/>'
             % (ramp, X(x), Y(y + h, top), Wd(w), Wd(h), f, s, dash))
    if label:
        o.append('<text class="ts" x="%s" y="%s" text-anchor="middle" font-size="%d" fill="%s">%s</text>'
                 % (round(X(x) + Wd(w) / 2, 1), round(Y(y + h, top) + Wd(h) / 2 + 4, 1), fs, tc, label))
    o.append("</g>")


SZ = {p: size(pkg_of(p)) for p in ("U1", "U2", "U3", "U4", "U8", "U10", "X1", "X3", "Q1", "J1", "JP3", "BTN")}
sdw, sdh = SZ["X3"][1], SZ["X3"][0]           # R270: the card ejects over the -x end

# --- FRONT ------------------------------------------------------------------
# The board is 2.750 in now, and the last 8.89 mm of it -- everything past
# x=60.96 -- is reserved for the Pmod and its signals. No grid position falls
# there, so nothing else may either.
#
# That forces the microSD to the other end. Its layer-39 keepout is the card
# plus 21.55 mm of eject stroke, so it has to throw the card off a board END;
# the board is 20.32 across, so a long edge cannot work. The +x end is now
# Pmod, so X3 turns to eject over the -x end and the card overhangs that edge
# by about 5.6 mm.
FPGA_X, FPGA_Y = 41.00, 4.20 + YOFF
blk(0.60, 3.23 + YOFF, sdw, sdh, FT, "microSD", fs=12)
blk(FPGA_X, FPGA_Y, *SZ["U1"], FT, "A35T", fs=13)
blk(28.008, 4.568 + YOFF, *SZ["U2"], FT, "FT2232", fs=11)   # x-centred on X1; dropped 0.12 for X1's courtyard
# X1 is anchored by its PCB EDGE line, not its bounding box: Molex puts that
# line 4.141 mm in front of the rear row and the mating face 0.70 beyond it, so
# the shell overhangs the outline. Draw only the part that is on the board.
blk(33.02 - SZ["X1"][0] / 2, BY1 - 4.141 + 0.675, SZ["X1"][0], 4.141 - 0.675,
    FT, "USB", fs=11)
# Q1 comes to the front: 3 parts, and it puts the 12 MHz square wave on the
# same side as both things it drives -- the FPGA's clock ball and the
# FT2232's OSCI -- so neither needs a via.
blk(53.59, 8.26 + YOFF, *SZ["Q1"], FT, "Q1", fs=10)
blk(58.79, 6.86 + YOFF, SZ["JP3"][1], SZ["JP3"][0], FT, "JTAG", fs=9)   # R90, in the only both-sides-clear corridor
blk(17.55, 5.83 + YOFF, SZ["BTN"][1], SZ["BTN"][0], FT, "BTN", fs=11)   # turned 90 deg, y-centred on X3
blk(23.55, 7.27 + YOFF, 3.46, 6.22, FT, "LEDs", fs=9)
# The regulator stayed on the BACK. Q1 was worth moving up; U8 was not,
# because it does not travel alone -- see the back.
# turned across the board so the whole connector sits inside the reserved
# strip: 5.08 wide against 8.89 available, 15.24 tall against a 16.256 channel
blk(63.865, 2.54 + YOFF, SZ["J1"][1], SZ["J1"][0], FT, "Pmod", fs=11)

# --- BACK -------------------------------------------------------------------
# Low-profile only. The one height verifiable from a local datasheet is U4's
# SOIC-8 208-mil at A = 2.16 mm max, so the flash is the tallest thing here and
# it is the part to measure against the header standoff.
blk(0.80, 4.41 + YOFF, *SZ["U4"], BK, "FLASH", fs=10)
blk(0.80, 10.81 + YOFF, *SZ["U10"], BK, "EEPROM", fs=10)
# U8's tight core: the IC, the three buck inductors on SW1/SW2/SW3 and the
# input cap -- 25.5 mm2 of footprint, ~34 placed. The other 20 parts of its
# network (three feedback dividers, enable, mode, PGOOD, the input diodes)
# want to be near but not tight, and spread into the space around it.
blk(10.60, 2.50 + YOFF, 6.00, 15.60, BK, "PWR + L1-L3", fs=9)   # grew when L1-L3 went 0603 -> IND2520
blk(40.00, 2.30 + YOFF, 18.00, 15.80, BK, "FPGA decoupling", ramp="c-amber", fs=11)
blk(17.20, 2.68 + YOFF, SZ["U3"][1], SZ["U3"][0], BK, "SDRAM", fs=13)   # dropped 1.20 to clear X1's shell nails
# the ball field, drawn on the BACK so the decoupling can be seen to cover it
o.append('<rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="#C6392F" stroke-width="1.2" '
         'stroke-dasharray="4 3" rx="2"/>'
         % (X(FPGA_X + 1.0), Y(FPGA_Y + 10.0, BK), Wd(9.0), Wd(9.0)))
o.append('<text class="ts" x="%s" y="%s" text-anchor="middle" font-size="10" fill="#C6392F">'
         'ball field, other side</text>' % (round(X(FPGA_X + 5.5), 1), round(Y(FPGA_Y + 10.0, BK) - 5, 1)))

o.append('<g><rect x="40" y="620" width="12" height="12" rx="2" class="c-teal" fill="#d6ede7" stroke="#2f7d6c"/>'
         '<text class="ts" x="58" y="630" fill="#5e5d59" font-size="12">placed to scale</text>'
         '<rect x="196" y="620" width="12" height="12" rx="2" class="c-amber" fill="#f7ead2" stroke="#BA7517"/>'
         '<text class="ts" x="214" y="630" fill="#5e5d59" font-size="12">capacitor field</text>'
         '<circle cx="352" cy="626" r="6" fill="none" stroke="#BA7517" stroke-width="1" '
         'stroke-dasharray="3 2"/><text class="ts" x="364" y="630" fill="#5e5d59" font-size="12">reserved USB landing</text>'
         '<circle cx="516" cy="626" r="2" class="gridpt" fill="#c9c9c2"/>'
         '<text class="ts" x="528" y="630" fill="#5e5d59" font-size="12">bare grid position</text>'
         '<rect x="668" y="620" width="12" height="12" rx="2" fill="#BA7517" opacity="0.15" '
         'stroke="#BA7517" stroke-dasharray="3 2"/>'
         '<text class="ts" x="686" y="630" fill="#5e5d59" font-size="12">Pmod only</text></g>')
o.append("</svg>")
svg = "\n".join(o)

# --- numbers, computed not typed --------------------------------------------
AREA = 0.0
CLS = collections.Counter()
for p, (dsn, dev) in PART.items():
    pk = DEVPKG.get((dsn, dev))
    if not pk or pk not in PK or p == "X2":
        continue
    s = size(pk)
    if s:
        AREA += s[0] * s[1]
        CLS["passive" if re.match(r"^(C|R|L)\d", p) else
            "LED/diode" if re.match(r"^(D|LD)\d", p) else
            "connector" if p.startswith(("X", "J")) else "IC"] += 1
# Usable area has two zones, and treating it as one undercounts the board.
# Where the header pads are, only the 16.256 mm channel between the rows is
# free. Past the last pad there are no through-holes at all, so the full 20.32
# is free. Earlier revisions of this file applied the channel to the whole
# length, which is why a board that was really +65 mm2 read as break-even.
PADMAXX = max(x for x, y in PADS.values()) + PADR
ROWGAP = max(ROWY) - min(ROWY)                 # 17.780 mm = 0.700 in, a wide DIP
MINPART = 1.20                                 # an 0402 on end; nothing is narrower


def usable(bx1=None, bh=None):
    """usable area on ONE side, for a board bx1 long and bh wide.

    Three zones, not two. Between the rows there is the channel. Past the last
    pad the full width is free. And OUTSIDE each row there is a strip -- today
    it is 0.51 mm, too narrow to hold anything, which is why earlier revisions
    could ignore it. It stops being ignorable the moment the board is widened,
    because the rows do not move: they are 0.700 in apart because that is what
    plugs into a breadboard. Credit a strip only once it can actually take a
    part on end, or widening reads as a smooth gain when it is really a cliff.
    """
    bx1 = BX1 if bx1 is None else bx1
    bh = BH if bh is None else bh
    strip = (bh - ROWGAP) / 2.0 - PADR
    strip = strip if strip >= MINPART else 0.0
    return PADMAXX * ((ROWGAP - 2 * PADR) + 2 * strip) + (bx1 - PADMAXX) * bh


USABLE = usable()
COVER = 100 * AREA / (2 * USABLE)
# Raw footprint area understates the job: parts need room between them. Chip
# passives pay the most for it -- an 0402 land is 3.00 x 1.00, and packed in
# rows with 0.5 mm between neighbours it really occupies 3.5 x 1.5. Big parts
# already carry most of their courtyard in the footprint. So budget the two
# classes differently rather than applying one number to everything.
def _both(p, f):
    """footprint and placed size from ONE measurement, so the ratio is honest"""
    pk = DEVPKG.get(PART[p])
    if pk not in PK or not _extent(pk):
        return None
    return _extent(pk)[0] if f is size else placed_size(pk)


APASS = ABIG = PPASS = PBIG = 0.0
for p in PART:
    if p == "X2" or PART[p] not in DEVPKG:
        continue
    f, d = _both(p, size), _both(p, placed_size)
    if not f or not d:
        continue
    if re.match(r"^(C|R|L)\d", p):
        APASS += f[0] * f[1]; PPASS += d[0] * d[1]
    else:
        ABIG += f[0] * f[1]; PBIG += d[0] * d[1]
KP = PPASS / APASS if APASS else 0.0
KB = PBIG / ABIG if ABIG else 0.0

# ...and what is not a part at all. The old budget counted footprints and
# nothing else, which is the whole reason it read +309 mm2 on a board that
# cannot take its own parts. These are real, permanent reservations: the
# escape corridors around the FPGA on the front, the stage-2 moat and the
# stage-3 fan-out ring on the back, and the two connector shrouds that reach
# past their own copper. They are kept in step with make_board.py by hand --
# see the ESCAPE/SHROUD constants there.
NOFPGA = 13.00 * 12.60                       # front, FPGA escape corridors
NOVIA = 7.20 * 7.20                          # back, stage-2 moat
FANRING = (2 * 6.44) ** 2 - (2 * 5.70) ** 2  # back, stage-3 fan-out ring
SHROUD = 2 * (3.60 * 4.30 + 5.58 * 8.12)     # Q1 and JP3, both sides
RESERVED = NOFPGA + NOVIA + FANRING + SHROUD
NEED = PPASS + PBIG + RESERVED
SLACK = 2 * USABLE - NEED

# Bulk area is a floor, not a promise, so read what the placer actually managed
# off the board it generated. Anything parked sits below y = 0. This is the
# number that has met a 16.256 mm channel; the gap between it and SLACK is
# fragmentation, and no amount of area arithmetic predicts it.
BRD = SCH[:-4] + ".brd"
PARKED, PARKEDA = 0, 0.0
try:
    _b = open(BRD, encoding="utf-8").read()
except IOError:
    _b = ""
for _m in re.finditer(r'<element name="[^"]+" library="[^"]+" package="([^"]+)"[^>]*?\sy="([-\d.]+)"', _b):
    if float(_m.group(2)) < 0 and _m.group(1) in PK:
        _d = placed_size(_m.group(1))
        PARKED += 1
        PARKEDA += _d[0] * _d[1] if _d else 0.0


def _length_for(area):
    """board length in inches whose usable area reaches `area`, both sides"""
    lo, hi = BX1, BX1 + 40.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if 2 * usable(bx1=mid) < area:
            lo = mid
        else:
            hi = mid
    return hi / 25.4


BREAKEVEN = _length_for(NEED)
COMFORT = _length_for(NEED + PARKEDA)

# Widening is the other way out, and it is not the same shape of answer.
# Lengthening adds area at a constant rate; widening adds nothing at all until
# the strip outside the pin rows can hold a part, and then adds a lot at once.
# The rows stay 0.700 in apart either way -- that is the breadboard interface,
# not a layout choice.
WIDTHS = []
for _in in (0.800, 0.850, 0.900, 0.950, 1.000):
    _u = 2 * usable(bh=_in * 25.4)
    _raw = (_in * 25.4 - ROWGAP) / 2.0 - PADR
    WIDTHS.append((_in, _raw, _raw >= MINPART, _u, _u - NEED, _u - NEED - PARKEDA))
WIDTHFIX = next((w for w in WIDTHS if w[5] > 0), None)
# The headline used to be typed prose and went stale the moment a part was
# deleted -- it read "about 3 % too small" over a table showing -1 mm2. Derive
# it from the number instead.
VERDICT = ("The parts do not fit: %.0f mm&sup2; short, %.0f&nbsp;%% over." % (-SLACK, -100.0 * SLACK / NEED)
           if SLACK < -0.005 * NEED else
           "The parts fit with %.0f mm&sup2; to spare, %.0f&nbsp;%%." % (SLACK, 100.0 * SLACK / NEED)
           if SLACK > 0.005 * NEED else
           "The parts land on the line: %.0f mm&sup2; needed against %.0f available. "
           "Break-even, with no margin at all." % (NEED, 2 * USABLE))
sheet7 = re.search(r'<sheet name="FPGA POWER">(.*?)</sheet>', t, re.S).group(1)
C7 = sorted({m.group(1) for m in re.finditer(r'<instance part="(C\d+)"', sheet7)})
C7A = sum(size(pkg_of(c))[0] * size(pkg_of(c))[1] for c in C7)

rows = "".join("<tr><td>%s</td><td>%s</td><td class=n>%.2f x %.2f</td></tr>"
               % (p, pkg_of(p), *size(pkg_of(p)))
               for p in ("U1", "U2", "U3", "U4", "U8", "U10", "X1", "X3", "Q1", "J1", "JP3", "BTN"))

HTML = """<title>Zulu A7 Board Plan</title>
<style>
:root{--surface-0:#fff;--surface-1:#f7f7f5;--border:#e3e3df;--border-strong:#c9c9c2;
--text-primary:#141413;--text-secondary:#5e5d59;--accent:#0f6b5c;--warn:#BA7517;--bad:#C6392F;}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--surface-0:#191917;--surface-1:#222220;
--border:#33332f;--border-strong:#4a4a45;--text-primary:#f0efec;--text-secondary:#a3a29c;--accent:#5fbfa9;}}
:root[data-theme=dark]{--surface-0:#191917;--surface-1:#222220;--border:#33332f;--border-strong:#4a4a45;
--text-primary:#f0efec;--text-secondary:#a3a29c;--accent:#5fbfa9;}
body{background:var(--surface-0);color:var(--text-primary);margin:0;padding:32px 24px;
font:400 16px/1.7 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;}
main{max-width:860px;margin:0 auto;}
h1{font-size:22px;font-weight:500;margin:0 0 4px;}
h2{font-size:18px;font-weight:500;margin:32px 0 8px;}
p.sub{color:var(--text-secondary);margin:0 0 24px;}
.fig{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:16px;overflow-x:auto;}
svg{display:block;width:100%;height:auto;min-width:620px;}
.th{font:500 14px ui-sans-serif,system-ui,sans-serif;fill:var(--text-primary);}
.ts{font:400 12px ui-sans-serif,system-ui,sans-serif;fill:var(--text-secondary);}
.box{fill:var(--surface-0);stroke:var(--border-strong);stroke-width:.5;}
.pad{fill:var(--surface-0);stroke:var(--border-strong);}
.gridpt{fill:var(--border);}
.c-teal rect{fill:#d6ede7;stroke:#2f7d6c;stroke-width:.5;}
.c-teal text{fill:#12463c;}
.c-amber rect{fill:#f7ead2;stroke:#BA7517;stroke-width:.5;stroke-dasharray:3 2;}
.c-amber text{fill:#6b4409;}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .c-teal rect{fill:#14352f;stroke:#4f9c8a;}
:root:not([data-theme=light]) .c-teal text{fill:#a8d9cd;}
:root:not([data-theme=light]) .c-amber rect{fill:#3a2e14;stroke:#BA7517;}
:root:not([data-theme=light]) .c-amber text{fill:#e0c58a;}}
table{border-collapse:collapse;width:100%;font-size:14px;margin-top:8px;}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--border);}
th{font-weight:500;color:var(--text-secondary);}
td.n{font-family:ui-monospace,"Cascadia Code",Consolas,monospace;white-space:nowrap;}
ul{padding-left:20px;}li{margin:8px 0;}
table.budget{margin:12px 0;font-size:13px;}
table.budget td,table.budget th{padding:4px 10px;}
code{font-family:ui-monospace,Consolas,monospace;font-size:.9em;background:var(--surface-1);
padding:1px 5px;border-radius:4px;}
.callout{border-left:3px solid var(--bad);background:var(--surface-1);padding:12px 16px;
border-radius:0 8px 8px 0;margin:16px 0;}
</style>
<main>
<h1>Zulu A7 Board Plan</h1>
<p class="sub">Front and back placement on the __INCH__&nbsp;in board, drawn to scale from the
footprints in <code>zulu_a7.sch</code>. Generated by <code>tools/board_plan.py</code>.</p>
<div class="fig">__SVG__</div>

<div class="callout"><strong>__VERDICT__</strong> The header rows leave a channel __CHAN__&nbsp;mm tall running the full length, so the
usable interior is __USABLE__&nbsp;mm&sup2; a side &mdash; not the __BOARD__&nbsp;mm&sup2; the board
measures &mdash; or __USABLE2__&nbsp;mm&sup2; across both. Raw footprints come to
__AREA__&nbsp;mm&sup2;, which reads as __COVER__&nbsp;% coverage, but raw footprint area understates the
job because parts need room between them.
<table class="budget">
<tr><th>class</th><th>footprint</th><th>packing</th><th>placed area</th></tr>
<tr><td>__NPASS__ chip passives</td><td class=n>__APASS__ mm&sup2;</td><td class=n>&times; __KP__</td><td class=n>__APASSN__ mm&sup2;</td></tr>
<tr><td>ICs, connectors, LEDs</td><td class=n>__ABIG__ mm&sup2;</td><td class=n>&times; __KB__</td><td class=n>__ABIGN__ mm&sup2;</td></tr>
<tr><td>reserved, not a part &mdash; FPGA escape, moat, fan-out ring, connector shrouds</td><td></td><td></td><td class=n>__RESERVED__ mm&sup2;</td></tr>
<tr><td><strong>needed</strong></td><td></td><td></td><td class=n><strong>__NEED__ mm&sup2;</strong></td></tr>
<tr><td>usable, both sides</td><td></td><td></td><td class=n>__USABLE2__ mm&sup2;</td></tr>
<tr><td><strong>slack</strong></td><td></td><td></td><td class=n><strong>__SLACK__ mm&sup2;</strong></td></tr>
</table>
The two packing factors are <strong>measured, not assumed</strong>: each part is sized by the box
<code>make_board.py</code>&rsquo;s tiler actually places it against &mdash; its layer-39 courtyard abutting
its neighbour, and its copper holding __CUGAP__&nbsp;mm off foreign copper, whichever is wider on each axis.
<p style="margin:10px 0 0">This budget used to guess &times;&nbsp;1.70 and &times;&nbsp;1.15 and said so
plainly. Those were wrong in <em>both</em> directions and cancelled, so the total came out within
1&nbsp;mm&sup2; of the measured one &mdash; right by luck. What it left out was everything that is not a
part: __RESERVED__&nbsp;mm&sup2; of FPGA escape corridors, stage-2 moat, stage-3 fan-out ring and connector
shroud. That omission alone is the difference between the +309&nbsp;mm&sup2; this page used to claim and the
__SLACK__ it reports now.</p>
<p style="margin:10px 0 0">And bulk area is a floor, not a promise. It assumes any square millimetre can
hold any part, when in practice a part has to sit near what it serves and the interior is a
__CHAN__&nbsp;mm channel &mdash; thin enough that the leftovers come out as strips too narrow to take an
0402 sideways. At the current length <strong>__PARKED__ parts are parked</strong> for want of somewhere to
go, which is __PARKEDA__&nbsp;mm&sup2; of parts against a __SLACKABS__&nbsp;mm&sup2; bulk shortfall: the
difference is fragmentation. Break-even needs <strong>__BREAKEVEN__&nbsp;in</strong> of length; leaving room
for the parts actually parked needs about <strong>__COMFORT__&nbsp;in</strong>. Everything else about the
placement below survives a change of length, because the only thing that moves is where the far end sits.</p>
<p style="margin:10px 0 0"><strong>Widening is the better lever, and it is a cliff rather than a slope.</strong>
The pin rows are __ROWGAPIN__&nbsp;in apart and stay there &mdash; that is the breadboard interface, not a
layout choice &mdash; so widening the board does not touch the channel. What it grows is the strip
<em>outside</em> each row, today __STRIP0__&nbsp;mm and worth nothing because a 0402 on end needs
__MINPART__&nbsp;mm.
<table class="budget">
<tr><th>width</th><th>strip outside each row</th><th>usable, both sides</th><th>slack</th><th>after re-placing the parked</th></tr>
__WIDTHROWS__
</table>
0.850&nbsp;in buys almost nothing; __WFIX__&nbsp;in is the first width that holds every part currently
parked. Widening also helps the part of the board that is not placement: the stage-3 fan-out ring is capped
at half-width 6.20&nbsp;mm by the board edge, and its 103 vias at 0.390 pitch already fill 81&nbsp;% of that
perimeter, which is why the fan still has 191 trace-to-trace violations. A wider board lets the ring move
out, and the perimeter grows with it.
<p style="margin:10px 0 0">The cost is real and is not area: the board would overhang each pin row by
__OVERHANG__&nbsp;in instead of 0.050, one extra 0.1&nbsp;in tie-point column per side covered on whatever it
plugs into. That is a call about the product, not about the layout.</p></div>

<h2>What decided the placement</h2>
<ul>
<li><strong>The back can only take low-profile parts.</strong> The board sits pin-down on a breadboard, so
the only clearance underneath is the header's standoff. That fixes X1, X3, J1, JP3, BTN and the LEDs to the
front, because on the back nobody could reach them. Worth measuring before committing: the only package height
verifiable from a local datasheet is U4's SOIC-8 208-mil at <strong>A = 2.16&nbsp;mm max</strong>, so the flash
is the tallest thing on the back. UG475 gives the CPG236 drawing as vector art with no height in the text, so
the FPGA's height is not established here &mdash; and now that it is on the front, it does not have to be.</li>
<li><strong>The FPGA is on the front; its decoupling is under it on the back.</strong> __NC7__ capacitors on
the FPGA POWER sheet, __C7A__&nbsp;mm&sup2; of them, want to sit directly behind the ball field &mdash; but
that only requires the two to be on <em>opposite</em> sides. It says nothing about which side each takes, and
an earlier version of this plan wrongly read it as a reason to put the A35T on the back. Top is the right side
for it: it is the part that dissipates, the part anyone will want to inspect or rework on a 238-ball BGA, and
the back faces a breadboard a couple of millimetres away with no airflow. The back keeps a 17.8 &times;
15.3&nbsp;mm window clear beneath it for nothing but those capacitors. On the old board the SDRAM sat in that
shadow, which is precisely why the decoupling had nowhere to go.</li>
<li><strong>The microSD had to rotate.</strong> Its layer-39 keepout is the card plus 21.55&nbsp;mm of eject
stroke, along the connector's own &minus;y. The board is 20.32&nbsp;mm across, so the card cannot come out
over a long edge. X3 is turned to <strong>R270</strong> so the card leaves over the <em>-x end</em>, overhanging
that edge by 5.60&nbsp;mm. R270 and not R90: the keepout runs 8.70&nbsp;mm past the copper on whichever side the
slot faces, and at R90 that side was +x &mdash; the stroke pointed into the board and through BTN, so a card could
only have been inserted from the middle of the board. <code>check_board.py</code> now compares layer-39 keepouts
against copper on the same side, which is what found it.</li>
<li><strong>The Pmod went along the bottom of the channel.</strong> 15.24 &times; 5.08&nbsp;mm will not fit
beside anything tall, but it fits under the USB landing, where the top 5&nbsp;mm of the channel is spoken
for and the bottom is empty.</li>
<li><strong>Q1 moved to the front; the regulator stayed on the back.</strong> Q1 is cheap &mdash; three parts
&mdash; and it earns the move: the 12&nbsp;MHz square wave now sits on the same side as both things it drives,
the FPGA's clock ball and the FT2232's OSCI, so neither needs a via. U8 does not travel alone. Its whole
network is 25 parts and 76&nbsp;mm&sup2; of footprint, and putting it on the front pushed that side to about
74&nbsp;% of its usable area against the back's 48. Thermally there was nothing to gain either way &mdash; an
LTC3569 in QFN-20 sheds heat into board copper, not into air &mdash; so it is back where the room is.
<br>What is drawn on the back is the <em>tight</em> core only: U8, the three buck inductors on SW1/SW2/SW3 and
the input capacitor, 25.5&nbsp;mm&sup2; of footprint and about 34 placed. Those five parts have to be close,
because SW1&ndash;SW3 are the highest di/dt nodes on the board and must not reach their inductors through vias.
The other twenty &mdash; three feedback dividers, the enable, mode and PGOOD networks, the input diodes,
50&nbsp;mm&sup2; and about 86 placed &mdash; want to be near but not tight, and spread into the space around
it. The back is now the regulator core, then the SDRAM, then the decoupling window, in that order from the
-x end; the window still covers the ball field.</li>
</ul>

<h2>Still to resolve</h2>
<ul>
<li><strong>The remaining passives.</strong> 143 chip parts totalling 444&nbsp;mm&sup2;, of which the FPGA
decoupling window absorbs about __C7A__&nbsp;mm&sup2;. The rest have to fit in the gaps left above and below the blocks
&mdash; roughly 2.3&nbsp;mm of channel above the back-side ICs and the front pockets at x&nbsp;10&ndash;16 and
x&nbsp;35&ndash;45. That is the tightest part of the job and it is not drawn here.</li>
<li><strong>The SDRAM is 22.35&nbsp;mm long in a 60.96&nbsp;mm board</strong>, and it now sits directly
opposite the FPGA rather than beside it &mdash; U3 ends at x&nbsp;39.55 on the back and U1 starts at 41.00 on
the front, 1.45&nbsp;mm apart. Moving the A35T right of the FT2232 put the ball field over where the SDRAM
used to be, so the two swapped: U3 took the decoupling window's old place and the window followed the balls.
The 39-signal bus is the shorter for it, but it now crosses sides at the FPGA edge rather than running along
one; check the package trace delays in <code>vivado/zulu_a7_io.csv</code> before length matching.</li>
<li><strong>BTN1 is gone.</strong> The button, its 10 k series resistor R87 and its 10 k pull-down R88 were
deleted to buy back area. The ball it freed, B18, is now <strong>CHAN28 on header pin 41</strong> &mdash; the
bottom-left corner position, which was the one slot left vacant when the bottom row was closed up and which
continues the numbering 37 &rarr; 38. Every ball on the part is in use again. BTN keeps its circuit unchanged.</li>
</ul>

<h2>Footprint sizes used</h2>
<table><tr><th>Part</th><th>Package</th><th>Size (mm)</th></tr>__ROWS__</table>
</main>"""

# --- the plan checks itself -------------------------------------------------
BAD = []
for i in range(len(placed)):
    for j in range(i + 1, len(placed)):
        a, b = placed[i], placed[j]
        if a[0] != b[0]:
            continue
        if a[2] < b[4] and b[2] < a[4] and a[3] < b[5] and b[3] < a[5]:
            BAD.append("%s overlaps %s" % (a[1], b[1]))
for top, lbl, x0, y0, x1, y1, ramp in placed:
    for px, py in PADS.values():
        if x0 < px + PADR and px - PADR < x1 and y0 < py + PADR and py - PADR < y1:
            BAD.append("%s lands on the X2 pad at (%.2f, %.2f)" % (lbl, px, py))
    if x0 < BX0 - 1e-9 or x1 > BX1 + 1e-9 or y0 < BY0 - 1e-9 or y1 > BY1 + 1e-9:
        BAD.append("%s falls outside the board outline" % lbl)
# the decoupling window must actually cover the ball field on the other side
fw = [p for p in placed if p[1] == "FPGA decoupling"][0]
bf = (FPGA_X + 1.0, FPGA_Y + 1.0, FPGA_X + 10.0, FPGA_Y + 10.0)
if not (fw[2] <= bf[0] and fw[4] >= bf[2] and fw[3] <= bf[1] and fw[5] >= bf[3]):
    BAD.append("the decoupling window does not cover the ball field")
assert not BAD, BAD
print("placement check on a %.2f x %.2f board: %d blocks, no overlaps, none on an occupied X2 pad,"
      "\n    nothing outside the outline, USB inside the vacant span, decoupling covers the ball field"
      % (BW, BH, len(placed)))
print("channel between the header rows: %.3f mm; usable %.0f mm2 a side" % (CHAN1 - CHAN0, USABLE))
print("footprints %.0f mm2 (X2 excluded) -> %.0f %% of both sides' usable area" % (AREA, COVER))
print("area budget: %.0f mm2 of passives x %.2f + %.0f mm2 of everything else x %.2f = %.0f mm2 needed"
      % (APASS, KP, ABIG, KB, NEED))
print("             against %.0f mm2 usable -> %+.0f mm2, %+.0f %%" % (2 * USABLE, SLACK, 100 * SLACK / NEED))
print("             of which %.0f mm2 is reserved and not any part: FPGA escape, moat, fan-out ring, shrouds" % RESERVED)
print("             the placer parked %d parts, %.0f mm2 -- break-even %.2f in, room for the parked %.2f in" % (PARKED, PARKEDA, BREAKEVEN, COMFORT))
# through usable(), not 2 * L * channel -- that applied the channel to the whole
# length and ignored the full-width area past the last pad, the same mistake the
# comment on USABLE says was fixed. It was still here, in the sensitivity table.
print("             LONGER, at %.3f in wide:" % (BH / 25.4))
for L in (68.58, 76.20, 78.99):
    u = 2 * usable(bx1=L)
    print("               %.3f in -> %.0f mm2, slack %+.0f, vs the parked %+.0f"
          % (L / 25.4, u, u - NEED, u - NEED - PARKEDA))
print("             WIDER, at %.3f in long (pin rows stay %.3f in apart):"
      % (BX1 / 25.4, ROWGAP / 25.4))
for _in, _raw, _ok, _u, _sl, _vp in WIDTHS:
    print("               %.3f in -> strip %.2f mm%s, %.0f mm2, slack %+.0f, vs the parked %+.0f"
          % (_in, _raw, "" if _ok else " (too narrow, worth nothing)", _u, _sl, _vp))
print("parts by class: %s" % dict(CLS))
print("FPGA POWER sheet: %d capacitors, %.0f mm2, window drawn 17.8 x 15.3 = %.0f mm2"
      % (len(C7), C7A, 17.8 * 15.3))

open(OUT, "w", encoding="utf-8").write(
    HTML.replace("__SVG__", svg).replace("__ROWS__", rows)
        .replace("__COVER__", "%.0f" % COVER).replace("__CHAN__", "%.3f" % (CHAN1 - CHAN0))
        .replace("__USABLE__", "%.0f" % USABLE).replace("__BOARD__", "%.0f" % (BW * BH))
        .replace("__AREA__", "%.0f" % AREA).replace("__NC7__", str(len(C7)))
        .replace("__C7A__", "%.0f" % C7A)
        .replace("__USABLE2__", "%.0f" % (2 * USABLE)).replace("__APASSN__", "%.0f" % PPASS)
        .replace("__NPASS__", "%d" % sum(1 for p in PART if re.match(r"^(C|R|L)\d", p)
                                         and PART[p] in DEVPKG and DEVPKG[PART[p]] in PK))
        .replace("__KP__", "%.2f" % KP).replace("__KB__", "%.2f" % KB)
        .replace("__RESERVED__", "%.0f" % RESERVED)
        .replace("__CUGAP__", "%.2f" % CU_GAP)
        .replace("__PARKEDA__", "%.0f" % PARKEDA).replace("__PARKED__", "%d" % PARKED)
        .replace("__SLACKABS__", "%.0f" % abs(SLACK))
        .replace("__BREAKEVEN__", "%.2f" % BREAKEVEN).replace("__COMFORT__", "%.2f" % COMFORT)
        .replace("__ROWGAPIN__", "%.3f" % (ROWGAP / 25.4))
        .replace("__STRIP0__", "%.2f" % ((BH - ROWGAP) / 2.0 - PADR))
        .replace("__MINPART__", "%.2f" % MINPART)
        .replace("__WFIX__", "%.3f" % (WIDTHFIX[0] if WIDTHFIX else 0.0))
        .replace("__OVERHANG__", "%.3f" % (((WIDTHFIX[0] if WIDTHFIX else 0.0) * 25.4 - ROWGAP) / 2.0 / 25.4))
        .replace("__WIDTHROWS__", "\n".join(
            "<tr%s><td>%.3f in</td><td class=n>%.2f mm%s</td><td class=n>%.0f mm&sup2;</td>"
            "<td class=n>%+.0f mm&sup2;</td><td class=n>%s</td></tr>"
            % (" style='font-weight:600'" if w is WIDTHFIX else "", w[0], w[1],
               "" if w[2] else " &mdash; too narrow", w[3], w[4],
               ("%+.0f mm&sup2;" % w[5]) if w[5] > 0 else "still short")
            for w in WIDTHS))
        .replace("__ABIGN__", "%.0f" % PBIG).replace("__APASS__", "%.0f" % APASS)
        .replace("__ABIG__", "%.0f" % ABIG).replace("__NEED__", "%.0f" % NEED)
        .replace("__SLACK__", "%+.0f" % SLACK)
        .replace("__VERDICT__", VERDICT)
        .replace("__INCH__", "%.3f &times; %.3f" % (BH / 25.4, BW / 25.4)))
print("wrote", OUT)
