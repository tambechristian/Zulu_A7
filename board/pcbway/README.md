# PCBWay variant — provisional, do not edit by hand

`zulu_a7.sch` and `zulu_a7.brd` in this directory are a complete, openable Eagle pair
for the **PCBWay 1+4+1 HDI** build. They are **generated**, not authored:

```bash
python tools/make_board.py --fab pcbway
```

Anything you edit here is lost on the next run. **The one schematic to edit is
`zulu_a7.sch` at the repository root.** Both variants come from it, and the only
thing that differs between them is the diameter of the 238 CPG236 ball lands.

## Why this variant exists

The active fab is JLCPCB, at a **0.225 mm** land. This variant keeps the full
**0.275 mm** land — UG475's maximum, and its recommended 1:1 ratio to the package
pad "for improved board level reliability". **HDI is the only route that keeps
it**, and JLCPCB does not do HDI at all.

| | root — JLCPCB | here — PCBWay |
|---|---|---|
| ball land | 0.225 mm (0.82:1) | **0.275 mm (1:1)** |
| solder mask opening | 0.325 mm | 0.375 mm |
| line / space | 3 mil trace, 3.5 mil clearance | 0.065 / 0.065 mm |
| escape | trace between two lands, +0.0188 mm | laser via inside every land |
| vias | 0.2 mm drill, 0.30 mm land, through | 4 mil laser, L1→L2 |
| status | **active, route this one** | provisional |

## What is not settled

1. **The DFM enquiry is unanswered.** It went out 2026-08-26; see
   `board/PCBWAY-DFM-ENQUIRY.md`, questions 5–7. Until they reply this is a
   guess at what they will build, made from their published HDI page.
2. **The layer plan does not survive HDI unchanged.** A 1+4+1 build lands every
   ball on L2, which `STACKUP.md` has as a solid ground plane. That is a rework
   of the plan, not a parameter, and it is not done.
3. **The stackup in the `.dru` is still the through-hole one.** HDI will change
   it. Do not compute an impedance width from this file until PCBWay sends the
   real build.

So: this pair is here so the option stays open and comparable, not because it is
ready to send. Route the root pair.

## Checking it

```bash
python tools/check_board.py board/pcbway/zulu_a7.brd board/pcbway/zulu_a7.sch
```

`check_board.py` reads the fab out of the board's design-rules name and checks
the rules *and the land* against it, so a board carrying the wrong land for its
fab fails rather than looking fine.
