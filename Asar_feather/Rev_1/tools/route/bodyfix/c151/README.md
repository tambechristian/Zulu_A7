# Body fix "c151": C151 off U8's body corner (Asar A7 Feather, board md5 c4bf0b71)

**Problem.** C151 is U8's VBATT (BAT, pin 23) bypass cap: 4.7 uF 0603 on the Bottom, rot 180. Its pad 2 sat 0.15 mm
under the nominal body of U8 (LTC3556 QFN 4x5, body x 8.5..12.5, y 14.8..19.8). body_check reported
`body_pad U8 C151 2 -0.150`. Against U8's maximum-tolerance body the overlap was 0.200 mm.

**Why east is the only direction.** C151 cannot move north or south. Below it, L8-2 (gap 0.21) and C147-2 (VU, gap
0.2001) sit at the 0.2 mm pad gap that leaves a 0.1 mm mask web. Above it, C82 (gap 0.2000) does the same. To clear the
body corner, pad 2's west edge has to reach at least x 12.65, so C151 must move east by at least 0.45 mm. The VU
through via at (15.55, 14.225) then sits inside pad 1. That via joins the L8/C147 VOUT copper on the Bottom to the Top
VU feed for VIN1, VIN2 and VIN3, and it limits an eastward move to 0.285 mm.

I scanned the area for a legal 0.35/0.20 through-via site (`work/vmap.py`: 0.09 mm on every layer and 0.24 mm
hole-to-hole). Every site outside a pad is blocked: by Q1 on the Top, by L4 USB5V0, by the L3/L4 PWR_FB2 via, and by C93
and the VCC1V8 lasers on the Bottom. The legal sites are all inside the VU pads (L8-2 or C147-2). This board already
uses through vias in SMD pads as standard practice: 108 of them, to be resin-plugged and capped (PCBWay Q8/Q10).

## Change (`build.py` writes `plan.json` and `model_final.json`)

| | Item |
|---|---|
| move | C151 dx +0.50, dy 0, rotation unchanged (180). Pad 2 VBATT goes from (12.7502, 14.45) to (13.2502, 14.45). Pad 1 GND goes from (14.45, 14.45) to (14.95, 14.45). |
| remove | The VU through via 0.35/0.20 at (15.55, 14.225) |
| remove | The VU Bottom 0.4 track (15.2, 13.5)-(15.55, 14.225) and the VU Bottom 0.4 stub (15.525, 14.225)-(15.55, 14.225) |
| remove | The VU Top 0.4 track (14.475, 14.55)-(15.55, 14.225) |
| add | A VU through via 0.35/0.20 at (14.60, 13.45). Its hole and land lie entirely inside C147-2 (VU). |
| add | A VU Top 0.4 track (14.60, 13.45)-(14.475, 14.55), joining the existing Top VU spine (14.475, 14.55)-(14.475, 17.5) |
| add | A VBATT Bottom 0.4 track (12.75, 14.9)-(13.2502, 14.45) |

About the VBATT track: the U8-23 track ends 0.05 mm inside the moved pad 2, which would leave a junction of about
0.35 mm. The new track restores a full 0.4 mm connection into the pad centre.

The GND L2..Bottom stack at (14.75, 14.6) stays inside the moved pad 1, which now spans x 14.40..15.50.

The VOUT current path gets shorter. It used to run C147-2, then a 0.4 mm Bottom track, the via, and a 0.4 mm Top track.
It now runs C147-2, the via in the pad, and a 0.4 mm Top track. C151 pad 2 is 1.57 mm (centre to centre) from U8-23;
it was 1.10 mm.

## Gates (run from Rev_1/tools on the scratch files; nothing was written in Rev_1)

| Gate | Result |
|---|---|
| body_check, final model | 40 findings, against 41 at baseline. The only difference is that `U8 C151 2 -0.150` is gone. Nothing is new. `--refs C151,U8` gives 0 findings. C151-2 is 0.200 mm from U8's nominal body and 0.150 mm from its maximum body; the two bodies are 0.80 mm apart. The 40 findings left are the baseline X2 bottom-header and 0201-row items (-0.020/-0.035), U7/L3 0.025 and X2/C101,C102,C139 0.040, which other fixes cover. |
| route_check plan.json model1.json | 0 violations, 0 open connections, PASS |
| hole_gate | PASS, 0 pairs, both for the plan against model1 and for an empty plan against model_final. hole_gate needs from/to keys on vias, so it was given copies with span converted to from/to (`work/*_ft.json`). |
| pad_gate model_final.json C151 | PASS, 0 under. The smallest gaps are 0.2000 (web 0.1000) to C82-1 and C82-2, and 0.2001 to C147-2. These are the same gaps as on today's board. |
| moved pads vs other-net tracks and vias | Smallest gap 0.125 mm, against the 0.09 mm rule (GND via at 13.075, 15.25; VCC1V8 via at 15.675, 15.175 is 0.135) |
| route_conn / `work/dangle.py` | 0 open. VU, VBATT and GND each stay a single component, with 0 pad-less islands, 0 dangling ends and 0 lone vias before and after. |
| widths | Every new or replaced track is 0.4 mm, the same as the removed VU tracks and the VBATT track. The via is the same 0.35/0.20 through via. |
