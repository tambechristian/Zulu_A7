# PCBWay assembly release (2026-10-07)

Fabrication moved to PCBWay, so the production assembly release now targets a PCBWay turnkey order, in which
PCBWay fabricates the HDI board and assembles it. `tools/generate_jlcpcb_assembly.py` gained
`--assembler {pcbway,jlcpcb,neutral}`.
- **pcbway:** the default.
- **jlcpcb:** reproduces the old JLCPCB files byte for byte.
- **neutral:** what the HDI copy uses. `--assembler-neutral` still works.

## Files (`assembly/`)

| File | What changed for PCBWay |
|---|---|
| `Zulu_A7_PCBWay_BOM.csv` (was `Zulu_A7_JLCPCB_BOM.csv`) | See the BOM list below. |
| `Zulu_A7_PCBWay_CPL.csv` (was `Zulu_A7_JLCPCB_CPL.csv`) | SMT parts only (PCBWay's centroid rule): J1 and X2 are hand-soldered. Every other row is unchanged. |
| `Zulu_A7_Assembly_Notes.txt` | Rewritten for PCBWay; see the notes list below. |
| Assembly drawings | The LED cathode (pad K) is marked with a red bar. LD1-LD5 had no polarity mark anywhere in the release. The footer refers to PCBWay's engineering review. |

The new BOM:
- **Columns:** PCBWay's own template: Item #, Designator, Qty, Manufacturer, Mfg Part #, Description / Value,
  Package/Footprint, Type (SMD / thru-hole / DNS), Your Instructions / Notes.
- **No LCSC column and no "consign" wording.** PCBWay buys by manufacturer part number.
- **X2** is split into its two strip part numbers (PRPC009SAAN-RC x2, PRPC011SAAN-RC x2).
- **JP3/JP4** appear as DNS rows.
- **Per-line instructions:**
  - U1 and U2: authorized channels only.
  - SC189 look-alikes: which voltage goes where.
  - LED polarity.
  - X1: one reflow only.
  - X2: pin orientation.
- **Descriptions** are the schematic SPEC without its design commentary.

The new notes:
- **Upload set:** with the recommended form settings (unique parts 59, SMD 170, BGA/QFP 2, THT 5 strips with 52
  joints).
- **Sensitive parts:** text ready to paste into the sensitive-parts box.
- **Order settings:** X-ray count, panelization (Panel by Supplier, rails, tab route, depanel by router) and
  fiducials on the rails.
- **HDI and U1 gate:**
  - U1's top land field holds 59 tented but unfilled 0.20 mm through vias, all at depopulated ball sites. The
    sites are classified by U1's 0.5 mm grid, as an independent check found.
  - PCBWay's BGA rule asks for them to be plugged.
- **CPL conventions.**
- **Reflow order:** bottom first, top last. X1 is rated for one reflow.
- **X2:** the short post end goes up through the board, and the housings overlap R1 and five 0603 caps in plan view.
- **X1:** stakes hand-soldered after reflow.
- **Polarity:** LED polarity by side and X, and look-alike-part checks.
- **Stencil and sourcing:** stencil notes; sourcing with no substitution without approval.
- **QA and order review:** a QA list and the order-review checklist.

## How it was checked

- **Research and review:** a research workflow read PCBWay's pages (BOM template, centroid rules, DNP marking,
  substitutes, sourcing policy, the order-form fields) and the project files, and drafted the notes. Three
  independent reviewers then tried to refute the draft, checking:
  - the PCBWay facts;
  - the board and BOM facts;
  - completeness for an assembly engineer.
- **Reviewer findings applied:**
  - the "consign" wording in the old BOM;
  - LD1-LD5 had no polarity mark;
  - X2's pin orientation was unstated;
  - X1's stake fill;
  - the U1 via plugging;
  - the panel form fields;
  - the THT rows in the CPL;
  - the 58-line vs 59-part count.
- **Generator checks:** it validates the PCBWay BOM columns and quantities, the DNS rows, the SMT-only CPL, and
  that the notes contain no JLCPCB/LCSC text and no line over 88 characters.
- **Not pre-approved:** the alternates in `docs/pcbway_bom_substitutes.csv` (2026-09-08, partly stale) were left
  out. The notes ask PCBWay to raise an engineering query rather than substitute.
- **Fab notes, U1 vias:** `PCBWAY_FAB_NOTES.txt` called U1's vias interstitial. It now says where they sit
  and asks PCBWay to plug or fill the through vias, matching the assembly notes.
- **Fab notes, X1 slots:** `PCBWAY_FAB_NOTES.txt` called X1's slots "rear shell legs". They are the front shell stakes at the
  mating-face end beside the board edge (MH1/MH2 are the rear pegs). The wording was corrected here and in the
  HDI copy's notes.
