# -*- coding: utf-8 -*-
"""South row (D0-D7) of the series-R plan: R placements + every other copper edit. Imported by design_arrays.py."""
import plan_check as P


def T(layer, net, x1, y1, x2, y2, w=None):
    d = dict(layer=layer, net=net, x1=x1, y1=y1, x2=x2, y2=y2)
    if w is not None:
        d['w'] = w
    return d


def V(net, x, y, kind):
    if kind == 'through':
        return dict(net=net, x=x, y=y, size=0.35, hole=0.20, span=list(P.COPPER), kind='through')
    if kind == 'L5-Bot':
        return dict(net=net, x=x, y=y, size=0.30, hole=0.15, span=['L5-VCC3V3', 'Bottom'], kind='micro')
    if kind == 'L4-L5':
        return dict(net=net, x=x, y=y, size=0.30, hole=0.15, span=['L4-SIG', 'L5-VCC3V3'], kind='micro')
    if kind == 'L3-L4':
        return dict(net=net, x=x, y=y, size=0.27, hole=0.15, span=['L3-SIG', 'L4-SIG'], kind='micro')
    raise ValueError(kind)


def RV(net, x, y, span):
    return dict(net=net, x=x, y=y, span=span)


def south(tpl):
    """Gap assignment: the Bottom pocket under U3 bounded by FT-VPHY (gap 5|6, then y 9.55) and TDO (gap 13|14)
    has 7 gaps (6|7..12|13) for 7 users (D3..D7, FT-VCORE, TMS).  Planarity under U3 (via x order) forces
    D7 12|13, FT-VCORE 11|12, D6 10|11, D5 9|10, D4 8|9, TMS 7|8, D3 6|7."""
    Rs = {}
    Rs['D0'] = tpl('D0', 'HA', +1)          # gap 1|2
    Rs['D1'] = tpl('D1', 'HA', +1)          # gap 3|4
    Rs['D2'] = tpl('D2', 'V', +1)           # gap 4|5
    Rs['D3'] = tpl('D3', 'HA', +1)          # gap 6|7 (U3-6 GND heel reshaped)
    Rs['D4'] = tpl('D4', 'HA', -1)          # gap 8|9 (U3-9 VCC3V3 moved to a heel microvia)
    Rs['D5'] = tpl('D5', 'V', +1)           # gap 9|10 (TMS moves to 7|8; FT-VCORE trunk lowered)
    Rs['D6'] = tpl('D6', 'V', +1)           # gap 10|11
    Rs['D7'] = tpl('D7', 'HA', +1)          # gap 12|13 (U3-12 GND path moved off x 29.54)
    rm_t, add_t, rm_v, add_v = [], [], [], []
    notes = []
    # U3-9 (VDDQ)
    rm_t += [T('Bottom', 'VCC3V3', 32.35, 6.17, 32.5, 5.1), T('Bottom', 'VCC3V3', 32.5, 5.1, 33.549, 5.1),
             T('Bottom', 'VCC3V3', 33.549, 3.95, 33.549, 5.1)]
    add_t += [T('Bottom', 'VCC3V3', 32.35, 6.17, 32.35, 7.0, 0.2)]
    add_v += [V('VCC3V3', 32.35, 7.0, 'L5-Bot')]
    notes.append('U3-9 VDDQ: toe track to C38-2 removed (C38-2 keeps its own feed from the via at (32.625,1.000) and C6-2); '
                 'a heel track and a Bottom>L5 microvia onto the VCC3V3 plane are added')
    # U3-6 (VSSQ) heel
    rm_t += [T('Bottom', 'GND', 34.475, 7.0, 34.475, 9.0), T('Bottom', 'GND', 34.475, 7.0, 34.75, 6.17)]
    add_t += [T('Bottom', 'GND', 34.75, 6.17, 34.75, 8.6, 0.25), T('Bottom', 'GND', 34.75, 8.6, 34.475, 9.0, 0.25)]
    notes.append('U3-6 VSSQ heel: the 0.41 mm GND dog-leg that crossed gap 6|7 becomes a 0.25 mm run straight up the pin '
                 'column to the same GND via (34.475,9.000)')
    # U3-12 (VSSQ) toe
    rm_t += [T('Bottom', 'GND', 29.54, 4.3, 29.54, 5.55), T('Bottom', 'GND', 29.54, 5.55, 29.95, 6.17)]
    add_t += [T('Bottom', 'GND', 30.05, 6.0, 30.05, 4.9, 0.1), T('Bottom', 'GND', 30.05, 4.9, 29.54, 4.9, 0.1),
              T('Bottom', 'GND', 29.54, 4.9, 29.54, 4.3, 0.115)]
    notes.append('U3-12 VSSQ toe: GND path to C152-1 re-run down x 30.05 and across y 4.90 (it ran down x 29.54, '
                 'in front of gap 12|13)')
    # FT-VCORE trunk
    rm_t += [T('Bottom', 'FT-VCORE', 29.949, 3.95, 29.949, 4.55), T('Bottom', 'FT-VCORE', 29.949, 4.55, 30.35, 4.55),
             T('Bottom', 'FT-VCORE', 30.35, 4.55, 31.149, 4.55), T('Bottom', 'FT-VCORE', 31.149, 3.95, 31.149, 4.55),
             T('Bottom', 'FT-VCORE', 31.149, 4.55, 32.349, 4.55), T('Bottom', 'FT-VCORE', 32.349, 3.95, 32.349, 4.55),
             T('Bottom', 'FT-VCORE', 32.349, 4.55, 32.55, 4.45), T('Bottom', 'FT-VCORE', 32.349, 4.45, 32.55, 4.45),
             T('Bottom', 'FT-VCORE', 30.35, 4.55, 30.35, 5.3)]
    add_t += [T('Bottom', 'FT-VCORE', 29.949, 3.95, 29.949, 4.28, 0.2), T('Bottom', 'FT-VCORE', 31.149, 3.95, 31.149, 4.28, 0.2),
              T('Bottom', 'FT-VCORE', 32.349, 3.95, 32.349, 4.28, 0.2),
              T('Bottom', 'FT-VCORE', 29.949, 4.28, 32.349, 4.28, 0.16), T('Bottom', 'FT-VCORE', 32.349, 4.28, 32.55, 4.45, 0.2),
              T('Bottom', 'FT-VCORE', 30.35, 4.28, 30.35, 5.3, 0.15)]
    notes.append('FT-VCORE (U2 core decoupling C152-C154): Bottom trunk y 4.55 (0.5/0.3 mm) -> y 4.28, 0.16 mm '
                 '(PWR_RAILS min 0.15), so D5/D6 can stand vertical; the 0.15 mm neck through gap 11|12 is unchanged')
    # TMS
    rm_t += [T('Bottom', 'TMS', 31.975, 5.25, 32.375, 4.85), T('Bottom', 'TMS', 32.375, 4.85, 32.65, 4.85),
             T('Bottom', 'TMS', 32.65, 4.85, 33.025, 4.475), T('Bottom', 'TMS', 31.975, 5.25, 31.975, 7.575),
             T('Bottom', 'TMS', 31.975, 7.575, 32.15, 8.125), T('L3-SIG', 'TMS', 32.15, 8.125, 32.15, 8.15)]
    rm_v += [RV('TMS', 32.15, 8.125, ['L5-VCC3V3', 'Bottom']), RV('TMS', 32.15, 8.125, ['L4-SIG', 'L5-VCC3V3']),
             RV('TMS', 32.15, 8.125, ['L3-SIG', 'L4-SIG'])]
    add_t += [T('L4-SIG', 'TMS', 33.45, 8.15, 33.85, 8.15, 0.0762),
              T('Bottom', 'TMS', 33.45, 8.15, 33.55, 8.05, 0.0762), T('Bottom', 'TMS', 33.55, 8.05, 33.55, 4.85, 0.0762),
              T('Bottom', 'TMS', 33.55, 4.85, 33.175, 4.475, 0.0762), T('Bottom', 'TMS', 33.175, 4.475, 33.025, 4.475, 0.0762)]
    add_v += [V('TMS', 33.45, 8.15, 'L4-L5'), V('TMS', 33.45, 8.15, 'L5-Bot')]
    notes.append('TMS (JTAG, 0.0762 mm): its Bottom crossing of the U3 row moves from gap 9|10 to gap 7|8; it drops to '
                 'Bottom through a new L4>L5>Bottom microvia stack at (33.450,8.150) on a 0.40 mm L4 extension of the '
                 'existing L4 TMS line, and reuses the existing stack at (33.025,4.475) outside the row')
    # TDO + C138-2: D7's R pad 1 sits 0.21 mm off U3-13's toe; TDO's diagonal (28.750,5.550)-(29.150,4.800) passed
    # 0.05 mm from it, and the VCC3V3 stub (28.750,3.950)-(28.750,4.850) to C138-2 left no other channel.  C138-2
    # gets its own Bottom>L5 microvia; TDO drops straight down x 28.75 and then 0.4 mm across to its stack.
    rm_t += [T('Bottom', 'VCC3V3', 28.75, 3.95, 28.75, 4.85), T('Bottom', 'VCC3V3', 27.93, 4.85, 28.75, 4.85),
             T('Bottom', 'TDO', 28.75, 5.55, 29.15, 4.8)]
    add_t += [T('Bottom', 'VCC3V3', 28.75, 3.95, 28.80, 4.40, 0.2),
              T('Bottom', 'TDO', 28.75, 5.55, 28.75, 4.95, 0.0762), T('Bottom', 'TDO', 28.75, 4.95, 29.15, 4.8, 0.0762)]
    add_v += [V('VCC3V3', 28.80, 4.40, 'L5-Bot')]
    notes.append('C138-2 (VCC3V3 decap): its 0.3 mm stub to the VCC3V3 hub microvia (27.930,4.850) is replaced by its own '
                 'Bottom>L5 microvia at (28.800,4.400); TDO (JTAG) re-shaped from one diagonal to down-then-across '
                 '(28.750,5.550)-(28.750,4.950)-(29.150,4.800)')
    return Rs, dict(remove_tracks=rm_t, add_tracks=add_t, remove_vias=rm_v, add_vias=add_v), notes
