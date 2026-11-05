# PCBWay enquiry -- laser microvia-in-pad on U1, ring scheme, 3/3 mil (final counts 2026-11-05; the user sends it)

History: first draft 2026-10-31 (all-signals-to-L3 scheme), question on 3/3 mil added 2026-11-04. Rewritten 2026-11-05
for the layer-per-ring fan-out and checked by three readers against the files; that version used counts from partial
plans. THIS version carries the counts of the board as placed (stage 7, DRC 0: 1487 vias, 4724 tracks, md5 1162f2f9).
What the checks changed against the earlier drafts:
- no "we could go to 0.275 mm lands": at 0.275 a 3 mil track between two balls has 0.0744 mm a side
- PCBWay's CAM for W1150632AS3P6 lasered our 0.15 vias at 0.127 mm, drilled most buried vias with a 0.20 tool and most
  through vias with 0.25, and enlarged the lands (working file ca45692c06a0.*). No room for that at 3 mil -> question 4
- item D / question 8: the Zulu order had via-in-pad only at BTN; here 113 through vias and ~265 lasers sit in pads
- stack figures are from PCBWay's approved file of 2026-10-27 (0.1016, not 0.1015); the reference order was 0.0762
  track / 0.09 gap, 69.85 x 25.40 mm, 0.225 lands; drl2-5 was confirmed a CAM helper (EQ 2026-10-27 item 1)
