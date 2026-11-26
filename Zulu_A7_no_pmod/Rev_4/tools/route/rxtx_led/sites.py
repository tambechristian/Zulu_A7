"""No-PMOD Rev 4 (2026-11-25): site search for the RX/TX activity LED LD6 (yellow 0603) + its 0201 resistor R136.

    python tools/route/rxtx_led/sites.py

LD6 cathode goes to U2 pins 54 (BCBUS3 RXLED#) and 55 (BCBUS4 TXLED#) at (31.75 / 31.25, 18.975); R136 runs from
VCC3V3 to the anode. Candidates: LD6 at rotation 0 or 90 on a 0.1 mm grid over x 18..46, y 12..25.4 (U2's north edge to the top edge, around X1); R136 beside the anode
(in line with the LED or turned 90). Rules, all on the Top side:
  pads >= 0.15 mm from every other pad (any net) and from every through-hole land, >= 0.30 mm inside the outline;
  bodies >= 0.26 mm from every other Top body (Altium Component Clearance is 0.254);
  pads and bodies clear of every printed Top Overlay text box (+0.10 mm);
  other-net Top tracks / Top vias within 0.09 mm are counted as rips (the router re-routes them).
Score: rips first, then cathode distance to the U2 pins. Prints the 12 best.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLS)
import body_check  # noqa: E402
from board_illustration import read_silk, silk_box  # noqa: E402

PCB = os.path.join(os.path.dirname(TOOLS), 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
TARGET = (31.5, 18.975)


def box_gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0)
    dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)


def pbox(p):
    return (p['x'] - p['w'] / 2, p['y'] - p['h'] / 2, p['x'] + p['w'] / 2, p['y'] + p['h'] / 2)


def seg_box_gap(t, b):
    n = max(2, int(math.hypot(t['x2'] - t['x1'], t['y2'] - t['y1']) / 0.05) + 1)
    return min(box_gap((x, y, x, y), b) for x, y in
               ((t['x1'] + (t['x2'] - t['x1']) * i / (n - 1), t['y1'] + (t['y2'] - t['y1']) * i / (n - 1)) for i in range(n)))


def main():
    M = json.load(open(os.path.join(TOOLS, 'route', 'illustration', 'base.json')))
    W, H = M['board']['w'], M['board']['h']
    P = body_check.load(os.path.join(TOOLS, 'route', 'illustration', 'base.json'))['Top']
    top_pads = [pbox(p) for p in M['pads'] if p['drill'] or 'Top Layer' in p['layers']]
    bodies = [b for d in P.values() for b in d['body']]
    silk = []
    for t in read_silk(PCB, 33):
        x0, x1, y0, y1 = silk_box(t)
        silk.append((x0, y0, x1, y1))
    tracks = [t for t in M['tracks'] if t['layer'] == 'Top Layer']
    vias = [v for v in M['vias'] if 'Top Layer' in v['span']]
    # region of interest (around U2's north edge and X1) and obstacle pre-filter
    RX0, RX1, RY0, RY1 = 18.0, 46.0, 12.0, 25.4
    near = lambda b: b[2] > RX0 - 2 and b[0] < RX1 + 2 and b[3] > RY0 - 2 and b[1] < RY1 + 2   # noqa: E731
    top_pads = [b for b in top_pads if near(b)]
    bodies = [b for b in bodies if near(b)]
    silk = [b for b in silk if near(b)]
    tracks = [t for t in tracks if near((min(t['x1'], t['x2']), min(t['y1'], t['y2']), max(t['x1'], t['x2']), max(t['y1'], t['y2'])))]
    vias = [v for v in vias if near((v['x'], v['y'], v['x'], v['y']))]

    def ok(pads, body):
        for b in pads:
            if b[0] < 0.3 or b[1] < 0.3 or b[2] > W - 0.3 or b[3] > H - 0.3:
                return False
            if any(box_gap(b, o) < 0.15 for o in top_pads):
                return False
            if any(box_gap(b, s) < 0.10 for s in silk):
                return False
        if any(box_gap(body, o) < 0.26 for o in bodies):
            return False
        if any(box_gap(body, s) < 0.10 for s in silk):
            return False
        return True

    def rips(pads):
        n = sum(1 for t in tracks if any(seg_box_gap(t, b) < t['w'] / 2 + 0.09 for b in pads))
        n += sum(1 for v in vias if any(box_gap((v['x'], v['y'], v['x'], v['y']), b) < v['size'] / 2 + 0.09 for b in pads))
        return n
    out = []
    for ix in range(int(RX0 / 0.1), int(RX1 / 0.1)):
        for iy in range(int(RY0 / 0.1), int(RY1 / 0.1)):
            cx, cy = ix * 0.1, iy * 0.1
            for rot in (0, 90):
                if rot == 0:
                    a, k = (cx - 0.8, cy), (cx + 0.8, cy)
                    led = [(a[0] - .45, a[1] - .45, a[0] + .45, a[1] + .45), (k[0] - .45, k[1] - .45, k[0] + .45, k[1] + .45)]
                    lbody = (cx - 0.8, cy - 0.4, cx + 0.8, cy + 0.4)
                else:
                    a, k = (cx, cy - 0.8), (cx, cy + 0.8)
                    led = [(a[0] - .45, a[1] - .45, a[0] + .45, a[1] + .45), (k[0] - .45, k[1] - .45, k[0] + .45, k[1] + .45)]
                    lbody = (cx - 0.4, cy - 0.8, cx + 0.4, cy + 0.8)
                if not ok(led, lbody):
                    continue
                # R136 beside the anode: 4 orientations, pad 2 (anode side) 0.55 mm beyond the anode pad edge
                for dx, dy, rrot in ((-1, 0, 0), (1, 0, 0), (0, -1, 90), (0, 1, 90)):
                    if rot == 0 and dx == 1 or rot == 90 and dy == 1:
                        continue                       # that side is the cathode
                    p2 = (a[0] + dx * 1.05, a[1] + dy * 1.05)
                    p1 = (p2[0] + dx * 0.6, p2[1] + dy * 0.6) if (dx, dy) in ((-1, 0), (0, -1)) else None
                    if p1 is None:
                        continue
                    rp = [(q[0] - .15, q[1] - .15, q[0] + .15, q[1] + .15) for q in (p1, p2)]
                    rbody = (min(p1[0], p2[0]) - .15, min(p1[1], p2[1]) - .15, max(p1[0], p2[0]) + .15, max(p1[1], p2[1]) + .15)
                    if not ok(rp, rbody) or box_gap(rbody, lbody) < 0.26:
                        continue
                    d = math.hypot(k[0] - TARGET[0], k[1] - TARGET[1])
                    out.append((rips(led + rp), round(d, 2), cx, cy, rot, p1, p2))
    out.sort()
    seen = []
    for o in out:
        if any(math.hypot(o[2] - s[2], o[3] - s[3]) < 1.0 for s in seen):
            continue
        seen.append(o)
        print('rips %2d  cathode-to-U2 %5.2f mm  LD6 centre (%.2f, %.2f) rot %d  R136 pads 1 (%.2f, %.2f) 2 (%.2f, %.2f)' % (
            o[0], o[1], o[2], o[3], o[4], o[5][0], o[5][1], o[6][0], o[6][1]))
        if len(seen) >= 12:
            break
    json.dump([dict(rips=o[0], dist=o[1], cx=o[2], cy=o[3], rot=o[4], r1=o[5], r2=o[6]) for o in seen],
              open(os.path.join(HERE, 'sites.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
