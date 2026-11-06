# -*- coding: utf-8 -*-
"""Synthesise the POST-ECO board: tools/route_inputs.json with C155-C159's ten lands added.

    python eco.py                writes inputs_eco.json

C155-C159 do not exist on the board today, so four of the brief's gates (tie_check, gnd_check,
route_emit's connectivity, capacity) cannot see the five new pads without this file.  It is an
INPUT to those gates, never a board file, and it is written here rather than under tools/.

What is added, and nothing else:
  * ten 0.30 x 0.30 pad records, in top_pads or bottom_pads according to each part's side;
  * the five VCC3V3 lands also into nets['VCC3V3']['pads'], which is how route_inputs.json carries
    a net's own pad list.  GND has NO entry in nets at all on this board (67 nets, GND is not one of
    them -- the plane nets are handled by gnd_check/tie_check from the layer pad lists), so there is
    no GND pad list to keep in step.  Every other top-level key is copied byte for byte.
"""
import io, json, os, sys
import gen

REPO = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium'
HERE = os.path.dirname(os.path.abspath(__file__))


def build(placement=None):
    inp = json.load(io.open(os.path.join(REPO, 'tools', 'route_inputs.json'), encoding='utf-8'))
    assert 'GND' not in inp['nets']
    for c in gen.CAPS:
        p1, p2, v1, v2 = gen.geom(c)
        key = 'top_pads' if c['layer'] == 'Top' else 'bottom_pads'
        # PAD 1 IS GND AND PAD 2 IS VCC3V3 -- see gen.rot_of().  geom() returns the VCC3V3 land
        # first, so the VCC3V3 land is pad 2 and the GND land is pad 1.  The positions and the nets
        # are unchanged from the judge's plan; only the pad numbers differ, and they have to match
        # what the ECO actually delivers or every stub in route.json is on the wrong pad.
        inp[key].append(dict(ref=c['ref'], pad='2', x=p1[0], y=p1[1], sx=0.30, sy=0.30, net='VCC3V3'))
        inp[key].append(dict(ref=c['ref'], pad='1', x=p2[0], y=p2[1], sx=0.30, sy=0.30, net='GND'))
        inp['nets']['VCC3V3']['pads'].append(
            dict(ref=c['ref'], pad='2', layer=c['layer'], x=p1[0], y=p1[1], sx=0.30, sy=0.30))
    return inp


if __name__ == '__main__':
    out = build()
    s = json.dumps(out, indent=1)
    path = os.path.join(HERE, 'inputs_eco.json')
    if '--check' in sys.argv:
        have = io.open(path, encoding='utf-8', newline='').read()
        print('inputs_eco.json  %s' % ('identical' if have == s else 'DIFFERS'))
        sys.exit(0 if have == s else 1)
    io.open(path, 'w', encoding='utf-8', newline='').write(s)
    print('wrote inputs_eco.json: %d top pads, %d bottom pads, VCC3V3 %d pads'
          % (len(out['top_pads']), len(out['bottom_pads']), len(out['nets']['VCC3V3']['pads'])))
