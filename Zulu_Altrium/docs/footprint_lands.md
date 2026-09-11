# Footprint land patterns

Where every pad in the eight footprints drawn on 2026-09-10 comes from. Each was read out of the
manufacturer's datasheet by one agent and then re-derived from the same primary source by a second
told to refute it, not to confirm it (workflow `zulu-footprint-lands`). Six came back CONFIRMED,
one CORRECTED, and none rejected. Geometry is in millimetres with the origin at the body centre,
viewed from the top.

| Footprint | Used by | Pads | Basis | Verdict |
|---|---|---|---|---|
| `742C043` | R1 - CTS 742C043, two isolated elements | 4 | recommended land | CONFIRMED |
| `742C163` | R4 - CTS 742C163, eight isolated elements | 16 | recommended land | CONFIRMED |
| `DM3D-SF` | X3 - Hirose DM3D-SF microSD socket | 14 | recommended land | CONFIRMED |
| `FT2232HL-LQFP64` | U2 - FTDI FT2232HL USB bridge | 64 | **derived** | CONFIRMED |
| `JST-B2B-PH-SM4-TB` | X4 - JST PH 2-circuit top-entry SMT header, the LiPo connector | 4 | recommended land | CONFIRMED |
| `PTS810` | BTN - C&K/Littelfuse PTS810SJM250SMTR LFS tact switch | 4 | recommended land | CONFIRMED |
| `SOT23-5` | U5, U6, U7 - Semtech SC189 bucks | 5 | recommended land | CONFIRMED |
| `VQFN16-3X3-RGT` | U8 - TI bq24232 charger and power path | 17 | recommended land | CORRECTED |

## 742C043

**R1 - CTS 742C043, two isolated elements** &middot; 4 pads &middot; body 1.600 x 1.600 mm &middot; verdict CONFIRMED

Source: zulu_a7.brd (EAGLE package 742C083) and zulu_a7.sch (device 742, package 742C083, connects block). p6, Mechanical Specifications - "Recommended Pad Layout". manufacturer recommended land.

### Pin 1 and numbering

Pad 1 is the BOTTOM-LEFT pad viewed from the top (component side), at (-0.40, -0.85); numbering then runs
counter-clockwise - pad 2 bottom-right, pad 3 top-right, pad 4 top-left - so pad 4 is directly opposite pad 1
and the element pairs are (1,4) and (2,3).
What this was confirmed against:
1. The EAGLE package 742C083 read out of C:\Users\tambe\Documents\Electronics\Zulu_A7\zulu_a7.brd, which was
already verified against CTS: pads 1,2,3,4 run left-to-right along the bottom row (x = -0.4, 0.4, 1.2, 2.0 at
y = -0.9) and pads 5,6,7,8 run right-to-left along the top row (x = 2.0, 1.2, 0.4, -0.4 at y = +0.9). That is
counter-clockwise from bottom-left, so pad n faces pad (9-n).
2. The matching EAGLE device in zulu_a7.sch, which wires the four resistor gates as <connect gate="A" pin="1"
pad="1"/> / <connect gate="A" pin="2" pad="8"/>, then B=(2,7), C=(3,6), D=(4,5) - i.e. element n = pad n with
pad (9-n), each element occupying one column. Scaling that rule from 8 pads to 4 gives element n = pad n with
pad (5-n), i.e. (1,4) and (2,3).
3. The CTS datasheet's own 742C043 cell on page 4 ("Circuit Types [Schematics]"), which draws two isolated
resistors each running vertically from a bottom termination to the termination directly above it - confirming
the two elements are column-wise (top-to-bottom), never diagonal. Combined with counter-clockwise numbering
this forces pad 4 opposite pad 1.
Note: CTS does not print pin numbers anywhere in DOC# 008-0335-0; the numbering is a convention, and the part
itself is electrically symmetric (2 isolated equal elements), so there is no mandatory rotation on the board.

### Cautions carried forward

1. The CTS recommended pad layout table is per PACKAGE CODE, not per part number - the row is literally "742",
covering 742C043, 742X083, 742C083 and 742C163 alike. All 742-code parts share P = 0.80 and W = 1.60, so the
same land applies; the only thing that changes between them is how many columns you instantiate (2 here). This
is the manufacturer's own grouping, not an assumption of mine.
2. This land is slightly TIGHTER than the EAGLE 742C083 cell already in zulu_a7.brd. EAGLE uses 0.5 x 0.9 pads
at y = +/-0.9 (span 2.70, gap 0.90); CTS recommends 0.45 x 0.9 at y = +/-0.85 (span 2.60, gap 0.80). I used
the CTS numbers per the "prefer the manufacturer's recommended land" rule. If you want the two footprints in
this project to match the existing EAGLE-derived 742C083 exactly, widen to dx = 0.50 and push the rows out to
y = +/-0.90 - both are fine for a 0.8 mm pitch concave array, and the EAGLE variant gives a little more toe
fillet. Do not mix: pick one and use it for both R arrays.
3. The pads overhang the body ends in Y by 0.45 mm (pad outer edge 1.30 vs body half-width 0.80) and sit
inside the body in X (pad outer edge 0.625 vs body half-length 0.80). That is correct and intended for concave
(Type C) terminations - the fillet climbs the castellation.
4. CTS gives no solder-paste or solder-mask recommendation in DOC# 008-0335-0. Use your normal 1:1 paste on a
0.45 x 0.90 pad (or a small reduction if you see bridging at 0.35 mm pad-to-pad gap in X), and non-solder-
mask-defined pads. The X gap between adjacent columns is 0.80 - 0.45 = 0.35 mm, which is below some fabs'
default mask sliver minimum - expect the mask between pads 1/2 and 3/4 to be merged into one opening on a
cheap process. That is normal for 0603x2 arrays but check your stencil supplier.
5. CTS prints no pin numbers and no pin-1 marker in this datasheet, and the marking (3-digit value, white,
page 6) is symmetric. The numbering above comes from the standard counter-clockwise convention corroborated by
the already-CTS-verified EAGLE 742C083 cell and its device connects. Since both elements are identical and
isolated, a 180-degree placement error is electrically harmless - but pad 1 must still be opposite pad 4 for
the schematic pairing to hold, which it is.
6. No 742C043 package existed anywhere on disk (0 hits in zulu_a7.brd and zulu_a7.sch); this land is newly
constructed from the CTS table plus the 742C083 numbering rule, so it has not been validated against an
existing board.