- plane strip MEASURED on the saved repoured polygons: 65 of the orthogonal U1 webs on L2 are 0.085-0.09 mm, not the
  ideal-circle 0.098 (Altium's antipads are 16-gons); 18 + 29 webs on L2 + L5 are under 0.0762 mm
The text between the rules is what goes to PCBWay, as plain text.

---

Subject: New board in the W1150632AS3P6 family: 0.10 mm laser via-in-pad under a 0.5 mm BGA and 3/3 mil - questions before release

Hello,

We are finishing the layout of a second, smaller board (50.8 x 22.86 mm) in the same family as our order W1150632AS3P6 (Zulu_A7_HDI_Optimized). Before we release it we need your confirmation on the points that go beyond that order.

Same as the data of W1150632AS3P6:
- 6 layers, 1.6 mm, ENIG
- 2-step HDI: stacked laser vias Top-L2-L3 and L4-L5-Bottom, mechanical buried via L3-L4 (0.15 mm hole / 0.27 mm land), through via 0.20 mm hole / 0.35 mm land
- Standard laser via 0.15 mm hole / 0.30 mm land
- Stack: the one you proposed and we approved for W1150632AS3P6 (your stackup file of 2026-10-27): 3313 PP 0.1016 mm (Top-L2 and L5-Bottom), 1080 PP 0.071 mm (L2-L3 and L4-L5), 0.5 oz inner copper, outer layers plated to 1 oz
(Top = L1, Bottom = L6.)

New on this board:

A. Laser via-in-pad under the FPGA (XC7A35T-CPG236: 0.5 mm pitch, 238 balls, 0.25 mm lands; the lands were 0.225 mm on W1150632AS3P6). A laser via of 0.10 mm hole / 0.25 mm land sits at the centre of the ball land, copper-filled and capped flat (like the via-in-pad at BTN on W1150632AS3P6):
- 68 GND balls: Top-L2
- 27 balls: Top-L2 + L2-L3, stacked
- 26 balls: Top-L2 + L2-L3, stacked on a buried via L3-L4 (0.15 / 0.27)
- 28 balls (3.3 V): Top-L2 + L2-L3 + buried L3-L4 + L4-L5, one column
- 89 balls have no centred via; on 9 of them (outer rows) a via overlaps the land off-centre: 8 laser vias and 1 through via (ball W8)
In total 258 laser vias of 0.10 / 0.25 in BGA lands (149 Top-L2, 81 L2-L3, 28 L4-L5) and 54 buried vias under them.

B. 89 more laser vias of 0.10 / 0.25 that are not centred on a ball land (on Top-L2, L2-L3, L4-L5 and L5-Bottom), 43 of them under the FPGA, where a 0.30 mm land does not fit. All other laser vias (748) stay 0.15 / 0.30. The board also has 225 buried vias and 167 through vias.

C. Clearance 0.0762 mm (3 mil) on all layers. The track stays 0.0762 mm; W1150632AS3P6 was 0.0762 mm track / 0.09 mm clearance.

D. Via-in-pad on other parts: about 265 laser vias (252 of them 0.15 / 0.30) sit in SMD pads, copper-filled and flat. 113 through vias (0.20 / 0.35) also sit in or on the edge of SMD pads, including ball W8 of the FPGA and balls G9 and H2 of the SDRAM (0.8 mm pitch, 0.40 mm lands). We would like these through vias resin-plugged and plated over.

Questions:

1. Via-in-pad: is a 0.10 mm laser via in a 0.25 mm land (0.075 mm ring) acceptable at 0.5 mm pitch, both in the BGA land on Top and on the inner lands (L2 to L5), copper-filled and capped so that the ball solders on a flat land? The land cannot grow: above 0.27 mm a 3 mil track no longer fits between two balls. If you need a bigger ring, what is your minimum?

2. Laser hole: on the W1150632AS3P6 stack the 0.10 mm hole goes through 0.1016 mm (Top-L2, L5-Bottom) and 0.071 mm (L2-L3, L4-L5). Your working file for that order lasered our 0.15 mm vias at 0.127 mm. Will you laser 0.10 mm here? If you would use 0.127 mm, is the 0.25 mm land (0.0615 mm ring) still acceptable? If 0.1016 mm is too thick for a 0.10 mm hole, please propose a thinner outer prepreg.

3. Stacking: W1150632AS3P6 has 27 columns L2-L3 + buried L3-L4 + L4-L5, and you confirmed there that the L2-L5 holes in your stackup drawing were CAM helpers only. Please confirm the same construction with 0.10 mm holes and 0.25 mm lands, with no mechanical L2-L5 drill: (a) 0.10 mm laser vias stacked Top-L2-L3, (b) a 0.10 mm laser via directly on the 0.15 mm buried via, (c) the full column Top-L2 + L2-L3 + buried L3-L4 + L4-L5, (d) in 4 places the same column continued to Bottom with an L5-Bottom laser, with 0.10 mm and 0.15 mm lasers mixed.

4. Mechanical vias: on W1150632AS3P6 your working file drilled most of our 0.15 mm buried vias with a 0.20 mm tool and most of our 0.20 mm through vias with a 0.25 mm tool, and enlarged their lands. On this board there is no room for that: tracks pass 0.0762 mm from the drawn 0.27 mm and 0.35 mm lands, and 54 buried vias sit under BGA balls at 0.5 mm pitch. Can you build the buried via as drawn (0.15 mm in a 0.27 mm land) and the through via as drawn (0.20 mm in a 0.35 mm land), without enlarging the lands? If not, what are your minimum tool and land for each?

5. Spacing: your minimum hole-edge to hole-edge distance (laser to laser, laser to buried or through hole). Adjacent BGA balls give 0.40 mm; our smallest distance between two holes that meet on a common layer is 0.24 mm, as on W1150632AS3P6. Your minimum from a hole wall to copper of another net: we have 0.15 mm from a laser hole to the L2 / L5 plane copper, 0.136 mm from a buried via and 0.151 mm from a through via. And your minimum from a non-plated hole to copper: we have 0.086 mm to a track and 0.076 mm to the plane pour.

6. Plane copper between clearance holes: between two adjacent via-in-pad balls the L2 ground plane keeps a copper strip about 0.09 mm wide. Can you hold that, or should we remove these strips? In about 45 other places on L2 and L5 a strip is narrower than 0.0762 mm. No connection depends on any of these, so you may clear any strip below your minimum.

7. 3/3 mil: can you hold 0.0762 mm track and gap on all six layers at the copper weights of that stack, including (a) one 3 mil track between two 0.25 mm BGA lands at 0.5 mm pitch on Top (0.082 to 0.087 mm from track to land; the solder mask opening on these lands is drawn 1:1 - can you keep the track under mask?) and (b) 3 mil gaps from tracks to laser via lands on L3 / L4? If any layer needs thinner copper for 3/3 mil, please say which.

8. Through vias in pads (item D): can you resin-plug and plate over the 0.20 mm through vias in SMD pads, including the BGA lands? Does it change your minimum hole or land?

9. Any DFM concern with 149 filled laser vias in the lands of one 0.5 mm BGA, plus about 30 more between or overlapping the lands (planarity, dimple depth)?

10. Price difference against W1150632AS3P6 for 5 and 10 pieces, with and without the plugged through vias, and the lead time.

We will send Gerber and drill files once these points are settled.

Thank you,
Christian

---
