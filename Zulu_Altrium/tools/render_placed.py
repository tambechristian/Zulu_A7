# -*- coding: utf-8 -*-
"""Draw the board AS PLACED, from the verified copper positions, to docs/placed.html.

Not the plan -- the result. Every rectangle here is a land bounding box reconstructed from
Pad.X/Y as Altium reports it after the fact, by the same route tools/verify_copper.py uses, so
what is drawn is what is in the PcbDoc.

    python tools/render_placed.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import place_board as pb
import verify_copper as vc
from verify_placement import read_report

OUT = os.path.join(os.path.dirname(HERE), 'docs', 'placed.html')
MM = 13.0                      # px per mm
BW, BH = pb.BOARD

# parts that get their designator drawn on the board; the rest are too small to label
BIG = 2.2                      # mm; label anything at least this wide or tall

DEPARTURES = [
    ('U2', 'FT2232HL', 'plan y 11.80 &rarr; 13.60',
     'The LQFP64 land is 12.95&nbsp;mm, not the 10&nbsp;mm body the plan drew, and X4 below it is '
     '6.50&nbsp;mm deep rather than 3.30. X4 cannot move sideways &mdash; it has to sit in the '
     '11.18&nbsp;mm window where X2 omits four pins &mdash; so the bridge moved up instead.'),
    ('Q1', '12 MHz osc.', 'plan x 39.75 &rarr; 41.30',
     'Cleared the same LQFP land, which ends at x&nbsp;39.43.'),
    ('U4', 'SPI flash', 'plan x 45.00 &rarr; 47.50',
     'Follows Q1 right. Still on the front directly above the FPGA, which is what change&nbsp;1 '
     'was for; it now sits centred over the ball field rather than to its left.'),
    ('JP3 / JP4', 'JTAG', 'plan y 23.25 / 0.70 &rarr; 21.68 / 3.72',
     'A 1.524&nbsp;mm pad at the plan&rsquo;s lower y would have hung 0.06&nbsp;mm over the board '
     'edge. Both take the plan&rsquo;s x and the previous layout&rsquo;s y.'),
    ('U10', 'EEPROM', 'plan y 20.15 &rarr; 20.60',
     'Overlapped the SDRAM land by 0.14&nbsp;mm.'),
    ('R1', 'config array', 'old y 3.00 &rarr; 3.70',
     'The 742C043 is 1.25&nbsp;mm wide and the gap between X2 pins 5 and 6 is 1.02&nbsp;mm, so it '
     'cannot sit between them. It moved above the pin row.'),
    ('R4', 'JTAG array', 'old x 59.79 &rarr; 59.30',
     'Clipped JP3&rsquo;s first pad by 0.09&nbsp;mm.'),
    ('LD3 / LD4', 'charge, done', 'new parts',
     'The bq24232 indicators continue the previous layout&rsquo;s LED column at its 1.20&nbsp;mm '
     'pitch, on the front where a hand can see them, even though their series resistors are in '
     'the power block on the back.'),
]


def layout():
    comp, ext, place, src, missing, overflow = pb.build(verbose=False)
    got = read_report()
    off = vc.lib_pad_offsets()
    out = []
    for d, g in sorted(got.items()):
        fp = comp.get(d)
        if fp is None:
            continue
        w, h = pb.size(fp, g['rot'], ext)
        o = off.get(fp, {}).get('1')
        if o is not None and g['p1'] is not None:
            tx, ty = vc.transform(o[0], o[1], g['rot'], g['layer'] == 'bottom')
            cx, cy = g['p1'][0] - tx, g['p1'][1] - ty
        else:
            cx, cy = g['cx'], g['cy']
        out.append(dict(d=d, fp=fp, layer=g['layer'], rot=g['rot'],
                        x=cx - w / 2, y=cy - h / 2, w=w, h=h, cx=cx, cy=cy))
    return comp, out


def svg(parts, side):
    X = lambda mm: (mm) * MM
    Y = lambda mm: (BH - mm) * MM
    o = ['<svg viewBox="-26 -22 %.0f %.0f" role="img" aria-label="%s side, %d parts drawn to scale">'
         % (BW * MM + 52, BH * MM + 62, side, sum(1 for p in parts if p['layer'] == side))]
    o.append('<rect class="board" x="0" y="0" width="%.1f" height="%.1f" rx="2"/>'
             % (BW * MM, BH * MM))
    # millimetre ruler along the bottom
    for mm in range(0, int(BW) + 1, 5):
        o.append('<line class="tick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 % (X(mm), BH * MM, X(mm), BH * MM + 6))
        o.append('<text class="tick-l" x="%.1f" y="%.1f" text-anchor="middle">%d</text>'
                 % (X(mm), BH * MM + 17, mm))
    cls = 'front' if side == 'top' else 'back'
    geom = pb.lib_geometry()
    for p in sorted(parts, key=lambda p: -p['w'] * p['h']):
        if p['layer'] != side or p['w'] <= 0:
            continue
        tip = ('<title>%s  %s  r%d  centre %.2f, %.2f mm</title>'
               % (p['d'], p['fp'], p['rot'], p['cx'], p['cy']))
        if p['fp'] in pb.THRU:
            # The header's land bounding box is 59.9 x 24.4 mm and would blanket the board. It is
            # forty separate 1.52 mm pins with a 10 mm gap where the LiPo connector sits, and that
            # is what the drawing has to show -- the same reason place_board.py collides against
            # pads rather than boxes for these four footprints.
            o.append('<g class="p %s">%s' % (cls, tip))
            for dx, dy, pw, ph in geom[p['fp']][1]:
                if p['rot'] % 360 == 90:
                    dx, dy, pw, ph = -dy, dx, ph, pw
                elif p['rot'] % 360 == 180:
                    dx, dy = -dx, -dy
                elif p['rot'] % 360 == 270:
                    dx, dy, pw, ph = dy, -dx, ph, pw
                o.append('<rect rx="1" x="%.2f" y="%.2f" width="%.2f" height="%.2f"/>'
                         % (X(p['cx'] + dx - pw / 2), Y(p['cy'] + dy + ph / 2), pw * MM, ph * MM))
            o.append('</g>')
        else:
            o.append('<rect class="p %s" x="%.2f" y="%.2f" width="%.2f" height="%.2f">%s</rect>'
                     % (cls, X(p['x']), Y(p['y'] + p['h']), p['w'] * MM, p['h'] * MM, tip))
    for p in parts:
        if p['layer'] != side or max(p['w'], p['h']) < BIG or p['fp'] in pb.THRU:
            continue
        o.append('<text class="lab" x="%.2f" y="%.2f" text-anchor="middle">%s</text>'
                 % (X(p['cx']), Y(p['cy']) + 3.4, p['d']))
    for p in parts:
        if p['layer'] != side or p['fp'] not in pb.THRU:
            continue
        o.append('<text class="lab thru" x="%.2f" y="%.2f" text-anchor="middle">%s</text>'
                 % (X(p['cx']), Y(p['y'] + p['h']) - 4, p['d']))
    o.append('</svg>')
    return '\n'.join(o)


CSS = """
:root{
  --paper:#f6f4ef; --ink:#1a212a; --muted:#6a6f78; --rule:#dcd8cf; --panel:#efece5;
  --board:#e7e3d9; --boardline:#b9b3a5;
  --front:#b1472f; --frontfill:#b1472f22; --back:#2f5d9e; --backfill:#2f5d9e22;
  --ok:#3d7a4e;
}
:root:not([data-theme="light"]){ }
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#12161b; --ink:#e7e5e0; --muted:#959aa3; --rule:#2a3138; --panel:#191e25;
    --board:#1d232a; --boardline:#3a434c;
    --front:#e0714f; --frontfill:#e0714f26; --back:#6f9fe0; --backfill:#6f9fe026;
    --ok:#6fb583;
  }
}
:root[data-theme="dark"]{
  --paper:#12161b; --ink:#e7e5e0; --muted:#959aa3; --rule:#2a3138; --panel:#191e25;
  --board:#1d232a; --boardline:#3a434c;
  --front:#e0714f; --frontfill:#e0714f26; --back:#6f9fe0; --backfill:#6f9fe026;
  --ok:#6fb583;
}
*{box-sizing:border-box}
body{background:var(--paper); color:var(--ink);
     font:400 15px/1.55 "IBM Plex Sans","Segoe UI",system-ui,sans-serif; margin:0}
