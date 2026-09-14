# DFM enquiry to JLCPCB — RESOLVED 2026-09-14 (sent 2026-09-12, answered by Jasper Wu, JLCPCB engineering support)

This file started with four multi-part questions. Reading JLCPCB's own published pages on
2026-09-11 answered all but one of them, so the rest are recorded below as **answered** with the
verbatim source, and are not to be asked again. **Only section 1 goes to the fab.**


> ## Answered. 3 mil stands, impedance control is free, and they volunteered a via warning.
>
> **Their reply, verbatim (2026-09-14):**
>
> > Dear Customer,
> >
> > Thank you for contacting JLCPCB engineering support with your detailed technical inquiry regarding BGA fan-out routing and controlled impedance for your 6-layer project.
> >
> > Here are the direct answers to your questions:
> >
> > 1. Controlled Impedance vs. 3 Mil BGA Fan-Out Allowance: Plainly answered: Ordering with Controlled Impedance does NOT withdraw or invalidate the 3 mil allowance for your BGA fan-outs.
> >
> > • When you select Controlled Impedance, our CAM engineers apply impedance matching and adjustments ONLY to the specific designated impedance net (your single USB 2.0 90 ohm differential pair on the top layer) based on the JLC06161H-3313E stackup.
> >
> > • All other non-impedance traces on the board, including your 238 BGA fan-out traces under the XC7A35T (CPG236) and your SDRAM bus, retain full access to our fine-line manufacturing capabilities down to 3 mil (0.0762 mm).
> >
> > • Therefore, you DO NOT need to drop the controlled impedance service. You can keep both the controlled 90 ohm USB pair and your 3 mil / 0.09 mm escape routing under the BGA lands.
> >
> > 2. Surcharges for 3 mil / 3.5 mil and Impedance Control:
> >
> > • Controlled Impedance Fee: On 6-layer boards using our standard stackups (including JLC06161H-3313E), Controlled Impedance is provided with NO extra charge ($0 surcharge).
> >
> > • 3.5 mil / 3.5 mil Line & Space: This falls within our standard 6-layer manufacturing baseline, so there is no difficulty surcharge.
> >
> > • 3.0 mil / 3.0 mil Line & Space: Because line and space under 3.5 mil require high-precision LDI exposure, vacuum etching, and optical inspection, a high-precision process fee of 20% on the PCB board price applies. When configuring your quote online, selecting 3 mil as the minimum track/spacing will reflect this 20% process tier.
> >
> > 3. Etch Compensation and Finished Width Tolerances:
> >
> > • Etch Compensation in CAM: In wet chemical etching, lateral undercutting naturally occurs. To achieve the nominal finished trace width on your bare board, our CAM engineers apply a standard positive etch compensation of approximately 0.5 mil to 0.8 mil (approx. 0.013 mm to 0.020 mm) on 0.5 oz base copper foils on the photo tooling.
> >
> > • For your 3 mil (0.0762 mm) BGA escape traces, CAM compensation is tightly calibrated to ensure the finished copper trace on the board centers around the nominal 3.0 mil target.
> >
> > • Clearance Protection in CAM: CAM compensation algorithms strictly protect clearance. If widening a trace would compromise the electrical clearance between adjacent BGA lands below the etching threshold, CAM preserves the required space to prevent solder bridging or copper shorts. Your drawn geometry (0.225 mm land with 0.2748 mm edge-to-edge gap, 3 mil trace, and 0.09 mm clearance) provides healthy manufacturing margin.
> >
> > • While general board-wide tolerance is listed at +/-20% to encompass isolated peripheral features, our actual production tolerance on fine-pitch multi-layer inner/outer traces using laser direct imaging (LDI) typically holds within +/-0.3 to +/-0.5 mil (+/-8% to +/-12%).
> >
> > 4. Proactive Engineering Tip Regarding Vias: You mentioned using 0.20 mm drill on a 0.30 mm land (annular ring of 0.05 mm / 1.97 mil). For multilayer through-hole vias, our standard recommendation is a minimum annular ring of 0.075 mm (3 mil), which corresponds to a 0.20 mm drill on a 0.35 mm pad. While 0.20/0.30 mm can be produced with high-precision registration, adding teardrops to your 0.20/0.30 mm vias in your layout is strongly recommended to maximize drill-to-pad integrity.
> >
> > We hope this provides the clarity you need to proceed confidently with your layout. Please let us know if you need any further engineering details!
> >
> > Best regards,
> >
> > Jasper Wu
> >
> > JLCPCB Customer Service Team
>
> **What it decides**, every number re-measured from `Pads6` on 2026-09-14 (land 0.225044, worst
> pitch 0.499872, land-edge gap 0.274828 mm, clearance rule 0.09):
>
> | asked | their answer | consequence for the board |
> |---|---|---|
> | Does impedance control withdraw the 3 mil allowance? | **No.** CAM touches only the designated pair. | The escape stays **3 mil / 0.09 mm** and the USB pair stays controlled. `Width_PWR_VCC3V3`'s Top min of 0.0762 stands; nothing in the rule set moves. **The fan-out is unblocked.** |
| surcharge | impedance **$0** on standard stackups; 3.5/3.5 baseline; **3/3 is a +20 % process tier** (LDI, vacuum etch, AOI) | Budget +20 % on the bare board. **The online quote must have 3 mil selected as min track/space**, or the order is placed in the wrong tier. |
> | etch compensation | +0.5–0.8 mil on the photo tooling, 0.5 oz base; finished 3 mil **centres on nominal**; CAM protects clearance; real fine-line tolerance **±0.3–0.5 mil (±8–12 %)**, not the published ±20 % | Escape margin at +12 %: clearance/side **0.094742 vs 0.09, +0.0047 mm** (it was +0.0017 at the ±20 % we argued from). At 3.5 mil the same +12 % **fails by 0.0024** — the wider trace is still the one that would fail, so the etch follow-up we had drafted is moot. |
> | *(not asked)* the via ring | recommend **0.075 mm ring = 0.20 drill / 0.35 land**; 0.20/0.30 **is producible** with high-precision registration; **teardrops strongly recommended** on 0.20/0.30 | A 0.35 land is **impossible at an interstitial (diagonal) position** — centre-to-land-edge is 0.240941 mm and it needs 0.265 (−0.024). At a **vacant ball-grid position** it clears by +0.122 (0.30 clears by +0.147), and two 0.35 lands on adjacent grid positions keep 0.150 mm between them. So the choice is per position, and it is a fan-out decision, not a rule change: interstitial vias were already "legal and not manufacturable" (`docs/routing_readiness.md`) at +0.94 µm with a 0.30 land; this makes the case against them final. **Add teardrops before the fab output** whatever the land. |
>
> Nothing here is to be asked again. The question below is kept as the record of what was sent.