### What the verifier challenged

1. NON-GEOMETRIC (prose only, no pad number affected): warnings item 3 states "The pads overhang the body ends in
   Y by 0.45 mm (pad outer edge 1.30 vs body half-width 0.80)". 1.30 - 0.80 = 0.50, not 0.45. The pad list itself
   is unaffected; the correct Y overhang past the 1.60 mm body is 0.50 mm per side.

2. PIN NUMBERING IS NOT DATASHEET-PROVEN (disclosed by the extractor, and I independently confirmed the absence).
   I grepped the full text layer of all 11 pages for 'pin', 'pad 1', 'terminal 1', 'numbering', 'orientation',
   'polari', 'marker' - ZERO hits. I also rendered and read pages 4, 5 and 6 at 300-900 dpi: the page-4 circuit
   cell, both page-5 package drawings (Convex Type X and Concave Type C) and the page-6 Recommended Pad Layout
   figure carry no pin number and no pin-1 marker anywhere. CTS DOC# 008-0335-0 Rev. T cannot prove the 1/2/3/4
   assignment. The claim's counter-clockwise map rests on project convention, not on the source. It is well
   corroborated (see notes) and safe for the intended use, but a downstream consumer must not treat it as
   datasheet-derived.

3. MINOR OVERSTATEMENT in the derivation prose: it says the result "reproduces the number already verified
   against CTS for the bigger sibling: 'CTS land 0.45 x 0.9 pads at +-0.85'". The 742C083 cell actually on disk
   in zulu_a7.brd is 0.50 x 0.9 at y = +/-0.90, NOT 0.45 x 0.9 at +/-0.85. The warnings section states the EAGLE
   values correctly, so the two sections contradict each other; the derivation sentence claims corroboration that
   the on-disk file does not provide. The chosen numbers are still right because they come from the CTS table
   directly, not from the sibling.

## 742C163

**R4 - CTS 742C163, eight isolated elements** &middot; 16 pads &middot; body 6.400 x 1.600 mm &middot; verdict CONFIRMED

Source: a.pdf p6, Mechanical Specifications - "Recommended Pad Layout", table row for package code 742. manufacturer recommended land.

### Pin 1 and numbering

Pad 1 is the LEFT end of the BOTTOM row viewed from the top (component side): x = -2.80, y = -0.85. Numbering
runs left to right along the bottom row (pads 1-8, y = -0.85), then right to left back along the top row (pads
9-16, y = +0.85), i.e. counterclockwise DIP-style, so pad 16 sits directly opposite pad 1 and each resistor
element spans pad k to pad 17-k: (1,16)(2,15)(3,14)(4,13)(5,12)(6,11)(7,10)(8,9). CONFIRMED against three on-
disk sources, not assumed: the EAGLE library's <device name="742" package="742C163"> connects block in
zulu_a7.sch.bak (gate A = pads 1/16 ... gate H = pads 8/9), the same file's <package name="742C163"> pad
coordinates, and the exported netlist zulu_a7.NET, where every R4 element spans a k / 17-k pair (PROG#=R4-1 vs
RST#=R4-16, DONE=R4-2 vs FPGA-DONE=R4-15, ... , VCC3V3=R4-8) and the DONE pull-up's series node DONE-PU =
{R4-9, R4-10} lands on two adjacent top-row pads. IMPORTANT: CTS itself defines no pin-1 end - the 742C163
body and land are fully symmetric about both axes and the datasheet numbers no terminals. Pad 1 is therefore a
library convention, so the footprint MUST carry a pin-1 dot or a keyed silkscreen/assembly marker at the
x=-2.80, y=-0.85 corner or the part can be assembled 180 degrees rotated with no electrical complaint from the
land itself. The value marking printed on the part (3-digit code, white, per page 6) is the only physical
orientation clue and it is not a pin-1 key.

### Cautions carried forward

1. PIN 1 IS A CONVENTION, NOT A DATASHEET FACT. CTS numbers no terminals and the part is symmetric about both
axes. The numbering above is confirmed against the project's own EAGLE library and netlist (see pin1_note),
which is exactly what R4's connectivity requires - but it is not traceable to CTS. Put a pin-1 marker on
silkscreen and assembly, and make sure the assembly house gets it; a 180-degree rotation is electrically
undetectable from the land.
2. THIS LAND DIFFERS SLIGHTLY FROM THE EAGLE CELL ALREADY ON THE BOARD. The EAGLE library's 742C163 (and
742C083) use 0.50 x 0.90 pads at y = +-0.90 (2.70 mm overall across). The CTS recommendation is 0.45 x 0.90 at
y = +-0.85 (2.60 mm across). Columns are identical in both (+-0.40, +-1.20, +-2.00, +-2.80 on 0.80 pitch);
only pad width (-0.05) and row offset (-0.05) change. I used CTS per the "prefer the manufacturer's
recommended land" rule. If bit-identical agreement with the existing EAGLE board matters more than the
datasheet, use 0.50 x 0.90 at +-0.90 instead - both are safe, the EAGLE one is marginally more generous
outward and leaves a 0.30 mm gap along the row instead of 0.35 mm.
3. A KNOWN ERROR IN THE PROJECT'S OWN NOTES. docs\\zulu_a7-bom.csv (R4 line) and
Zulu_Altrium\\docs\\pcbway_bom_substitutes.csv describe the CTS land as "0.45 x 0.80 mm pads, 0.80 mm pitch,
2.60 mm across". That misreads datasheet dimension B (0.80 = the inner GAP between the rows) as the pad
height. The pad is 0.45 x 0.90. Zulu_Altrium\\docs\\component_validation.md and tools\\bom_audit.py have it
right ("0.45 x 0.9 pads at +-0.85"). Worth fixing the two CSV notes so the wrong number does not get re-
derived later; note the "2.60 mm across" in them is correct either way, so the error is self-concealing.
4. CTS PUBLISHES ONE LAND FOR THE WHOLE 742 FAMILY. The Recommended Pad Layout table is keyed on package code
"742", not on 742C163 specifically, so the same A/B/C/D covers 742C043, 742X083, 742C083 and 742C163. That is
why this footprint and R34's 742C083 and R1's 742C043 all share one pad cell - a genuine convenience, but it
also means CTS gives no 16-pad-specific land and the 8-column grid above is derived from L = 6.40 and P =
0.80, not drawn by CTS.
5. NO COURTYARD OR SILK IS SPECIFIED BY CTS. Body is 6.40 x 1.60 with +-0.20 on both. Suggest a courtyard of
about 6.80 x 3.00 (land is 6.05 wide x 2.60 tall; IPC nominal-density adds ~0.25 clearance) and silkscreen
kept clear of the pads - a 1.60-tall body outline would sit between the two rows, which is only 0.80 mm apart,
so put the outline on assembly and use short silk ticks outside the end pads plus the pin-1 dot.
6. NO SOLDER-PASTE REDUCTION IS GIVEN. For a concave-termination array on 0.80 pitch, consider 1:1 paste or a
small reduction in pad width; 0.35 mm between adjacent pads is the bridging risk, not the 0.80 mm between
rows.
7. SUPPLY, from the project's own prior research (not the datasheet): CTS files the entire 74x series under
Legacy Products, and there is no drop-in second source on this exact land - the cited alternate, Panasonic
EXB-2HV101JV, is 0.50 mm pitch convex in a 3.80 x 1.60 body and needs its own footprint. Not a geometry
problem, but this land is a single point of failure for R4.
8. Page numbers in `source` are 1-based as printed ("Page 6 of 11"), matching PDF index 5.