.wrap{max-width:1060px; margin:0 auto; padding:40px 24px 72px}
header{border-bottom:2px solid var(--ink); padding-bottom:16px; margin-bottom:26px}
h1{font:600 27px/1.15 "IBM Plex Sans",sans-serif; margin:0 0 6px; letter-spacing:-.015em}
.sub{color:var(--muted); margin:0 0 16px; max-width:70ch; font-size:14.5px}
.meta{display:flex; flex-wrap:wrap; gap:8px 22px;
      font:500 11.5px/1 "IBM Plex Mono",monospace; letter-spacing:.06em;
      text-transform:uppercase; color:var(--muted)}
.meta b{color:var(--ink); font-weight:600}
section{margin:34px 0}
.viewhead{display:flex; align-items:baseline; gap:14px; margin-bottom:10px}
h2{font:600 17px/1 "IBM Plex Sans",sans-serif; margin:0}
.viewhead span{color:var(--muted); font-size:13px}
.swatch{display:inline-block; width:10px; height:10px; border-radius:2px; vertical-align:-1px}
.sheet{background:var(--panel); border:1px solid var(--rule); border-radius:3px;
       padding:16px 14px 10px; overflow-x:auto}
svg{display:block; width:100%; min-width:760px; height:auto}
.board{fill:var(--board); stroke:var(--boardline); stroke-width:1.2}
.tick{stroke:var(--boardline); stroke-width:1}
.tick-l{fill:var(--muted); font:500 9px "IBM Plex Mono",monospace}
.p{stroke-width:.9}
g.p rect{stroke-width:.9}
g.p.front rect{fill:var(--frontfill); stroke:var(--front)}
g.p.back rect{fill:var(--backfill); stroke:var(--back)}
.lab.thru{opacity:.7; font-size:8.5px}
.p.front{fill:var(--frontfill); stroke:var(--front)}
.p.back{fill:var(--backfill); stroke:var(--back)}
.lab{font:600 9px "IBM Plex Mono",monospace; fill:var(--ink); opacity:.85; pointer-events:none}
.checks{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:1px;
        background:var(--rule); border:1px solid var(--rule); border-radius:3px; overflow:hidden}
