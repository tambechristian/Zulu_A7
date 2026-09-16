# -*- coding: utf-8 -*-
"""C123 (0201 100 nF) under U1's analog fan-out vias, 2026-09-16.  Writes tools/c123_placement.json
and tools/c123_route.json.

WHY.  UG480 Figure 6-1 Note 1 puts the 100 nF "as close as possible to the package balls" and the 470 nF at
the ferrite bead.  C124 (470 nF) stays at L7; C123 left the bead as an 0201 (tools/c123_to_0201.py) and lands
here, on Bottom, straight under the GNDADC via (46.90, 14.90) and the VCCADC via (47.40, 14.90) that fan out
balls C12 and C13.  Pad to ball is one 0.45 mm Bottom stub, the via barrel and U1's own dog-bone: the loop
measured 2.45 nH / 0.949 mm2 against 26.47 nH / 13.4 mm2 at the bead (planner harness, same Neumann model
as the other two candidates, 4.92 and 5.03 nH, which each needed two new vias outside the land field).

C92 (VCC1V0 0201) moves one slot west along the same y 14.45 row, turned 180 so it mirrors today's mount
about the VCC1V0 via (46.40, 13.90): pad 1 still ties to that via, pad 2 now to the GND via (45.90, 13.90)
instead of (46.90, 13.90).  Its ties stay 0.15 mm, the board's practice for the under-die 0201s.

The three-planner, six-reviewer workflow picked this over the judge's pairdrop once its only failures
(gates 1 and 4) turned out to be block_place testing the moved pads against copper the plan itself removes
-- fixed in block_place.py and route_stitch.py the same day.

    python tools/c123_plan.py      then gate it with --inputs on a model where C123 is already an 0201
                                   (tools/route_inputs.json once the ECO has been saved)

Every coordinate that names existing copper was read from the model, not from prose.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

V_GNDADC_U1 = (46.9000, 14.8999)     # GNDADC fan-out via, Top dog-bone to U1-C12
V_VCCADC_U1 = (47.4001, 14.8999)     # VCCADC fan-out via, Top dog-bone to U1-C13
V_VCC1V0 = (46.4001, 13.8999)        # VCC1V0 via, Top to U1-G10: C92-1's via before and after
V_GND_WEST = (45.9000, 13.8999)      # GND via: C92-2's via after (before: (46.90, 13.90))
V_VCCADC_BEAD = (53.3400, 2.3000)    # VCCADC via at the bead, L3 run to U1 and C124
L7_2 = (52.4503, 3.0500)             # bead output pad
ROW_Y = 14.45                        # the 0201 row between the via rows y 13.90 and 14.90

C123_1 = (47.45, ROW_Y)              # VCCADC, 0.05 east of its via column
C123_2 = (46.85, ROW_Y)              # GNDADC, 0.05 west of its via column
C92_1 = (46.20, ROW_Y)               # VCC1V0, mirror of 46.59 about the via column 46.40
C92_2 = (45.6001, ROW_Y)             # GND, pad pitch 0.5999 kept

placement = {
    'movable': ['C92', 'C123'],
    'moves': [
        # C92 first: C123 lands on C92's old pads
        {'ref': 'C92', 'rot': 180, 'pad': '1', 'x': C92_1[0], 'y': C92_1[1]},
        {'ref': 'C123', 'rot': 180, 'pad': '1', 'x': C123_1[0], 'y': C123_1[1]},
    ],
    'hide_designators': ['C123', 'C92'],
    'roles': {},
}


def T(net, layer, a, b, w):
    return dict(net=net, layer=layer, x1=a[0], y1=a[1], x2=b[0], y2=b[1], width=w)


plan = {
    'vias': [],
    'tracks': [
        T('VCCADC', 'Bottom', C123_1, V_VCCADC_U1, 0.30),
        T('GNDADC', 'Bottom', C123_2, V_GNDADC_U1, 0.30),
        T('VCC1V0', 'Bottom', C92_1, V_VCC1V0, 0.15),
        T('GND', 'Bottom', C92_2, V_GND_WEST, 0.15),
        # L7-2 straight to the bead's VCCADC via (it reached it through C123's old pad centre)
        T('VCCADC', 'Bottom', L7_2, V_VCCADC_BEAD, 0.30),
    ],
    'remove': {
        'vias': [
            {'net': 'GNDADC', 'x': 56.2000, 'y': 4.8000},
        ],
        'tracks': [
            # C92's old ties, ending on its old pad centres where C123 now sits
            T('VCC1V0', 'Bottom', (46.4001, 13.8999), (46.5900, 14.4500), 0.15),
            T('GND', 'Bottom', (46.9000, 13.8999), (47.1899, 14.4500), 0.15),
            # C123-1's stubs at the bead (they met at the old 0402 pad centre 53.5503, 3.05)
            T('VCCADC', 'Bottom', (53.3400, 2.3000), (53.5503, 3.0500), 0.30),
            T('VCCADC', 'Bottom', (52.4503, 3.0500), (53.5503, 3.0500), 0.60),
            # C123-2's Bottom chain to the GNDADC via (56.20, 4.80)
            T('GNDADC', 'Bottom', (54.8503, 3.0500), (55.7500, 3.0500), 0.30),
            T('GNDADC', 'Bottom', (55.7500, 3.0500), (56.2000, 3.5000), 0.30),
            T('GNDADC', 'Bottom', (56.2000, 3.5000), (56.2000, 4.8000), 0.30),
            # the L3 GNDADC tail that only reached that via, first leg off (48.35, 5.00) included
            T('GNDADC', 'L3-SIG', (55.7000, 4.3000), (56.2000, 4.8000), 0.20),
            T('GNDADC', 'L3-SIG', (48.8500, 4.3000), (55.7000, 4.3000), 0.20),
            T('GNDADC', 'L3-SIG', (48.3500, 5.0000), (48.8500, 4.3000), 0.20),
        ],
    },
}


def main():
    io.open(os.path.join(HERE, 'c123_placement.json'), 'w', encoding='utf-8').write(json.dumps(placement, indent=1))
    io.open(os.path.join(HERE, 'c123_route.json'), 'w', encoding='utf-8').write(json.dumps(plan, indent=1))
    print('wrote c123_placement.json (%d moves) and c123_route.json (%d tracks, %d removals)' % (
        len(placement['moves']), len(plan['tracks']), len(plan['remove']['vias']) + len(plan['remove']['tracks'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