---

# 1. THE QUESTION

**Does ordering with controlled impedance withdraw the "3 mil is acceptable in BGA fan-outs"
allowance?**

Your general capability page states, in the row *Min. track width and spacing (1 oz)*:

> Multilayer: 0.09 / 0.09 mm (3.5 / 3.5 mil). **3 mil is acceptable in BGA fan-outs.**
> — https://jlcpcb.com/capabilities/pcb-capabilities

But two other pages state a flat 3.5 mil with no exception and no cross-reference:

> Min. Trace width/Spacing | Min. Via | Min. BGA
> 3.5mil | 0.2mm | 0.25mm
> — https://jlcpcb.com/impedance, under *"Multilayer high precision PCB's with impedance control"*

> Minimum trace width and spacing | 3.5mil (0.09mm)
> — your dedicated 6-layer product page

On https://jlcpcb.com/impedance the string "BGA" appears exactly once — in the `Min. BGA` column
header — and "fan-out", "fanout" and "3 mil" appear zero times. So nothing there withdraws the
allowance explicitly; it simply is not mentioned.

**Why it decides the board.** Our part is an XC7A35T in CPG236: 238 balls on 0.5 mm pitch, lands
held at **0.225 mm**, which leaves **0.2748 mm** between adjacent land edges. One escape trace runs
between two lands, so it needs `width + 2 × clearance`:

| line / space | needs | margin in 0.2748 mm | |
|---|---|---|---|
| 3 mil / 0.09 mm *(as drawn)* | 0.2562 mm | **+0.0186 mm** | works |
| 3.5 mil / 3.5 mil | 0.2667 mm | **+0.0081 mm** | works, barely |
| 4 mil / 4 mil | 0.3048 mm | **−0.0300 mm** | impossible |

The land cannot be enlarged to buy margin — at 0.25 mm the gap falls to 0.2499 mm and the escape
closes entirely — and the trace cannot go below 3 mil, which is your floor.