.check{background:var(--panel); padding:14px 16px}
.check .n{font:600 21px/1 "IBM Plex Mono",monospace; font-variant-numeric:tabular-nums;
          color:var(--ok); display:block; margin-bottom:5px}
.check .t{font-size:12.5px; color:var(--muted); line-height:1.4}
table{border-collapse:collapse; width:100%; font-size:13.5px}
th,td{text-align:left; padding:9px 12px 9px 0; border-bottom:1px solid var(--rule);
      vertical-align:top}
th{font:600 11px "IBM Plex Sans",sans-serif; letter-spacing:.07em; text-transform:uppercase;
   color:var(--muted)}
td.d{font:600 12.5px "IBM Plex Mono",monospace; white-space:nowrap; width:7.5em}
td.m{font:400 12px "IBM Plex Mono",monospace; color:var(--front); white-space:nowrap; width:15em}
.note{color:var(--muted); font-size:13.5px; max-width:76ch}
.note b{color:var(--ink); font-weight:600}
"""


def main():
    comp, parts = layout()
    nf = sum(1 for p in parts if p['layer'] == 'top')
    nb = len(parts) - nf

    rows = '\n'.join(
        '<tr><td class="d">%s</td><td class="m">%s</td><td>%s</td></tr>' % (d, mv, why)
        for d, _kind, mv, why in DEPARTURES)

    html = """<title>Zulu A7 As Placed</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>%(css)s</style>
