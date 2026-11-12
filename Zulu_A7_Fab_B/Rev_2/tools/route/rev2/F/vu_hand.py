"""vu_hand.py <out_step.json> [vu_width]
Strategy F hand step around the moved X4 (LiPo JST, 2.54 mm west): VU keeps Rev 1's weave through X4 (south of
MP1, north through the MP1 / pad 1 gap, east above pads 1-2, south through the pad 2 / MP2 gap, east under MP2 to
the kept trunk at 34.45,3.4), shifted 2.54 mm west, at 0.6 mm (Rev 1: 0.7; the pinch under MP1's SW corner leaves
0.62). To clear its way:
  * VBATT's west run drops from y 3.0 to 2.8 before x 24.5 (0.4 mm, as Rev 1's west run) and joins its 0.6 run at
    26.5,2.5 (VU passes above it under MP1);
  * the VCC3V3 through via at 27.93,4.85 (Bottom decap hub + U2.20 tie, now in the MP1 / pad 1 gap) becomes an
    L5>Bottom microvia at the same spot, and its Top stub to U2.20 goes; U2.20 stays joined to U2.31 on Top along
    y 6.9625 (0.0762 over MP2, which the old 0.145 track cleared by exactly 0.09) and gets a new plane tie from
    the router;
  * TDI's Top hop at x 32.2 (L3 > Top at 32.2,5.7 > Top down to 4.3 > L3 at 32.6,4.0, in the pad 2 / MP2 gap)
    is removed: TDI rejoins its L3 run by router on L3;
  * the old X4.2 GND Top stub (32.55,2.25)-(33.4,3.05) is removed (dead, in VU's way)."""
import json
import sys

out = sys.argv[1]
W = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
h = 0.3
VU = [(24.81, 4.949), (24.81, 3.7), (24.81 + h, 3.4), (27.81 - h, 3.4), (27.81, 3.4 + h), (27.81, 6.3 - h),
      (27.81 + h, 6.3), (31.91 - h, 6.3), (31.91, 6.3 - h), (31.91, 3.4 + h), (31.91 + h, 3.4), (34.45, 3.4)]


def tr(net, pts, w, layer='Top Layer'):
    return [{'net': net, 'layer': layer, 'w': w, 'x1': a[0], 'y1': a[1], 'x2': b[0], 'y2': b[1]}
            for a, b in zip(pts, pts[1:])]


def T(net, x1, y1, x2, y2, w, layer='Top Layer'):
    return {'net': net, 'layer': layer, 'w': w, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}


step = {
    'remove': [T('VBATT', 17.075, 3.0, 25.5, 3.0, 0.4), T('VBATT', 25.5, 3.0, 26.5, 2.5, 0.6),
               T('TDI', 32.2, 4.3, 32.2, 5.7, 0.0762), T('TDI', 32.2, 4.3, 32.3219, 4.2085, 0.0762),
               T('GND', 32.55, 2.25, 33.4, 3.0501, 0.5),
               T('VCC3V3', 27.93, 6.9625, 29.2251, 6.9625, 0.145), T('VCC3V3', 27.93, 6.5, 27.93, 6.9625, 0.145),
               T('VCC3V3', 27.93, 4.85, 27.93, 6.5, 0.3),
               T('VCC3V3', 29.2251, 6.9625, 32.4022, 6.9625, 0.145), T('VCC3V3', 34.1178, 6.9625, 34.7249, 6.9625, 0.145)],
    'remove_vias': [{'net': 'TDI', 'x': 32.2, 'y': 5.7, 'size': 0.3, 'hole': 0.15, 'from': 'Top Layer', 'to': 'L2-GND'},
                    {'net': 'TDI', 'x': 32.2, 'y': 5.7, 'size': 0.3, 'hole': 0.15, 'from': 'L2-GND', 'to': 'L3-SIG'},
                    {'net': 'VCC3V3', 'x': 27.93, 'y': 4.85, 'size': 0.35, 'hole': 0.2, 'from': 'Top Layer', 'to': 'Bottom Layer'}],
    'tracks': tr('VU', VU, W) +
              tr('VBATT', [(17.075, 3.0), (24.3, 3.0), (24.5, 2.8), (26.2, 2.8), (26.5, 2.5)], 0.4) +
              [T('VCC3V3', 29.2251, 6.9625, 32.3, 6.9625, 0.145), T('VCC3V3', 32.3, 6.9625, 34.2, 6.9625, 0.0762),
               T('VCC3V3', 34.2, 6.9625, 34.7249, 6.9625, 0.145)],
    'vias': [{'net': 'VCC3V3', 'x': 27.93, 'y': 4.85, 'size': 0.3, 'hole': 0.15, 'from': 'L5-VCC3V3', 'to': 'Bottom Layer'}],
}
json.dump(step, open(out, 'w'), indent=0)
print('VU %d tracks at %.2f' % (len(VU) - 1, W))
