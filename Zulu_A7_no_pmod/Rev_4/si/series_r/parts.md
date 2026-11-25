# SDRAM DQ series resistors: which part to use

Zulu_a7_no_pmod Rev 2, U3 AS4C32M16SB-7TCN (Bottom) to U1 XC7A35T-2CPG236I, nets D0-D15.
Status: **planning only.** No board, schematic, library or BOM file has been changed.
Written 2026-11-13.

## Recommendation

| | Primary | Fallback (same footprint, already on the BOM) |
|---|---|---|
| MPN | **Yageo RC0201FR-0722RL** | **Yageo RC0201FR-0733RL** |
| Value / tol. / TCR | 22 ohm, +-1 %, +-200 ppm/C | 33 ohm, +-1 %, +-200 ppm/C |
| Power | 1/20 W (50 mW) at 70 C | 1/20 W |
| Body | 0201 (0603 metric), 0.60 x 0.30 x 0.23 mm | same |
| Land pattern | the board's own **R0201** footprint, unchanged | same |
| BOM | 1 new line (same family as 9 existing RC0201FR lines) | **0 new lines**: item 41 "R24,R25 RC0201FR-0733RL" becomes 18 pieces |
| Ball undershoot, reads, max corner (ideal R, `results_r22/33.json`) | -0.35 V, 17 % of the DS181 Table 4 budget | -0.31 V, 15 % |
| Read edge, 10-90 % at U1 (same files) | 0.62-0.97 ns | 0.78-1.32 ns |

The **R0201** footprint in `zulu_a7.PcbLib` and on the board is two 0.30 x 0.30 mm rectangular pads with centres
0.60 mm apart: a 0.30 mm gap and 0.90 x 0.30 mm overall. Read from the PcbLib `R0201/Data` stream with olefile;
the board copies (R2, R24) agree. 34 R0201 and 44 C0201 parts already use these lands (Components6 of the PcbDoc,
md5 2a616c1c), and the Fab B Rev 2 PCBWay release assembles 86 0201 parts with the same lands.

**Why 0201 discrete parts and not arrays:** the U3 DQ pins do not sit next to each other. VDDQ and VSSQ pins sit
between them: the south row is D0 pin 2, D1/D2 pins 4/5, D3/D4 pins 7/8, D5/D6 pins 10/11, D7 pin 13. So the DQ
x positions run 37.95 / 36.35, 35.55 / 33.95, 33.15 / 31.55, 30.75 / 29.15 mm, spaced 1.6 or 0.8 mm (fresh PcbDoc
extract, see "Board facts"). A 4-element array therefore never lines up with four DQ pins. Every array forces
jogs: at 0.4-0.5 mm pitch the traces have to fan in to it, and no trace fits between its pads. Discrete 0201s can
be placed one per net wherever each net has room, and they reuse a proven footprint and BOM family.

With the 0201's own parasitics simulated (see "Electrical" below), the worst ball reading at the max corner is
2.1 % of the budget at 22 ohm, 0 % at 33 ohm and 8.9 % at 15 ohm. D8 is the one net that is sensitive to the
part's L/C, so re-simulate it once the parts are placed.

**22 ohm versus 33 ohm is a real choice, not only a fallback.** 33 ohm is already a purchased line on this BOM
(R24/R25, the 12 MHz clock series resistors). It gives a slightly better ball undershoot (15 % against 17 %) but
slower read edges (up to 1.32 ns) and more delay. The read-timing study decides between them. The user proposed
22 ohm, which is the primary here. 15 ohm (RC0201FR-0715RL) leaves 30 % of the budget used. It is fine
electrically, but it is a new BOM line with no advantage over 22 ohm.

## What the project already uses (measured from files)