### What the verifier challenged

1. NOT A GEOMETRY DEFECT, but the claim's own 'sharpest geometric check' (STEP 4) is unsound and should not be
   relied on. It argues that DONE-PU = {R4-9, R4-10} landing on two adjacent pads proves the counterclockwise
   numbering, because 'under any other numbering scheme that series link would be a reach across the part.' That
   is false. Under the rival scheme (top row numbered left-to-right, so pad 9 at x=-2.80 and pad 10 at x=-2.00)
   pads 9 and 10 are STILL adjacent, one 0.80 mm hop apart. The DONE-PU adjacency is invariant under the very
   substitution it is supposed to rule out, so it discriminates nothing. The numbering is nevertheless correct -
   see notes - but it is established by the CTS page-4 circuit panel, which the claim quoted yet never used for
   this purpose.

2. WARNING 1 OVERSTATES THE HAZARD. It says the footprint 'MUST carry a pin-1 dot ... or the part can be
   assembled 180 degrees rotated with no electrical complaint from the land itself,' implying a mis-assembly
   risk. There is none. Every element spans one column top-to-bottom and all eight are equal (page 4: R1 = ... =
   R8), so a 180 degree rotation maps the element set onto itself - the {1,16} column element lands on the {8,9}
   column and vice versa - and land-level connectivity is byte-for-byte identical. A 180 degree rotation is not
   merely undetectable, it is harmless. Corroborating this, CTS DOES print an orientation dot on the bussed
   745X101/745X102 parts on page 4 and deliberately prints none on 742C163. A pin-1 marker is fine as assembly
   documentation but is not a correctness requirement for this part.

3. WARNING 3 MISCITES ONE OF ITS TWO FILES. The '0.45 x 0.80 mm pads' error (misreading dimension B, the inter-
   row gap, as the pad height) exists in exactly one place:
   C:\\Users\\tambe\\Documents\\Electronics\\Zulu_A7\\docs\\zulu_a7-bom.csv line 6.
   C:\\Users\\tambe\\Documents\\Electronics\\Zulu_A7\\Zulu_Altrium\\docs\\pcbway_bom_substitutes.csv line 63 does
   not state pad dimensions at all and carries no such error. The substance of the warning is right (the pad is
   0.45 x 0.90, and component_validation.md lines 170/176 have it right); only the file list is wrong.

## DM3D-SF

**X3 - Hirose DM3D-SF microSD socket** &middot; 14 pads &middot; body 11.950 x 11.450 mm &middot; verdict CONFIRMED

Source: DM3AT-SF-PEJM5.pdf p9, "■Recommended PCB mounting pattern". manufacturer recommended land.

### Pin 1 and numbering

Pad 1 (DAT2) is the RIGHT-HAND end of the eight-pad contact row, viewed from the top (component side) with the
card-slot opening facing -y (toward the bottom of the drawing, the same orientation as the datasheet's
figure). Pad 1 sits at x = +3.20 mm, i.e. 3.20 mm right of the card-slot centre line, and is the contact
nearest the switch-A / G3 side; pad 8 (DAT1) is the left-hand end at x = -4.50 mm, 4.50 mm left of the centre
line. This follows the datasheet's own "(4.5)" dimension, which is measured to the #8 lead in the outline view
and to the leftmost pad in the land view, proving the land figure is un-mirrored top view. Functions in pad
order: 1 DAT2, 2 CD/DAT3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 DAT0, 8 DAT1. In Altium, place the designator/pin-1
marker at the lower-right of the contact row, and note that the card is inserted in the -y direction (the
socket opening is on the -y edge).

### Cautions carried forward

