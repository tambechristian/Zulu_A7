# Stage 8: the XADC knot is untied, and PWR_SWITCH is corrected (2026-09-29)

**Status: PLACED AND SAVED.** PcbDoc md5 `210a6f2b7669980309fb2472a125ad98`, 2026-09-29 12:07.
DRC archived as `docs/drc_stage8_2026-09-29.drc`.

Two changes, made in that order on the same day:

1. **The routing**, committed as `082f769` (PcbDoc `871a0669485754f6258364a8917f4b0e`).
2. **The PWR_SWITCH class correction**, which is what made the routing DRC-legal.

## 1. The routing

Stage 7's judge measured **NODE_P1 `R15-2 <-> R16-2` as vetoing 19 commits by itself**, and as the
named blocker on 12 of the 78 connections still open. It is the keystone. Untying it needed the two
removals the user had already approved: the **AIN16_N via at (43.300, 3.200)** and **AIN16_P's four
Bottom primitives** near R16. Both split their nets, so both got replacement copper.

7 vias and 26 tracks added; 1 via and 6 tracks removed. Verified against the saved PcbDoc:

| | before | after |
|---|---|---|
| NODE_P1 islands | 3 | **1** |
| AIN16_P / AIN16_N islands | 1 each | 1 each |
| GND SMD pads tied | 203 | **204** |
| `route_reach` | 140 / 140 | **140 / 140**, nothing walled off |
| DRC Un-Routed Net Constraint | 146 | **143** |

R13-2 is now tied. **R15-1 was left untied**: tying it walls off ANALOG-IO1, and an open connection is
recoverable where a walled-off one is not.

The AIN16 pair mismatch goes 0.062 -> 2.400 mm. That is deliberate and was settled before the stage
ran: the **AIN15 pair on this same board is already 2.286 mm (13.0 %) mismatched, placed and
shipping**. These are XADC inputs behind a resistor divider and a 1 nF anti-alias cap sampled in the
hundreds of kHz; 2 mm of 0.0762 mm outer track is about 13 mOhm and 0.2 pF against a kOhm source
impedance. Coupling symmetry, not length, is what matters here.

## 2. The DRC said 11 Width violations, and the gate had passed the plan clean

Altium raised **11 Width Constraint violations**, every one a NODE_P1 track at 0.0762 mm against
`Width_PWR_SWITCH`'s 0.2 mm (7.874 mil) minimum. Two separate defects, both now fixed:

- `tools/route_inputs.py` kept only `Width` and `Width_SDRAM`, so the **power Width rules never
  reached the model at all**. It now keeps every rule whose `RULEKIND` is `Width`.
- `tools/route_emit.py`'s `width_ok()` fell back to the global 0.0762 mm for any net not among the 67
  modelled ones, **ignoring class-scoped rules entirely**. The new `_class_width_min()` walks the
  Width rules in PRIORITY order the way Altium does and returns the tightest matching minimum.
  Re-run against the stage-8 plan, it reports exactly the 11 violations Altium found.

Both fixes shipped in `082f769`.

## 3. The board was wrong, not the copper: NODE_P0 and NODE_P1 left PWR_SWITCH

`PWR_SWITCH` held five nets. Three of them -- **NetL1_1 (L1-1<->U5-5), NetL2_1 (L2-1<->U6-5),
NetL3_1 (L3-1<->U7-5)** -- are the SC189 buck switching nodes. They are real switching loops and they
earn the 0.2 mm minimum.

The other two are not switching nodes at all. **NODE_P0** (R10-1, R11-2, R12-2) and **NODE_P1**
(R14-1, R15-2, R16-2) are the **XADC resistor-divider taps**, carrying microamps into an FPGA analogue
input behind a 1 nF cap. They were swept into the class by their names looking like power nodes.

The cost was not cosmetic. At 0.2 mm a NODE_P1 track needs `0.2 + 2 x 0.09 = 0.38 mm`, and the gaps it
must pass through in the y 3.950 resistor row are **0.30 mm** pad edge to pad edge. **NODE_P1 could
not be routed at all at that width** -- it was short by 0.08 mm. Dropping the two nets out of the
class puts them on the global `Width` rule (priority 7, `All`, 0.0762 mm minimum), which is what an
XADC tap wants.

This is a design-rule change and was the user's decision, taken 2026-09-29.

### How it was applied

`IPCB_ObjectClass` has no proven member-removal call in this build, so `FixPwrSwitchClass` in
`tools/ZuluSetup.pas` **removes the class object whole and re-makes it with `AddClass` under the same
name**. `Width_PWR_SWITCH` scopes by `InNetClass('PWR_SWITCH')` -- a name expression -- so it re-binds
to the new object, and nothing else on the board references the class. The script reported
`Removed 1 old class object(s)`. `MakeNetClasses` line 163 was updated to match, so the source of
record and the board agree.

### Verified from the saved file, not from the screen

- `Classes6/Data`: **30 class records** (unchanged), `PWR_SWITCH` appears **once**, members exactly
  `NetL1_1, NetL2_1, NetL3_1`. No duplicate class names.
- `Vias6/Data` is **byte-identical**. `Tracks6/Data` is the **same multiset** of 2154 records --
  identical in layer, net, both endpoints and width; Altium merely reordered 283 of them on save.
- Regenerating `tools/route_inputs.json` from the saved board: `tracks`, `vias`, `rules`, `nets`,
  `pads` all **identical**. The single difference in the entire board model is the class membership.
- `route_emit._class_width_min`: NODE_P0 and NODE_P1 now match **no** class-scoped Width rule and fall
  to the global 0.0762 mm; NetL1_1/L2_1/L3_1 still return 0.2 mm.
- `verify_stack.py` PASS; `board_preflight.py` CLEAN.

### The DRC, measured across the archive

| report | Un-Routed | **Width** | Plane relief | Net antennae | total |
|---|---|---|---|---|---|
| stage 4a, 09-21 | 145 | 0 | 1 | 50 | 200 |
| stage 5, 09-23 | 146 | 0 | 1 | 50 | 197 |
| stage 5b, 09-24 | 146 | 0 | 1 | 50 | 197 |
| stage 8 routed, 09-29 10:36 | 143 | **11** | 1 | 50 | 205 |
| **stage 8 + class fix, 09-29 12:05** | **143** | **0** | 1 | 50 | **194** |

The 11 Width violations are gone and **every other count is unchanged, line for line**.

## A correction to the stage-8 commit message

`082f769` says the DRC went "7 -> 18 Width violations" and "Un-Routed 144 -> 141". **Both figures are
wrong**, and the archived reports above are the record. Width Constraint was **0** in every report
before stage 8; stage 8 introduced **11**; this fix returns it to **0**. Un-Routed went **146 -> 143**.
The stage-8 delta of three closed connections is right; the absolute numbers were not.

## Still open

- **78 of the 140 signal connections**, minus the three stage 8 closed.
- **R15-1's GND tie** (and the third untied GND pad), still blocked on ANALOG-IO1's corridor.
- The **FT-REF / USB pair / U2-5** three-way contention -- a placement decision, not a routing one.
- The **USB gap contradiction**: the PcbDoc's `DiffPairsRouting` says width and gap are both 0.150 mm;
  the docs say 0.125 mm, and 0.125 is where the 87.4 Ohm 2-D FEM figure came from. **If 0.125 is
  wanted, the RULE must be edited, not the copper.**
- Teardrops, final DRC, IBIS, fab outputs, the JLC order.