| Source | Resistor packages found |
|---|---|
| PcbDoc `Components6/Data` (olefile) | R0201 x34, R0402 x14, 742C043 x1 (R1), 742C083 x1 (R34), 742C163 x1 (R4). Capacitors: C0201 x44 (C155-C159 among them), C0402 x16, C0603 x19, C0805 x15 |
| PcbLib `zulu_a7.PcbLib` storages | C0201, C0402, C0603, C0805, IND2520, QFN28-UFD-4X5, **R0201**, R0402, SOT23-5, VSON10-DLA0010A. The 742C array patterns are on the board only, not in this library |
| `assembly/Zulu_A7_Fab_B_Rev_2_PCBWay_BOM.csv` | Yageo RC0201FR-07xxxL (1 %, 1/20 W) on 14 lines, **including RC0201FR-0733RL (R24, R25)**. RC0402FR lines. CTS 742C043472JP, 742C083472JP, 742C163101JP (0.8 mm-pitch concave arrays, +-5 %) |
| `docs/zulu_a7-bom.csv` | same RC0201FR family. Murata GRM033 0201 capacitors (C155-C159 = GRM033R61A104KE15D) |

These BOMs are the Fab B Rev 2 release and the master BOM. The no_pmod board lacks R26-R33 but otherwise uses
the same parts. The highest resistor designator in the schematics is R118 (`Text=R…` records in
zulu_a7_*.SchDoc), so R119-R134 appear to be free. Assumed, not checked against the PcbDoc's hidden or unplaced
records.

## Options compared

Datasheet numbers come from the manufacturer PDFs read in this session (Panasonic EXB array datasheet AOC0000C14,
1-Mar-20; Yageo YC/TC array datasheet V.9, 2019-02-21; Rohm MNR datasheet). Stock figures are distributor
snapshots found by web search on 2026-11-13. They vary by region, so check them before ordering.

