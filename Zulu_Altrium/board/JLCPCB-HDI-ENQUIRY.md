# JLCPCB HDI enquiry — DRAFT 2026-09-29, NOT YET SENT

To: JLCPCB support / HDI engineering. Ref: our 2026-09-14 DFM reply (3 mil allowance, 0.35 via lands).

## The board, in one paragraph

69.85 x 25.40 mm, 6 copper layers, ENIG, impedance control on one USB pair (Top layer over L2). Today it is your
standard stack JLC06161H-3313E, all through-holes 0.20 mm / 0.35 mm. We intend to re-order it as **HDI 2-step** on
your published stack **JLCH061611N2-2116** (L1 0.035 / 2116 0.112 / L2 0.030 / 2116 0.112 / L3 0.030 / core 0.930 /
L4 0.030 / 2116 0.112 / L5 0.030 / 2116 0.112 / L6 0.035 mm), with stacked laser microvias L1-L2 + L2-L3 and L6-L5 +
L5-L4 (copper filled and planarized), 0.15 mm hole / 0.30 mm pad, optionally a mechanical buried via L3-L4 0.15 / 0.27,
through vias 0.20 / 0.35 unchanged, 3 mil line/space. The critical part is a Xilinx XC7A35T-CPG236 (0.5 mm pitch, 238
balls, 0.225 mm lands). Microvias will sit at BGA interstitials and in the vacant moat, not in the pads.

Your online quote for this (qty 5) is $309.34, 12-13 days, with Buried Via Fee and Lamination Fee shown as 'Manual
Quote'. Before we order we need the answers below; several decide the design.

## Questions

1. On JLCH061611N2-2116 ordered as HDI 2-step, confirm the 6L layer pairs: L1-L2 and L2-L3 laser stacked (copper filled and planarized) and L6-L5 / L5-L4 likewise; the surcharge for stacked vs staggered; and whether a microvia stack may sit on an epoxy-filled buried via.

2. Laser hole sizes on the 0.112 mm 2116 outer prepreg: is a 0.12 mm hole (0.93:1, pad 0.27) accepted, or only your 0.10/0.15 defaults -- which discrete sizes do you laser between 0.075 and 0.15? Does the 1:1 aspect rule count the 0.035 mm outer foil (0.147 mm)? Laser hole-size and position tolerance ('not controlled' on the capability page) and layer-to-layer registration.

3. Buried via L3-L4 (0.15 hole, 0.27 pad, 0.930 mm core) on this stack: the Buried Via Fee and Lamination Fee amounts, whether they apply to the N-type named stack, and whether the stack keeps its name with buried vias added.

4. The engineer-generated stack: PRESSED thickness and Dk (state the frequency) of each 2116 sheet (we assume 0.112 / 4.29; your 3313E table used Dk 4.10 and PCBWay quote 4.45 for 2116 -- our USB pair moves 2.4 ohm across that range) and of the 0.930 core; confirm gaps are copper-face to copper-face; 1.58 mm total.

5. Impedance on HDI: your calculator's figure for a 0.150 mm / 0.150 mm Top-layer pair on this stack (we solve 87.8 ohm; 85 at 0.162/0.150; 90 at 0.141/0.150), the solder-mask thickness and Dk you model (1.2 mil / 3.8?), the +-10 % promise without a report, the $33.08 line item (standard stacks were $0), and whether the 3 mil / 0.09 mm BGA fan-out allowance (+20 % tier, your 2026-09-14 reply) still stands on an HDI order with impedance control; fine-line tolerance (+-8-12 %) on HDI outer layers.

6. Is 0.5 oz (0.0152 mm) inner copper honoured on a 6L HDI order, or is 1 oz truly forced? (Our inner power-rail width floors halve at 1 oz.)

7. Plane anti-pads: is a 0.48 mm void around a 0.15/0.30 microvia on an inner plane acceptable (hole edge to plane copper 0.165), and is a plane web narrower than 3 mil between two adjacent voids rejected, or merged by CAM?

8. Hole-edge rules: does 0.24 (different nets) / 0.13 (same net) apply laser-to-mechanical as well (0.15 microvia vs 0.20 through = 0.415 mm centre pitch), and is a same-net trace entering its own via exempt from the 0.15 mm hole-to-trace figure?

9. Does 'BGA pad to trace >= 0.10 mm' apply to a microvia land at an interstitial of the 0.5 mm BGA? A 0.30 mm land clears the 0.225 mm lands by 0.0909 mm (0.27: 0.1059) against our 0.09 mm rule.

10. 'Blind via edge to board edge >= 0.35': hole edge or pad edge; and the through-via-to-edge minimum on an HDI order.

11. Any minimum spacing between two vias whose spans share no layer (a Top-L2 microvia directly over an L5-Bottom microvia at one XY)?

12. Lead time: do the 12-13 days include the stack review round trip; the forced 4-wire Kelvin test; expedite options; the Oct 1-4 holiday effect.

13. (For rev B, not this order) Filled-and-capped microvia inside a 0.225 mm BGA land on a 0.5 mm pitch: 0.10 mm hole (ring 0.0625) or 0.075 mm hole (ring 0.075) -- accepted, on which outer prepreg, at what cost?