WHICH PATTERN THIS IS. The file named DM3AT-SF-PEJM5.pdf is NOT a single part drawing — it is the 12-page
HIROSE DM3 Series microSD card connector catalogue (Jul.1.2022 printing, contents current as of 01/2017),
covering DM3AT, DM3BT, DM3CS and DM3D. DM3D-SF's OWN recommended PCB mounting pattern IS present in the file,
on page 9, together with its own outline drawing and its part/HRS number ("DM3D-SF" / "609-0025-8"). The prior
note "DM3 catalog p9" is correct. I used page 9 (DM3D). I did NOT use the DM3AT-SF-PEJM5 pattern on page 3 —
that is a physically different, much larger footprint (14.5 mm wide, "P=1.1", "0.7" pads, different
ground/switch pad layout) and would be wrong for the fitted part.
PRIOR NOTE IS PARTLY WRONG. "8 x 0.55 pads on 1.1 pitch" is not right. The contact pads are 0.70 mm wide x
1.75 mm long on 1.1 mm pitch. The "0.55" in the figure is a different dimension entirely: it is the distance
from the RIGHT edge of the front-left ground pad to the CENTRELINE of the #8 contact pad. The rest of the note
("4 cover pads, 2 switch pads, 2 keep-outs") is confirmed exactly.
Y ORIGIN CONFIDENCE. The recommended-pattern figure contains no body outline, so the body could not be located
directly. I solved for it by equal pad overhang and then verified the method in X, where it reproduced the
datasheet's own shell dimensions (-5.95 / +6.00 from the card centreline) to 0.001 mm, and in Y, where the
derived rear face lands on the "10.2MIN" no-copper limit to 0.001 mm. I rate the Y datum good to roughly
+/-0.1 mm; the pad-to-pad geometry is exact regardless. If you prefer a different datum, add +4.475 mm to
every y to put the origin on the top edge of the contact row, or +5.350 mm to put it on the contact-row pad
centres.
X ORIGIN IS THE CARD-SLOT CENTRE LINE. The 11.0 mm plastic housing is exactly centred on it, but the 11.95 mm
metal shell is 5.95 mm left and 6.00 mm right, so the shell's own centre is +0.025 mm from x=0. The body box I
report (11.95 x 11.45) therefore runs x -5.95..+6.00, y -5.725..+5.725. 25 um is below any fab tolerance;
shift everything by -0.025 mm in x if you want the shell exactly centred.
KEEP-OUTS — MUST BE ADDED, they are not pads. The figure hatches two "No conductive traces" zones (note 3). In
the final frame: (a) 8.500 x 2.000 mm centred at x = -0.650, y = +0.525 (spans x -4.900..+3.600, y
-0.475..+1.525); (b) 2.500 x 2.000 mm centred at x = -0.700, y = +4.725 (spans x -1.950..+0.550, y
+3.725..+5.725). Place these as copper keep-out / route-keepout regions on all layers under the connector.
OTHER FIGURE NOTES. The remaining MIN/MAX callouts ("8.1MIN", "5.05MIN", "2.55MAX", "0.4MIN", "10.2MIN",
"8.2MAX", "6MIN", "4MAX") are all limits on those same two keep-out zones, not pad dimensions. The DM3D is a
push-pull manual connector with no ejection mechanism, so there is no ejector keep-out beyond the slot; the
card protrudes to "(15.8):CARD FULLY INSERTED" from the rear face, i.e. about 10.1 mm beyond the body's front
edge (y = -15.825 at the card's far end), so leave the -y side clear for card insertion and finger access. The
card-detect switch is NORMALLY OPEN: A-B open with no card, closed with the card inserted, so pull pad A or B
up and ground the other.
PAD NAME MAPPING (datasheet label -> requested name): #1(DAT2)->1, #2(CD/DAT3)->2, #3(CMD)->3, #4(VDD)->4,
#5(CLK)->5, #6(VSS)->6, #7(DAT0)->7, #8(DAT1)->8; "Card Detection Switch (A)" -> A (rear-right pad); "Card
Detection Switch (B)" -> B (left flank, upper pad). The datasheet does not letter the four metal-cover ground
pads, so I assigned them: G1 = front-left corner pad (next to pad 8), G2 = left flank lower pad, G3 = right
flank lower pad, G4 = front-right corner pad (next to pad 1). Tie all four G pads to GND/shield.

### What the verifier challenged

1. DERIVATION IS FACTUALLY WRONG ON A KEY POINT (no geometric consequence). The claim states 'The land figure
   carries no body outline, so the body could not be located directly' and 'ORIGIN ... I solved for it by equal
   pad overhang'. False: the p9 recommended-pattern figure DOES draw the body, as a dash-dot (phantom) rectangle
   at PDF x 138.610..237.923, y 424.552..519.708 = 11.9504 x 11.4502 mm. The extractor's rectangle finder missed
   it because its top edge is split into three collinear segments by the keep-out zone and it is dashed. Measured
   body centre = ROW + 4.47461 mm vs the claim's derived ROW + 4.475 (error 0.0004 mm) and CL + 0.0254 mm in x.
   So the answer survives, but the self-assessed 'Y ORIGIN CONFIDENCE ... good to roughly +/-0.1 mm' and 'Medium-
   high on the absolute origin in Y' are unwarranted — the Y datum is exact and directly measurable, not a
   derivation.

2. CONFIDENCE STATEMENT IS OVERSTATED. The claim asserts 'every one of them lands on an exact 0.05 mm value that
   is independently confirmed by a labelled dimension in the figure ... 14/14 pads cross-check'. Two pad
   dimensions have NO printed callout anywhere on page 9: (a) the contact-pad WIDTH 0.70 mm (measured 0.6998;
   '0.7' is printed only on the sibling DM3AT p3 and DM3BT p5 land figures, not on p9), and (b) pad B's WIDTH
   1.45 mm (measured 1.4496). Both values are correct and exact in the vector art, but they are measured, not
   read off a dimension. Page 9's complete dimension text contains no '0.7' and no '1.45'.

3. BODY BOX CARRIES A 0.025 mm X ERROR AS RETURNED. body {dx:11.95, dy:11.45} read as centred on the origin puts
   the shell at -5.975..+5.975 about x=0, whereas the real shell is -5.9496..+6.0005 about CL (confirmed
   identically in both the outline plan view and the land figure's phantom outline: the shell centre is +0.0254
   mm from the card-slot centreline). The claim's own warnings text states this correctly, but the structured
   body field cannot express the offset. 25 um, below any fab tolerance; affects only courtyard/silk, no pad.

4. SWITCH-TRACE PROSE IS GARBLED (conclusion still correct). The derivation places switch (B) '9.35..9.85 mm
   forward of the body's front edge' and (A) '10.30..11.45 mm forward of the front edge'. Those are distances
   REARWARD of the front edge, not forward — forward of the front edge is the open card-slot side. My own leader
   trace: the (B) arrowhead sits at the left shell face, +4.125 mm rear of body centre (= 9.575 mm rear of the
   front edge); the (A) arrowhead at +5.850 mm right, +5.725 mm rear of centre (= the rear face). The mapping B =
   left upper pad, A = right upper pad is nonetheless correct.

5. SOURCE-FILE / PART-NUMBER CAUTION (not an extraction defect, flag for the BOM). The cited file is named DM3AT-
   SF-PEJM5.pdf but the extracted pattern is DM3D-SF from page 9. That is the right page for the stated
   footprint, and the extractor flagged it, but nobody has yet confirmed the board actually fits DM3D-SF rather
   than the DM3AT-SF-PEJM5 the filename names. The two land patterns are NOT interchangeable (DM3AT p3 is 14.5 mm
   wide with a different ground/switch pad layout). Resolve against the BOM before release.

## FT2232HL-LQFP64

**U2 - FTDI FT2232HL USB bridge** &middot; 64 pads &middot; body 10.000 x 10.000 mm &middot; verdict CONFIRMED

Source: DS_FT2232H.pdf p58, Figure 8.2 "64 pin LQFP Package Details". DERIVED, no manufacturer land exists.

### Pin 1 and numbering

Pin 1 is at (-5.70, +3.75) - the TOP-MOST pad of the LEFT row, viewed FROM THE TOP (component side). This is
taken directly from the "Top View" marking diagram at the top of Figure 8.2, which labels the four
corners/rows as: 64 at the top-left corner and 49 at the top-right corner (top row, so 49..64 runs right-to-
left); 1 at the upper end of the left edge and 16 at the lower end of the left edge (left row runs downward);
17 at the bottom-left and 32 at the bottom-right (bottom row runs left-to-right); 33 at the lower-right and 48
at the upper-right (right row runs upward). The package-outline view lower-left in the same figure repeats
these labels and additionally shows a circular pin-1 index dot inside the body near the upper-left corner. So
numbering is COUNTER-CLOCKWISE viewed from the top, exactly the convention stated in the task - it is
confirmed, not assumed. Pin 1 = GND per the Figure 3.1 schematic symbol (pin 2 = OSCI, pin 3 = OSCO), so a
good build check after placement is that the pad nearest the upper-left body corner on the left row lands on
GND and the two below it on the 12 MHz crystal. Recommend marking the pin-1 corner on the top overlay with a
dot outside the pad field near (-6.9, +4.9) plus a chamfered silkscreen corner, since a 180 deg rotation error
here is silent.

### Cautions carried forward

1. NO MANUFACTURER LAND PATTERN EXISTS - THIS LAND IS DERIVED. I searched all 69 pages for "land", "PCB
layout", "solder pad", "stencil" and "recommend". FTDI's section 8 gives only package OUTLINE drawings (8.1
QFN-64 p.57, 8.2 LQFP-64 p.58, 8.3 VQFN-56 p.59) plus a reflow profile. There is no "Recommended Land Pattern"
/ "Recommended PCB Layout" / "Solder Pad Layout" figure for the FT2232HL anywhere in DS_FT2232H.pdf. The pads
below are therefore an IPC-7351B Density Level B (Nominal/Median) gull-wing QFP land derived by me from the
Figure 8.2 lead dimensions, NOT an FTDI-published footprint. IPC name: QFP50P1200X1200X160-64N.
2. Derived-from values, restated for audit: lead width b = 0.17/0.22/0.27; lead foot length L =
0.45/0.60/0.75; lead span D = E = 11.75/12.00/12.25; pitch e = 0.50 BSC; body D1 = E1 = 9.90/10.00/10.10;
height A max 1.60. Resulting pad 0.28 x 1.55 mm, row centre 5.70 mm from the body centre (11.40 mm between
opposite row centres), outer land span Zmax 12.95, inner land gap Gmin 9.85.
3. PAD WIDTH IS 0.28, NOT THE STRICT IPC NUMBER 0.245. The strict IPC-7351B Level B side-fillet equation (JS =
-0.02 for pitch <= 0.625 mm) gives Xmax = 0.245 mm, which is narrower than the maximum lead width b = 0.27. I
rounded UP to 0.28 mm, the industry-standard width for 0.5 mm pitch QFP (also Altium's own LQFP64 default),
for solderability and AOI fillet-inspection margin. Cost: land-to-land clearance drops from 0.255 to 0.220 mm.
That is comfortable for the PCBWay HDI process this board uses, but if you want a strictly-IPC land or extra
paste-bridging margin on a hand-soldered build, change dx (left/right rows) / dy (top/bottom rows) to 0.25 and
leave every x,y unchanged - the row centre and pad length do not move.
4. Paste layer: do NOT use a 1:1 paste aperture on 0.5 mm pitch. Reduce the paste aperture to roughly 0.25 x
1.30 mm (about 90% of the width, 85% of the length, home-on-pad), or the assembler's house rule, to control
bridging.
5. Pad 1 is a distinct SHAPE in many houses (rounded-rect or a chamfered corner) but I have specified all 64
as plain "rect" of identical size, as required. Mark pin 1 on the overlay instead - see pin1_note. A 90 or 180
degree rotation error is silent and mis-wires the whole part, so verify pin 1 = GND, pin 2 = OSCI, pin 3 =
OSCO against the crystal net before release.
6. NO EXPOSED / THERMAL PAD. The LQFP-64 has none - the exposed-centre-pad note in section 8 belongs to Figure
8.3 (the 56-pin VQFN). Do not add a centre pad. The FT2232HQ QFN-64 (Figure 8.1) is a different package and a
different footprint; this one is for the -HL suffix only, which is what U2 is.
7. Body outline 10.00 x 10.00 mm is the NOMINAL D1/E1 and excludes mould protrusion (datasheet note 2 allows
0.25 mm per side). For a courtyard, use about 13.0 x 13.0 mm (Zmax 12.95 plus an IPC Level B 0.25 mm excess on
each side) rather than the 10 mm body.
8. The dimensions were read from a rendered raster image, not from a text layer - get_text() on that page
returns only the heading and caption. I re-rendered and zoomed the VARIATIONS table to confirm every digit,
but there is no machine-readable text to cross-check against, so a second pair of eyes on the table crop is
cheap insurance: C:\\Users\\tambe\\AppData\\Local\\Temp\\claude\\C--Users-tambe-Documents-Electronics-
Zulu-A7-Zulu-Altrium\\1e3d9c42-62fe-43bd-a170-baf7d18a0d60\\scratchpad\\table_zoom.png and the full figure at
...\\scratchpad\\lqfp64_raw.png

## JST-B2B-PH-SM4-TB

**X4 - JST PH 2-circuit top-entry SMT header, the LiPo connector** &middot; 4 pads &middot; body 7.950 x 5.000 mm &middot; verdict CONFIRMED

Source: JST_B2B_PH_SM4_TB_LF_SN_ePH.pdf p1, <SMT type> - SM4 type / Top entry type, under "PC board layout and Assembly layout". manufacturer recommended land.

### Pin 1 and numbering

Pad 1 (BAT+) is at x = -1.0, y = -2.25; pad 2 (GND) at x = +1.0. In JST's land figure "Circuit No.1" labels
the leftmost contact pad, with the dash-dot datum "End face of wafer on the mating side" running along the
top. That figure is explicitly "viewed from the connector mounting side" (top view), so it transfers with no
mirroring: with the wafer's mating-side end face toward +y, circuit 1 is at -x. This is independently
confirmed by the page-3 front elevation, which is taken looking at that same datum face and shows Circuit No.1
at the RIGHT - the correct left-right reversal for a view from +y of a part whose pin 1 is at -x. Mark pin 1
on silkscreen at the -x end, outside the MP1 pad (e.g. a dot near x = -4.6, y = +1.6).

### Cautions carried forward

1. TOP-ENTRY, so the connector OPENING FACES STRAIGHT UP out of the board (+z) - there is no in-plane opening
direction. What +y means here is the wafer's "End face of wafer on the mating side" (the datum face, the one
carrying the shroud lock ramp located "1.9" from it): that face is at y = +2.5. The contact leads exit the
OPPOSITE face and run out to -y; their lands reach y = -5.0, i.e. 2.5 mm past the body edge at y = -2.5. Leave
that -y strip clear of other parts. Mated height is 6.6 mm for the header alone, "(8.6)" with the PHR
receptacle fitted, and the wire leaves vertically - keep vertical clearance above the part.
2. "2 max.", "7.5 min." and "1 min." are LIMITS, not nominals. The land I give (1.0 x 5.5 contacts) is the
MINIMUM recommended copper; it may be grown outward in -y but must not be shrunk, and the contact land must
start no further than 2.0 mm from the datum.
3. The source figure is generic (drawn with 3 contacts and break lines). I instantiated it for 2 circuits
using A = 2.0 and B = 7.95 from the page-3 table.
4. MP1/MP2 overhang the 7.95 mm body ends by 0.225 mm each. Total copper envelope is 8.40 x 7.50 mm; courtyard
should be at least 9.4 x 8.5 mm to allow for the wider PHR-2 receptacle shell dropping over the header.
5. UNRESOLVED CROSS-CHECK (does not change the pads): the page-3 front elevation draws a ~1.03 mm wide stepped
feature at each end, centred 2.11 mm in from the body end (0.86 mm outboard of circuit 1). The recommended
fixing land sits at 2.40 mm outboard of circuit 1, spanning 0.225 mm outside to 1.375 mm inside the body end -
adjacent to that feature but not overlapping it. Either the elevation feature is a moulded pocket rather than
the tab itself, or the tab foot is offset from the tab body. The land figure is the manufacturer's recommended
layout and the task rule is to prefer it, so I used it unchanged; the fixing tabs are non-electrical anyway,
so a small positional error there would cost mechanical hold, not connectivity.
6. MP1/MP2 are mechanical only. Tie them to GND (or leave them as a separate MP net) - do NOT assume they are
internally bonded to either contact. Keep them off any net you rely on for the battery return.
7. The parts are tin-plated brass/copper alloy on a PA (ivory) wafer; standard SnAgCu reflow land, no special
paste reduction called for. Paste = copper 1:1 on all four pads.
8. X4 is the LiPo connector, so pad 1 (BAT+) will carry battery current; the part is rated "2 A AC/DC (AWG
#24)" per circuit, which is the ceiling for that net through this connector.