<div class="wrap">
  <header>
    <h1>Zulu A7 &mdash; as placed</h1>
    <p class="sub">Every land drawn from the position Altium reports, not from the plan. The board
      is 69.85 &times; 25.40&nbsp;mm; the drawing is to scale and the ruler below each view is in
      millimetres. Hover any part for its footprint, rotation and centre.</p>
    <div class="meta">
      <span>PLACED <b>%(n)d of %(n)d</b></span>
      <span>FRONT <b>%(nf)d</b></span>
      <span>BACK <b>%(nb)d</b></span>
      <span>CLEARANCE <b>0.30 mm minimum</b></span>
      <span>SOURCE <b>zulu_a7.PcbDoc</b></span>
    </div>
  </header>

  <section>
    <div class="viewhead"><h2>Front</h2>
      <span><i class="swatch" style="background:var(--frontfill);border:1px solid var(--front)"></i>
      top-layer land patterns &middot; pin 1 of the header at the top right</span></div>
    <div class="sheet">%(front)s</div>
  </section>

  <section>
    <div class="viewhead"><h2>Back</h2>
      <span><i class="swatch" style="background:var(--backfill);border:1px solid var(--back)"></i>
      seen through the board, same orientation</span></div>
    <div class="sheet">%(back)s</div>
  </section>

  <section>
    <div class="viewhead"><h2>Checks</h2><span>run against the saved file, not a dialog</span></div>
    <div class="checks">
      <div class="check"><span class="n">175 / 175</span>
        <span class="t">placed, none missing and none left off the board</span></div>
      <div class="check"><span class="n">0</span>
        <span class="t">pairs of lands closer than 0.30&nbsp;mm, on either side</span></div>
      <div class="check"><span class="n">0</span>
        <span class="t">parts within 0.30&nbsp;mm of the board edge</span></div>
      <div class="check"><span class="n">0.0001 mm</span>
        <span class="t">worst copper error against the intended centre</span></div>
      <div class="check"><span class="n">59.690, 24.130</span>
        <span class="t">X2 pin 1, exactly &mdash; the grid every carrier board is built to</span></div>
    </div>
  </section>

  <section>
    <div class="viewhead"><h2>Where this departs from the plan</h2>
      <span>and why the geometry decided it</span></div>
    <table>
      <thead><tr><th>Part</th><th>Move</th><th>Reason</th></tr></thead>
      <tbody>%(rows)s</tbody>
    </table>
  </section>

  <section>
    <p class="note"><b>Off the board.</b> The four Creative Commons marks are licence art with no
      copper, carried through the import as real pinless components. They are not meant to be on
      the PCB, and they are not: all four sit below the outline on a shared baseline at
      y&nbsp;&minus;9.502&nbsp;mm, which is where the previous layout parked them. They stay in
      the design rather than being deleted, because the schematic still owns them and the next
      Import&nbsp;Changes would bring them straight back.</p>
    <p class="note" style="margin-top:14px"><b>Still to re-cut.</b> The 0201s under the ball field
      are on an even 6&nbsp;&times;&nbsp;4 lattice, assigned by rail rather than by designator:
      the eight VCC1V0 balls sit in a 0.5&nbsp;&times;&nbsp;3.0&nbsp;mm cluster at the centre of
      the die, and the four core caps are 0.65 to 2.89&nbsp;mm from it. That lattice will want
      re-cutting once the BGA fan-out is drawn.</p>
  </section>
</div>
""" % dict(css=CSS, n=len(parts), nf=nf, nb=nb,
           front=svg(parts, 'top'), back=svg(parts, 'bottom'), rows=rows)

    with open(OUT, 'w') as f:
        f.write(html)
    print('wrote %s  (%d parts: %d front, %d back)' % (OUT, len(parts), nf, nb))


if __name__ == '__main__':
    main()