| Option | Example MPN (22 ohm) | Elements | Body (mm) | Pitch (mm) | Power/element | Tol. | Fit here |
|---|---|---|---|---|---|---|---|
| **0201 discrete** | **Yageo RC0201FR-0722RL** | 1 | 0.60 x 0.30 | n/a | 50 mW | 1 % | **best**: existing footprint and BOM family. DigiKey lists about 0.56 M in stock in one regional snapshot |
| 01005 discrete | Panasonic ERJ-XGNJ220Y; Yageo RC0100JR-0722RL | 1 | 0.40 x 0.20 | n/a | 31 mW | 5 % | not justified: saves 0.3 mm per part but needs new lands, a thinner or stepped stencil and a new process at PCBWay. PCBWay's page says "as small as 01005" but nothing on this board uses it |
| 2 x 0201 | Panasonic EXB-14V220JX (convex; MPN built from Panasonic's part-number code, stock not checked); Bourns CAY06-220J2AS (convex, listed at LCSC); Yageo YC102 (flat; 22 ohm MPN not checked) | 2 | 0.80 x 0.60 (CAY06 0.85 x 0.60) | 0.50 (YC102 about 0.55; the extracted table is misaligned) | 31 mW | 5 % | possible for the D1/D2-type pairs (0.8 mm apart at the pin, so 0.3 mm jogs). New footprint |
| 4 x 0201 | Panasonic EXB-18V220JX (flat terminals); Yageo YC104-JR-0722RL (flat, 1 % as YC104-FR-…) | 4 | 1.40 x 0.60 | 0.40 | 31 mW | 5 % (1 %) | densest, but the pins are not contiguous (see above). 0.40 pitch with about 0.2 mm pads means no trace between pads and fan-in on every net. New footprint |
| 4 x 0402 convex/concave | Panasonic EXB-28V / EXB-N8V220JX; Yageo YC124-JR-0722RL; Bourns CAT10/CAY10; Vishay CRA04P | 4 | 2.00 x 1.00 | 0.50 | 63 mW | 5 % | larger than four 0201s placed where they fit. No benefit |
| 2 x 0603 concave, 0.8 pitch | **CTS 742C043220JP** (same series as R1) | 2 | 1.60 x 1.60 | 0.80 | 63 mW | 5 % | matches the D1/D2, D3/D4… pairs pin-for-pin, and the 742C043 pattern is on the board. But it is about 5x the area of two 0201s, and the space round U3 is full (see "Board facts") |
| 4 x 0603 concave, 0.8 pitch | CTS 742C083220JP (same series as R34); Panasonic EXB-38V; Bourns CAT16-220J4LF | 4 | 3.20 x 1.60 | 0.80 | 63 mW | 5 % | the 0.8 pitch matches U3, but four consecutive DQs are never on consecutive pins. Too big |
| Rohm MNR | MNR02 (2 x 0402), MNR04 (4 x 0402) | | 1.0 / 2.0 long | | 63 mW | 5 % | Rohm makes **no 0201-element** MNR part (MNR02 is the smallest, 1005 x 2). Not a 0201 option |
| Vishay ACAS / CRA | ACAS 0606/0612 (precision thin film), CRA04P (4 x 0402) | | 1.6+ | 0.5-0.65 | | | no 0201-element Vishay array was found. Not a candidate |

Corrections to the task's candidate list, from the datasheets:
- Panasonic **EXB-24V is 2 x 0402** (1.0 x 1.0 mm, 0.65 mm pitch), not 0201.
- The 4 x 0201 Panasonic part is **EXB-18V**, which has flat terminals.
- Yageo **YC124 is 4 x 0402**. The 4 x 0201 part is YC104.
- Bourns **CAY10/CAT10 are 4 x 0402** (0804). **CAY16 is 0603-based**. Bourns' 0201 array is **CAY06** (2 elements).

Array land patterns: Panasonic and Yageo both send the land pattern to a separate document ("data files" and
"Chip resistors mounting"), which could not be retrieved as text this session. A web-search excerpt of the
Panasonic table gives EXB-14V a/b/c = 0.30/0.30/0.30 mm, d = 0.80-0.90 mm. That value is **unverified**. If an
array is ever chosen, take the lands from the manufacturer's CAD data, not from this note.

## PCBWay assembly capability

From [pcbway.com/assembly-capabilities.html](https://www.pcbway.com/assembly-capabilities.html), fetched 2026-11-13:
- "we can accept components as small as 01005, 0201, 0402"
- "Fine Pitch Parts: we can assemble 0.25mm fine pitch parts"
- BGA "0.3mm pitch for rigid PCBs ... with X-ray testing"
- laser-cut stainless stencils
- AOI "checks for ... 0201 components"

The page does not mention resistor arrays, minimum pad spacing, stencil thickness or placement accuracy. A
0.4 mm-pitch 4 x 0201 array is inside the stated 0.25 mm fine-pitch limit. This board already has 0.5 mm-pitch
parts (U1, U2, U8) and 86 0201 parts on the Fab B Rev 2 release. So 0201 resistors add **no new process**. One
new BOM line (22 ohm) adds one unique part to the turnkey quote; 33 ohm adds none. **Ask PCBWay** only if an
array or 01005 is chosen.

## Electrical: are the part's parasitics negligible at 0.3 ns edges?

For a 0201, yes. For a part with twice that L and C, not on D8.

**Size comparison.** The SDRAM's own package is L_pkg 5.09 nH, C_comp 4.71 pF typ, from the vendor IBIS
`si/ibis/as4c32m16sb/Alliance-Memory_AS4C32M16SB-7TCN_Ibis.ibs`. U1's LVCMOS33 C_comp is 7.1-7.7 pF
(`si/vivado/zulu_a7_no_pmod_u1.ibs`). The ESL of a 0201 chip (about 0.3-0.5 nH) and its pad and body capacitance
(about 0.03-0.08 pF) are under 10 % and under 2 % of what sits at the pin already. The 0.6 mm body is electrically
short: about 4 ps against a 300 ps edge.

**Simulation.** The bus_sim.py read case was rerun through its own `simulate()` by
`si/series_r/parasitic_sim.py`, which monkeypatches only the series element. Results are in
`parasitic_results_r22.json` (`_r15`, `_r33`), and the log is in `run_r*.log`. Three variants, fab stack, D0-D15:
- **ideal**: R only. It reproduces the existing `results_r22.json` (ball -0.353 V, 17.2 %) and checks the wrapper.
- **0201**: R plus 0.5 nH ESL, 0.05 pF across the body and 0.08 pF pad-to-plane at each end.
- **heavy**: twice those values, as an upper bound.

Worst of the 16 nets in each row. "Budget" is the DS181 Table 4 share used, at UI 7.5 ns, computed the same way
as series_study.py.

| R | Variant | Corner | Ball Vmin | Ball Vmax | Ball budget | Die Vmin | Die budget | Read t10-90 |
|---|---|---|---|---|---|---|---|---|
| 22 | ideal | typ | -0.255 V | 3.439 V | 5.3 % | -0.119 V | 0 % | 0.65-0.97 ns |
| 22 | ideal | max | -0.353 V | 3.685 V | 17.2 % | -0.133 V | 0 % | 0.62-0.97 ns |
| 22 | **0201** | typ | -0.268 V | 3.497 V | 7.7 % | -0.111 V | 0 % | 0.65-0.98 ns |
| 22 | **0201** | max | -0.248 V | 3.651 V | **2.1 %** | -0.129 V | 0 % | 0.62-0.79 ns |
| 22 | heavy (2x) | typ | -0.219 V | 3.483 V | 0.9 % | -0.109 V | 0 % | 0.65-1.00 ns |
| 22 | heavy (2x) | max | **-0.461 V** | **3.821 V** | **99.0 %** (D8 only) | -0.146 V | 0 % | 0.63-0.81 ns |
| 15 | ideal | max | -0.424 V | 3.728 V | 30.0 % | -0.196 V | 0 % | 0.41-0.63 ns |
| 15 | 0201 | max | -0.418 V | 3.724 V | 8.9 % | -0.213 V | 1.1 % | 0.41-0.63 ns |
| 33 | ideal | max | -0.307 V | 3.667 V | 15.5 % | -0.110 V | 0 % | 0.78-1.32 ns |
| 33 | 0201 | max | -0.197 V | 3.623 V | 0 % | -0.106 V | 0 % | 0.76-1.34 ns |

The ideal rows reproduce `results_r15/r22/r33.json` and docs/si_analysis.md: -0.42 V / 30 %, -0.35 V / 17 %,
-0.31 V / 15 %. 160 cases ran with 0 errors.

**What this shows**
- With realistic 0201 parasitics every net stays under 10 % of the budget at the ball. Per net the change is
  within about +-0.06 V either way.
- The parasitics are **not exactly negligible on D8**, the net that is already the worst. D8's ball minimum goes
  -0.353 V (ideal), -0.219 V (0201), -0.461 V (heavy). The extra L/C shifts the phase of a ringing at U1's ball
  that is close to marginal.
- The budget number jumps because DS181 Table 4 is a step table: past 0.45 V the allowed time drops from 61.7 %
  to 25.8 % of the UI.
- At the die every case passes; the worst is 1.1 %.

**Conclusions for the part choice**
- Use the smallest part, a 0201: an 0402, or a poorly placed part with long necks, starts to resemble the
  "heavy" case.
- Keep it right at the pin.
- After placement, re-simulate D8 (and D3, D5, D13, which are the next most sensitive) with the real resistor
  position and stub. Per-net results are in `parasitic_results_r22.json`.

**Crosstalk inside an array (estimate, not simulated).** No manufacturer publishes the inter-element coupling.
The assumed values are Cm about 0.02-0.05 pF and Lm about 0.05-0.1 nH between adjacent 0201 elements at 0.4 mm
pitch.
- Capacitive part: Cm x dV/dt = 0.05 pF x 11 V/ns = 0.55 mA into about 23 ohm (22 ohm + driver on one side, the
  53 ohm Bottom line on the other) gives about 13 mV.
- Inductive part: Lm x dI/dt = 0.1 nH x about 0.12 A/ns gives about 12 mV.
- Total: about 25 mV per neighbour, about 50 mV with both neighbours switching. That is under 2 % of 3.3 V and
  small against the 0.8 V low-side noise margin.

So crosstalk is not the reason to avoid arrays. The pin order and fan-in are.

**Power.** The worst-case read charges at most about 11.5 pF through the resistor:
- 9.0-20.7 mm of line (`results_r22.json` len_mm) at about 0.156 pF/mm (`lines.json`), plus two vias, plus U1's
  C_comp of about 7.6 pF.
- Energy is 1/2 C V^2 = 69 pJ per edge at 3.465 V.
- At 143 MHz toggling every cycle this is **10 mW or less**, an upper bound that assumes all of it lands in the
  resistor.

That is 20 % of a 0201's 50 mW and 32 % of an array element's 31 mW. Writes charge only U3's 4-5.6 pF C_comp
through the resistor, about 5 mW. A resistor's tolerance does not matter here: 15-33 ohm all pass.

## Board facts the placement plan needs

Fresh extract of the PcbDoc on disk (md5 2a616c1c), olefile, read-only. Pad, via and track records were decoded
with the offsets documented in `Altium_backup/tools/route_inputs.py`.

- U3's DQ pads are 0.45 x 1.20 mm.
  - South row y = 6.17: D0 x37.95, D1 36.35, D2 35.55, D3 33.95, D4 33.15, D5 31.55, D6 30.75, D7 29.15.
  - North row y = 17.53: D8 29.15, D9 30.75, D10 31.55, D11 33.15, D12 33.95, D13 35.55, D14 36.35, D15 37.95.
- Each DQ net has exactly one 0.125 mm Bottom segment from the pad to a through via (0.35/0.20):
  - 0.88-0.94 mm for D0-D2 and D8-D15 (vias at y about 7.05 and 16.65);
  - 2.76-2.79 mm for D3-D7 (vias at y about 8.93-8.95);
  - every via sits under U3's moulded body (body edges at about y 6.77 / 16.93).
- A 0201 needs 0.90 mm of land length, so it cannot go inline in a 0.9 mm stub without moving that net's via. It
  cannot go under the body either.
- Outside the rows, Bottom is already full:
  - south: C4-C8 at y 3.05; C137/C138/C152-C154/C38/C40/C41 at y 3.95; vias at y 4.2-5.6 between them;
  - north: R80-R85 at y 19.05-20.85; C156; X1's mounting holes; about 40 vias in y 18.1-22.
- Top above U3 holds U2 (FT2232 LQFP-64, 32 pads in x 27.5-40, y 5-19) and 38 routed nets.
- This is why the smallest, one-per-net part is the right choice. Placement is a separate task.

## Sources

- [PCBWay assembly capabilities](https://www.pcbway.com/assembly-capabilities.html)
- Panasonic chip resistor array EXB datasheet (AOC0000C14):
  https://industrial.panasonic.com/cdbs/www-data/pdf/AOC0000/AOC0000C14.pdf
- Yageo YC/TC array chip resistors datasheet V.9 (Arrow copy): https://static.chipdip.ru/lib/634/DOC040634511.pdf
- Rohm MNR datasheet:
  https://fscdn.rohm.com/en/products/databook/datasheet/passive/resistor/chip_resistor_network/mnr-e.pdf
- [DigiKey RC0201FR-0722RL](https://www.digikey.co.nz/en/products/detail/yageo/RC0201FR-0722RL/5281382)
- [DigiKey EXB-18V220JX](https://www.digikey.co.uk/en/products/detail/panasonic-industry/EXB-18V220JX/671381)
- [DigiKey YC104-JR-0722RL](https://www.digikey.ie/en/products/detail/yageo/YC104-JR-0722RL/5951471)
- [DigiKey 742C043220JP](https://www.digikey.ca/en/products/detail/cts-resistor-products/742C043220JP/1124585)
- [DigiKey 742C083220JP](https://www.digikey.co.uk/en/products/detail/cts-resistor-products/742C083220JP/1124392)
- [Bourns CAY06-AS datasheet](https://www.mouser.com/datasheet/2/54/cay06-as-1102382.pdf)
- [ERJ-XGNJ220Y listing](https://www.onlinecomponents.com/en/panasonic/erjxgnj220y-44476456.html)