## PTS810

**BTN - C&K/Littelfuse PTS810SJM250SMTR LFS tact switch** &middot; 4 pads &middot; body 4.200 x 3.200 mm &middot; verdict CONFIRMED

Source: Littelfuse-CK-Tactile-PTS810-Series-Datasheet.pdf p1, "Recommended PCB Layout". manufacturer recommended land.

### Pin 1 and numbering

Pad 1 is the UPPER-LEFT pad, at x = -2.075, y = +1.075 (top view, component side). Both the "Recommended PCB
Layout" and the package top view in "Dimensions (mm)" print the digits 1/2/3/4 in the same 2x2 arrangement: 1
upper-left, 2 upper-right, 3 lower-left, 4 lower-right. Pins 1 and 3 are the two leads on the left flank of
the body, pins 2 and 4 the two on the right flank.
PAIRING - it is NOT a diagonal pairing. The "Schematic" figure on page 1 draws a horizontal wire joining pin 1
to pin 2 (the TOP row) and a second horizontal wire joining pin 3 to pin 4 (the BOTTOM row), with the single
normally-open contact bridging between the two wires. So terminal A = pads 1 + 2 (both at y = +1.075),
terminal B = pads 3 + 4 (both at y = -1.075). Wire 1&2 to one net and 3&4 to the other; a diagonal connection
(1-4 / 2-3) would be wrong for this part. Consistent with "1 make contact = SPST NO".

