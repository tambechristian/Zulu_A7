# Switching the stack to JLC06161H-3313E — the procedure

**Status 2026-09-12: APPLIED AND VERIFIED.** `tools/verify_stack.py` prints
`PASS -- stack matches JLC06161H-3313E`, laminate **1.65038 mm** against the 1.65040 mm quote
(the 0.00002 mm gap is the file's 4-decimal mil quantum, not an error). Total including mask
1.67070 mm. The 35 deltas are closed. What survived the edit, checked from the saved file:
two `POLYGONTYPE=Split Plane` polygons, all 47 rules including `SolderMaskExpansion_U1`, both
planes still `GND` at 20 mil pullback, and all six `LAYERID`s unchanged.

**All FIVE stack copies agree**, including the two the verifier does not read: the base64/zlib
`V9_STACKCUSTOMDATA` blob holds every new value and not one stale one, and `V9_CACHE_LAYERn_*`
reads 1.378 mil outer / 0.5984 mil inner / 44.126 mil at Dk 4.523 for the L3-L4 gap. Doing the
edit in the GUI rather than by patching text is what made that true.

## Why

The board's stack was built as a **custom** profile on the belief that *"JLC publish one 6-layer
1.6 mm build and this is not it"* (commit `74eef9a`). That belief was wrong: JLCPCB publish
**fifteen** 6-layer 1.6 mm templates, and `jlcpcb.com/impedance` says *"The PCB will be strictly
produced in accordance with the following stackup."* One of the fifteen meets the design intent
**better than the custom build** on both axes:

| | L1–L2 | L2–L3 | L3–L4 | L4–L5 | L5–L6 | ratio |
|---|---|---|---|---|---|---|
| custom (now) | 0.0994 | 0.1164 | 1.0173 | 0.1164 | 0.0994 | 8.74 |
| **JLC06161H-3313E** | 0.0994 | 0.1000 | **1.1208** | 0.1000 | 0.0994 | **11.21** |
| default if left unspecified (`-3313`) | 0.0994 | 0.5500 | 0.1164 | 0.5500 | 0.0994 | **0.20** |

The custom build also has a defect nobody had spotted: **L2 and L5 each sit between two prepregs
with no core to be etched on**, so they would have to be bare foils. All fifteen published builds
etch their inner layers on copper-clad cores at L2/L3 and L4/L5. (A core *between* L3 and L4 is
not a defect — JLC do exactly that in three of the fifteen, and those three are the three
highest-ratio builds.)

## What was checked, and what it cost

- **The USB pair is bit-for-bit unchanged: 87.37 Ω on both stacks.** Two independent 2-D FEM
  solvers, agreeing to the digit. The pivot is that Altium's `DIELHEIGHT` is copper-face to
  copper-face — verified from the file, where copper 0.141122 + dielectric 1.469222 = 1.610345 mm
  exactly — so thinning L2 does not move the reference plane. Skin depth confirms the thinner
  plane is invisible above 75.6 MHz.
- **Aspect ratio passes.** 1.5900/0.20 = 7.95:1 → 1.6504/0.20 = **8.25:1**, against JLCPCB's
  published *"Do not exceed 10:1 when plating through-holes"*. Use the **laminate** figure, not
  the mask-inclusive one: drilling happens before mask.
- **Thickness is inside a tolerance we were already buying.** JLC give ±10% for ≥1.0 mm, i.e.
  1.44–1.76 mm. Both 1.6103 and 1.6707 mm sit inside.
- **SDRAM broadside L3↔L4 crosstalk improves 14–37%.**
- **COST 1 — inner copper thins 0.0175 → 0.0152 mm.** VCC1V0's 0.400 mm inner track goes from a
  9.7 °C rise to **12.2 °C** at 367 mA; IPC-2221 wants 0.4515 mm. See *Width_PWR_RAILS* below.
- **COST 2 — SDRAM Z0 on L3/L4 drops 11–12%**, not the 5.6% a Dk-only reading gives: the gap
  thins *and* Dk rises, both in the same direction. The 50 Ω inner width moves 0.1651 → 0.1247 mm,
  a 24% narrowing. Re-derive L3/L4 widths when routing.

## The edit — fourteen fields, in place

> **DO NOT REBUILD THE STACK.** Deleting or re-adding a copper row, or using a preset import /
> "load from file", recreates L2-GND and L5-GND as signal layers, reverts `PLANE1NETNAME` /
> `PLANE2NETNAME` to *(No Net)*, resets the 20 mil pullback and strands the two locked Split Plane
> polygons. Altium does not warn you. **Edit dielectric rows in place only.**

> **DO NOT TYPE THE COPPER WEIGHT.** Altium links Weight↔Thickness at 1 oz = 1.4 mil, so typing
> `0.5oz` writes 0.01778 mm — 17% thicker than target. **Type Thickness, in mm, with the `mm`
> suffix.** Afterwards the Weight cell will read about 0.43 oz. That is correct; do not "fix" it.

`Design ▸ Layer Stack Manager`, then **turn Stack Symmetry OFF** before typing anything.

| row | field | set to |
|---|---|---|
| Top Layer | Thickness | `0.035mm` |
| *Dielectric 2* (L1↔L2) | — | **leave alone** — already 0.0994 mm / Dk 4.100, and it is the USB pair's reference |
| L2-GND | Thickness | `0.0152mm` |
| Dielectric 4 (L2↔L3) | Type, Thickness, Dk | **Core**, `0.1mm`, `4.6` |
| L3-SIG | Thickness | `0.0152mm` |
| Dielectric 1 (L3↔L4) | Thickness, Dk | `1.1208mm`, `4.523` — leave Type as **Dielectric**, see below |
| L4-SIG | Thickness | `0.0152mm` |
| Dielectric 5 (L4↔L5) | Type, Thickness, Dk | **Core**, `0.1mm`, `4.6` |
| L5-GND | Thickness | `0.0152mm` |
| *Dielectric 3* (L5↔L6) | — | **leave alone** |
| Bottom Layer | Thickness | `0.035mm` |

**The L3–L4 gap is entered as ONE row, not three.** JLC build it as 7628 0.21040 / bare core 0.700
/ 7628 0.21040, but the file's legacy `LAYERn` block has only one dielectric slot per copper layer
and no dielectric-only slot, so three rows would put the file's stack copies into disagreement and
renumber every `V9_STACK_LAYERn` below the insertion. The merged Dk is the **series-capacitance**
value, not a mean: `1.1208 / (0.21040/4.4 + 0.700/4.6 + 0.21040/4.4) = 4.5228`.

> The merged row is a **solver model, not a build recipe.** Do not hand it to the fab as the
> lamination sequence — **order the stackup by name, `JLC06161H-3313E`, selected in the
> impedance-control flow, and get it onto the order acknowledgement.** A free-text remark is not a
> binding channel, and the substitution is not cosmetic: `-3313` and `-1080` put L3 0.55 mm from
> its GND reference and then leave L3 and L4 facing each other across 0.1088 mm.

## The `DIELTYPE` code, corrected

Applying this edit proved what the 2026-09-11 notes had only guessed. Typing `Core` into the
Layer Stack Manager's Type cell and reading the saved file back gives **1**, not 0:

| code | Layer Stack Manager shows | in this board |
|---|---|---|
| 0 | `Dielectric` (generic) | Dielectric 1, the merged L3↔L4 gap |
| 1 | `Core` | Dielectrics 4 and 5 |
| 2 | `Prepreg` | Dielectrics 2 and 3 |
| 3 | `Surface Material` | both solder masks |

`verify_stack.py` had `CORE = 0` and even said code 1 was unknown. That was wrong, and it was
wrong in the way the project keeps getting caught by: the FR-4 row *displayed* as `Dielectric`
and was *called* a core in prose, so prose became the constant. The verifier now carries
`GENERIC, CORE, PREPREG, SURFACE = 0, 1, 2, 3`.

**Dielectric 1 is deliberately left as generic `Dielectric`, not `Core`.** It is 7628 + 0.7 mm
core + 7628 merged into one row; labelling it `Core` would assert a single-core build that JLC
do not do there. `Dielectric` is the honest label for a merged row, and it is the label that
matches the warning above: the merged row is a solver model, not a lamination recipe.

## Afterwards

```bash
python tools/verify_stack.py     # must print PASS and 'laminate 1.65040 mm'
python tools/board_preflight.py  # wider check
```

Then confirm from the file, not the dialog, that `PLANE1NETNAME=GND`, `PLANE2NETNAME=GND`,
`PLANE1PULLBACK=PLANE2PULLBACK=20mil`, that `Polygons6` still holds two `POLYGONTYPE=Split Plane`
objects, and that `Rules6` is unchanged.

**`verify_stack.py` checks three of the file's FOUR stack copies.** Board6/Data also carries
`V9_STACKCUSTOMDATA` — base64 of zlib, a 13.9 kB `<StackupDocument>` that is the Layer Stack
Manager's own serialization, repeating every thickness, Dk, weight and the pullback. It cannot be
text-edited. **This is the reason the edit must go through the GUI**: a scripted or offline edit
would print PASS while that blob still held the old stack. Adding `V9_CACHE_LAYERn_*` to the
verifier (a fourth text copy it also misses) is about eight lines.

## Follow-on, not part of this edit

- **`Width_PWR_RAILS` needs raising.** Preferred 0.400 → **0.500 mm**; max 1.000 → **1.500 mm**
  (VCC3V3 at 662 mA needs 1.019 mm on an inner layer, which the present rule cannot even express).
  Note that **`PREFEREDWIDTH` is router guidance — Altium's Width rule only *checks* MINLIMIT and
  MAXLIMIT** — so a 3 mil VCC1V0 track passes DRC today. MINLIMIT cannot simply be raised, because
  VCC1V0, VCC1V8 and VCC3V3 all have BGA balls and must neck to 3 mil to escape; the per-layer
  Width table is the lever, since the thermal risk is on the inner layers and the necking is on
  Top.
- **VCC3V3 (662 mA) and VU (495–720 mA) were already inadequate on a 0.400 mm inner track before
  this change** — 37.0 °C and 19.1 °C rise on the old stack. The copper change makes them worse
  but did not cause them. Keep them on outer copper or in pours.
- **Altium's own impedance readout will disagree with JLC's** until the mask rows are changed from
  0.4 mil / Dk 3.5 to JLC's published 1.2 mil / Dk 3.8 — Altium currently reads about **+4.25 Ω
  high**, so tuning the pair to read 90 Ω in Altium would build ≈86 Ω.