> **So, plainly: if we order this board with controlled impedance on one differential pair, do the
> 238 BGA fan-out traces still get the 3 mil allowance, or does the whole board fall under the
> 3.5 mil impedance-page figure?**

If the answer is "3.5 mil applies", we would rather **drop the controlled-impedance service
altogether** and accept the pair at whatever your standard process yields, than lose 0.0105 mm of
fan-out margin. Please also tell us the surcharge for 3 mil / 3.5 mil line and space on a 6-layer
board, and whether impedance control is charged separately.

One related figure that is not published anywhere we could find: **what etch compensation do you
apply?** Your track width tolerance is ±20% and your impedance tolerance is ±10%, and those two
cannot both hold unless you compensate the width in CAM. At +20% a 3 mil trace finishes at
0.0914 mm and our fan-out margin falls to **+0.0034 mm**, so the answer matters to us.

---

# 2. ANSWERED FROM YOUR OWN PAGES — recorded, not to be asked

Each of these was going to be a question. All quotes read live on 2026-09-11.

| was going to ask | answer | source |
|---|---|---|
| Will you press our custom 6-layer stackup? | **No — and no need.** *"The PCB will be strictly produced in accordance with the following stackup."* You publish 15 six-layer 1.6 mm builds. **JLC06161H-3313E** matches our design intent better than the custom one we had drawn, so we have adopted it. | jlcpcb.com/impedance |
| Minimum inner copper to board edge? | **≧0.2 mm.** *"Copper clearance from routed board edges: ≧0.2 mm"* | capabilities page |
| Will you run a 0.050 mm annular ring on a 0.20 mm drill? | **Yes, it is your published minimum.** *"Multilayer: 0.15 mm hole size / 0.25 mm via diameter"* — the same 0.050 mm ring. Noted: *"0.2mm or 0.25mm hole size with via diameter less than 0.45mm, will cost more."* | capabilities page |
| Will you build a 0.225 mm BGA land as drawn? | **Yes, with ENIG.** *"0.2mm-0.25mm BGA pad diameter requires ENIG"* — we are ENIG. *(Held with some caution: 0.25 mm appears as a minimum on three of your pages and 0.2 mm on one. If our reading is wrong, say so, because this number decides the board.)* | capabilities page |
| Will you hold a 0.175 mm solder-mask dam? | **Yes.** *"Min. pad spacing: 0.10 mm (green, red, yellow, blue, purple)"* | capabilities page |
| What impedance do you calculate for the pair? | **Computable from your own data.** With your mask model (C1 1.2 mil, C2 0.6 mil, C3 1.2 mil, CEr 3.8), our 0.15 mm / 0.15 mm pair over 3313 at 0.0994 mm gives **≈88 Ω** against a 90 Ω target, inside your **±10%** (±5% on request). Kept as drawn. | jlcpcb.com/impedance + capabilities |
| Is outer copper base or finished? | **Finished.** *"Finished Outer Layer Copper"*, *"Finished copper weight of inner layer is 0.5oz by default."* Our earlier "0.5 oz base plated to 1 oz" phrasing was wrong and has been dropped. | capabilities page |

**One thing your pages told us that we had wrong, and have now fixed:** *"Keep at least 0.09 mm
clearance between soldermask openings and neighboring traces."* Our mask expansion was 0.05 mm,
which left only 0.049 mm between each BGA opening and the escape trace beside it — every one of
the 238 in violation. The openings are now 1:1, giving 0.099 mm.

---

# 3. THE BOARD, FOR CONTEXT

69.85 × 25.40 mm, 6 copper layers, **1.6 mm**, **all through-holes — no blind, buried or
microvias**, ENIG. Stackup **JLC06161H-3313E**. Layer roles L1 signal / L2 ground / L3 signal /
L4 signal / L5 ground / L6 signal — chosen because a 39-net SDRAM bus runs on L3 and L4 and must
couple to its planes rather than to itself, which is why the default `-3313` build is not suitable
for us. Vias are 0.20 mm drill on a 0.30 mm land. One 90 Ω USB 2.0 differential pair on the top
layer at 0.15 / 0.15 mm. Nothing is routed yet, so the fan-out can still be designed around your
answer.

---

*Every figure above is either measured from our own design files or quoted from JLCPCB's published
pages on 2026-09-11, with the URL given so it can be re-checked. Their verbatim answer of
2026-09-14 is at the top; the consequences table there supersedes the arithmetic in section 1
where the two differ (their real etch tolerance is ±8–12 %, not the ±20 % argued from).*