### Cautions carried forward

1. The prior note on file is CORRECT and is confirmed, not merely assumed: 1.05 x 0.65 mm pads at +/-2.075,
+/-1.075, 5.2 x 2.8 envelope, body 4.2 x 3.2. No change was needed.
2. PAIRING IS ROW-WISE, NOT DIAGONAL. 1&2 are one terminal, 3&4 the other, as drawn in the datasheet's
Schematic. Many tactile switches use the diagonal convention, so if the schematic symbol for BTN in the
project ties 1-4 and 2-3, the net assignment will be wrong even though the land pattern is right. Worth
checking the symbol pin-to-net mapping.
3. The datasheet gives no courtyard, no silkscreen and no solder-mask/paste guidance. Suggested courtyard: at
least 5.2 x 3.2 mm (the pad envelope in X, the body in Y) plus your normal clearance; the body corners at
+/-2.1, +/-1.6 fall inside the pad X envelope, so the pads set the X extent and the body sets the Y extent.
Keep silkscreen outside the pads - the pads sit only 0.4 mm outside the body edge in Y and 0.4 mm outside it
in X, so a body outline drawn on silk will collide with the pads unless it is broken at the four leads.
4. This is a top-actuated switch, 2.5 +0.2/-0.1 mm tall with a ~3 mm actuator on the top face; the 3D body /
assembly height is 2.5 mm from the PCB, not the 1.6 mm standoff. Leave keep-out above.
5. The recommended land gives only about 0.05 mm of pad beyond the lead on each side in Y and 0.30 mm of toe
in X. It is a tight, minimum-area land by IPC standards. It is the manufacturer's own recommendation so I used
it verbatim, but if your assembler wants more heel fillet on a J-lead you may want to grow the pads inboard
(increase dx toward the centre) rather than outboard, which would reduce the 3.1 mm gap.
6. Pad shape is given as plain rectangles (the figure shows square-cornered hatched rectangles). Rounded-
rectangle pads with a small corner radius are fine if your house style uses them.
7. Only one placement of the layout artwork was read; note that the same image object (xref 118) is also
placed a second time at PDF y 647-706 on page 1, outside the visible figure area. That duplicate was ignored;
it is identical artwork.

