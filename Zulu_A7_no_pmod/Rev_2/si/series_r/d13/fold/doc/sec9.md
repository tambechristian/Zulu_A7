## 9. Risks and what is not covered

1. **R132 is the one D13 site, and it is tight.** It sits 0.2035 mm (pad box) from R131 with a 0.1035 mm mask web
   and overlapping courtyards, its courtyard overlaps U2's by about 0.05 mm, and its new copper has margins of
   +0.0032 (L3) and +0.0044 (Top) mm. It needs U1's designator moved (decision 13) and the gnd47 GND re-tie. Its
   U3-side Top track runs under U2's body corner with a 0.044 mm mask cover to U2-48 (decisions 14 and 15). If
   PCBWay rejects it, `d13/u1_end/plan.json` keeps R133/R134 and leaves D13 without a resistor (it then passes on the
   fab stack at 93.8 % and fails on the PcbDoc stack at 507.5 %).
2. **R129-R130 assembly spacing.** About 0.23 mm body to body at maximum tolerance, courtyards overlapping by
   0.04-0.07 mm, ComponentClearance 0.26 against 0.254 (6 um margin) on Altium's pad-box measure. A GUI DRC with
   that rule on sits at the edge. Five 0201s now sit in a column at x 38.45-39.7 on Top beside U1 (R127, R129-R132),
   with 0.10-0.16 mm mask webs and 45-degree jogs ending under the pads. Fallback: `d10/stagger/plan.json`
   (decision 12).
3. **Not simulated:**
   - coupling between adjacent new R pads, the fold-back returns and the Top column R127/R129-R132 with its parallel
     runs at x 38.5-40.2;
   - coupling of the new SDRAM-D13 Top track under U2 to USB5V0 and the U2 leads;
   - the CHAN7 / SDRAM-D14 projected stack overlap at (45.4,17.2) / (45.3,17.15), about 15 fF into an XADC input;
   - the new L2 openings at D12 and D13 and the L5 openings at D9, D14 and D15 (bus_sim treats the planes as ideal);
   - the IBIS slow corner;
   - the DC and decoupling effect of the south re-work: FT-VCORE trunk 0.5 -> 0.16 mm, U3-9 VDDQ now via L5, U3-12
     +0.41 mm.
4. **Estimated values:**
   - the 0201 parasitics are estimates, but the sensitivity runs show they barely matter;
   - the body proxies are pads plus Mech3/Mech4, because the board has no 3D bodies and the PcbLib has no TSOPII-54;
   - U3's body is assumed centred on its pad field.
5. **Checker vs Altium.** Several margins are under 0.011 mm, including the inherited +0.000 at the x 38.5 via
   column on L3/L4, the two +0.0003 Top corners and R132's new +0.0032 / +0.0036 / +0.0040 / +0.0044. Every margin
   below Altium's 2.54 um resolution is inherited from the 13-resistor plan. The independent checkers are calibrated
   to the board's DRC 0, but Altium's own DRC at gate 7 is what decides, including its 2.54 um rounding after
   remove/re-add.
6. **Net class.** If any SDRAM-Dn is left out of SDRAM_DATA, nothing fails, but Clearance_SDRAM_INNER and
   Width_SDRAM silently stop covering it (gate 4).
7. **Via-in-pad.** Seven sites need VIPPO, filled and capped: R128-1/2, R131-1/2, R132-2, R133-1, R134-1. R132-R134
   each have the via in one pad only; unfilled, their solder areas differ by 19.6 % (tombstoning).
8. **D14 and D15 through vias.** The existing through vias at (47.9,17.15) and (48.9,16.8) now join only Top and
   Bottom: the signal comes up from R133/R134 on the Bottom and leaves on the Top, so it uses the full barrel. The
   simulation models them as connected.
9. **D13 is longer.** Its route grows by about 6.6 mm and its new U3-side path is Top microstrip. Its read delay
   (+0.083..+0.097 ns) is the largest on the bus but well inside the budget in §3.
10. **Read timing.** It cannot be closed without an SDRAM controller. Direct capture already fails without the
   resistor.
11. **Snapshot.** Everything is based on PcbDoc md5 2a616c1c and `dq_series_r_plan.json` md5 7c2b8ae6 (16
   resistors; the 13-resistor plan is `dq_series_r_plan_13.json`, md5 f2949630). Unsaved edits in Altium invalidate
   the plan until gate 0 is re-run. Re-running `plan_export.py` on its own overwrites the plan with the 12-resistor
   one; follow the order in gate 0.