## SOT23-5

**U5, U6, U7 - Semtech SC189 bucks** &middot; 5 pads &middot; body 2.950 x 1.600 mm &middot; verdict CONFIRMED

Source: SC189-datasheet 08 27 10.pdf p23, "Land Pattern -  SOT23-5". manufacturer recommended land.

### Pin 1 and numbering

Pin 1 is the LEFT pad of the 3-pad row, at (-0.95, -1.25), viewed FROM THE TOP. Confirmed two independent ways
in this datasheet:
(1) "Pin Configuration" on printed page 2, explicitly labelled TOP VIEW for SOT23-5. Rendered at 900 dpi, it
draws the part rotated 90 deg (pins on the left and right vertical sides): left side top-to-bottom = 1 VIN, 2
GND, 3 EN; right side = 5 LX (top, in line with pin 1) and 4 VOUT (bottom, in line with pin 3). Rotating that
drawing 90 deg counter-clockwise so the 3-pin side becomes the bottom edge gives 1 bottom-left, 2 bottom-
centre, 3 bottom-right, 4 top-right, 5 top-left.
(2) "Outline Drawing - SOT23-5" plan view on page 23, rendered at 1200 dpi: the bottom edge carries three
leads labelled "1" and "2" from the left, and the top edge carries two leads with "N" (N = 5, per the table
row "N  5") at the TOP-LEFT. Same result.
So the numbering runs counter-clockwise when viewed from the top: 1, 2, 3 along one long side (1 at the left
end), 4 at the far end of the opposite side, 5 back at the near end. The 2-pad row's middle position is empty.
CORRECTION TO THE TASK BRIEF: the brief says "pin 4 diagonally opposite pin 3". That is not what this
datasheet shows. Pin 4 (VOUT) sits DIRECTLY OPPOSITE pin 3 (EN) - same end of the package, both at x = +0.95.
It is pin 4 that is DIAGONALLY opposite pin 1, and pin 5 (LX) that is directly opposite pin 1 (VIN). The rest
of the brief's description (1,2,3 on one side with 1 at one end; 4,5 on the other) is correct, as is the pin
function list 1 VIN / 2 GND / 3 EN / 4 VOUT / 5 LX.

### Cautions carried forward

1. PRIOR NOTE VERIFIED. The on-file hint ("datasheet p23 land: 0.95 pitch, pads 0.60 x 1.10, inner gap 1.40,
outer span 3.60") is correct and complete as far as it goes. I additionally recovered C = (2.50), the row
centreline spacing, which is what actually places the pads in y; 1.40 + 2(1.10) = 3.60 and (1.40+1.10)/2 =
1.25 both agree with it, so the numbers are mutually consistent and not a transcription error.
2. THE BRIEF'S PIN-4 STATEMENT IS WRONG. Pin 4 is directly opposite pin 3, not diagonally opposite it. See
pin1_note. If any downstream code or schematic symbol was built on the "pin 4 diagonally opposite pin 3"
assumption, pins 4 and 5 would be swapped - and on the SC189 that swaps VOUT with the switching node LX, which
would be a hard failure (inductor and output cap on the wrong nodes). Worth re-checking the U5/U6/U7 symbol-
to-footprint pin mapping.
3. Semtech flags the land pattern as reference-only: "THIS LAND PATTERN IS FOR REFERENCE PURPOSES ONLY." It is
a fairly tight pattern - pad length 1.10 with an inner gap of 1.40 gives roughly 0.30 mm of toe extension
beyond the 2.80 BSC lead-tip span and about 0.40 mm of heel land inside it. It is close to IPC-7351 nominal
(density level B) for SOT23-5, so it is fine for PCBWay-class assembly, but if you want extra toe fillet for
inspection you could stretch Y to 1.20 and hold G at 1.40 (Z then becomes 3.80) without touching pitch or pad
width. I did NOT do that - the numbers above are exactly the datasheet's.
4. No solder-mask or paste dimensions are given in the figure; use your normal mask expansion. No
thermal/exposed pad exists on the SOT23-5 variant (that is only on the 2x2 MLPD-UT6 option on page 22 - do not
mix the two land patterns up, they are adjacent pages in the same PDF).
5. Body size is for silkscreen/courtyard only. D has no NOM in the table (2.80 min / 3.10 max); I used the
2.95 midpoint. E1 nominal 1.60 is taken straight from the table. Both exclude mold flash per outline note 3,
so keep silkscreen clear of the pads rather than drawing the body outline tight.

## VQFN16-3X3-RGT

**U8 - TI bq24232 charger and power path** &middot; 17 pads &middot; body 3.000 x 3.000 mm &middot; verdict CORRECTED

Source: bq24232.pdf p44, LAND PATTERN EXAMPLE / EXAMPLE BOARD LAYOUT, RGT0016C, VQFN - 1 mm max height, drawing 4222419/E 07/2025. manufacturer recommended land.

### Pin 1 and numbering

Pin 1 is the TOPMOST pad of the LEFT column, at (-1.40, +0.75) mm in top view (component side). Confirmed from
the datasheet's own pinout drawing on page 5, captioned "16-Pin RGT Package with Thermal Pad (Top View)",
where the left column reads 1,2,3,4 top to bottom (TS, BAT, BAT, CE), the bottom row 5,6,7,8 left to right,
the right column 12,11,10,9 top to bottom, and the top row 16,15,14,13 left to right - i.e. counter-clockwise
from the top. The same numbering is printed on the land pattern figure itself (1 and 4 flag the left column, 5
and 8 the bottom, 9 and 12 the right, 13 and 16 the top). The package outline shows the PIN 1 INDEX AREA
hatched in the TOP-LEFT quadrant of the body, with an optional PIN 1 ID dimple there; put the
silkscreen/assembly pin-1 marker outside the top-left corner, around (-1.9, +1.9).

### Cautions carried forward

1. The (2.8) dimension on the TI figure is CENTRE-TO-CENTRE of opposite pad rows, not outer-edge-to-outer-
edge. I verified this from the PDF vector geometry (pad centres measured at exactly 1.4000 mm from the drawing
centreline using the drawing's own 56.68 pt/mm scale). If it were read as an outer-edge span, every pad would
sit 0.3 mm too far inboard and would overlap the 1.68 mm thermal land. Do not "fix" 1.40 to 1.10.
2. Pad 17 is drawn as one 1.68 x 1.68 mm square copper land. That is the COPPER. The paste layer should NOT be
1.68 square: TI's stencil page specifies a (square 1.55) aperture giving 85% printed solder coverage by area
under the package, on a 0.125 mm stencil. In Altium, either set pad 17's paste expansion to -0.065 mm per side
(1.68 -> 1.55) or, better for void control, split the paste into a 2x2 or 3x3 aperture array hitting ~85%
area. Altium's default 0 paste expansion on a 1.68 pad will over-paste and float the part.
3. Solder mask: TI prefers NON SOLDER MASK DEFINED with 0.07 mm minimum mask opening all around the pad (0.07
MAX all around for the SMD alternative). Set solder mask expansion to 0.07 mm on pads 1-16 rather than leaving
the library/board default, or the 0.24 mm wide lands can end up mask-defined.
4. The four (dia 0.2) vias at (+/-0.58, +/-0.58) mm shown inside the thermal land are OPTIONAL (note 5) and
are NOT pads - I did not include them in the pad list. If you add thermal vias in the footprint, put them at
exactly those coordinates and tent/plug/fill them (note 5), otherwise paste will wick into them.
5. Clearance between the thermal land edge (0.84 mm from centre) and the signal pad inner edge (1.10 mm from
centre) is only 0.26 mm. Check this against your PCBWay HDI rule set - it is fine for typical 0.1 mm/0.1 mm
rules but leaves no room to grow the thermal land.
6. (R0.05) corner rounding on all pads is cosmetic; plain rectangles are correct for fabrication.
7. The mechanical drawing (4222419/E, 07/2025) is newer than the datasheet body text (SLUS821J, revised May
2017) - normal for TI, and the appendix is the authoritative land pattern.
8. Pin-name check for the schematic symbol (bq24232 column, page 5): 1 TS, 2 BAT, 3 BAT, 4 CE, 5 EN2, 6 EN1, 7
PGOOD, 8 VSS, 9 ILIM, 10 OUT, 11 OUT, 12 CHG, 13 IN, 14 TMR, 15 ITERM, 16 ISET. Note pin 8 is VSS and the
thermal pad (17) must also be tied to VSS - it is not a no-connect.

### What the verifier challenged

1. PIN NAME ERROR (high impact, warnings item 8): pins 9 and 12 are swapped. The claim states '9 ILIM, 10 OUT, 11
   OUT, 12 CHG'. The datasheet Pin Functions table (page 5) reads 'CHG 9 9 O Open-Drain Charging Status
   Indicator' and 'ILIM 12 12 I Adjustable Current Limit Programming Input'. Confirmed positionally in the page-5
   bq24232 top-view diagram: the name ILIM (x=438.3, y=303.3) aligns with the label '12' (x=419.6, y=302.7), and
   CHG (x=438.8, y=350.2) aligns with '9' (x=420.4, y=350.9). CORRECT pin map for bq24232: 1 TS, 2 BAT, 3 BAT, 4
   CE, 5 EN2, 6 EN1, 7 PGOOD, 8 VSS, 9 CHG, 10 OUT, 11 OUT, 12 ILIM, 13 IN, 14 TMR, 15 ITERM, 16 ISET. This does
   not change any pad coordinate but would mis-wire the schematic symbol: ILIM sets the input current limit
   resistor, CHG is an open-drain status LED output.

2. VIA COUNT ERROR (warnings item 4): the land figure shows FIVE optional 0.2 mm vias, not four. I clustered the
   blue stroke paths on page 44 and found five circles of diameter 11.339 pt (= 0.20003 mm at the figure's
   56.6929 pt/mm scale): four at (+/-32.8815, +/-32.8815) pt = (+/-0.580, +/-0.580) mm AND one centred at
   (299.1245, 281.417) pt, i.e. exactly at the origin (0, 0). The centre via is drawn in the same blue copper
   colour as the other four and is the same diameter. Anyone following warning 4 verbatim ('put them at exactly
   those coordinates') would omit the centre thermal via.

3. MINOR / arithmetic hygiene: the extractor used a drawing scale of 56.68 pt/mm. The figure is labelled
   SCALE:20X, so the exact scale is 72/25.4 x 20 = 56.69291 pt/mm. Re-measuring with the exact scale gives the
   thermal land as 95.245 pt = 1.68000 mm (not the quoted 1.6805) and the via diameter as 0.20003 mm. The quoted
   1.6805 is a rounding artifact of the approximate scale, not a real dimension; the correct value is exactly
   1.68, as printed.

