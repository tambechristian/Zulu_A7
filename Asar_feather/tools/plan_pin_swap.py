"""Choose the FPGA ball for each Feather header signal (2026-10-23, pre-routing pass).

Pool: the 19 balls already on Feather pins (CHAN0-8, CHAN14-22, CHAN-CLK) plus the 19 balls the Feather freed
(old CHAN9-13, CHAN23-28 and the Pmod JA1-4/JA7-10), all on 3.3 V banks 14/16. D4 keeps P18 (CHAN-CLK,
clock-capable SRCC). The other 18 header pads get balls by a minimum-total-distance assignment (straight line,
ball to pad, board coordinates from tools/board_dump.json). With U1 at rot 180 its A row faces south, so pads on
the south (16-pin) strip take U1's A-H balls and the north (12-pin) strip its U-W balls. This is only the first
re-pin: swapA, swapB and x_perm_b (README) moved six of these nets again. Net names stay as they are (CHANn);
only the ball under each net changes. Writes tools/pin_swap.json: {net: [old ball, new ball]} and the ball
permutation used to rename U1's symbol pins.
    python tools/plan_pin_swap.py
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feather_map as M  # noqa: E402
import verify_placement as V  # noqa: E402

USED = {'CHAN0': 'B18', 'CHAN1': 'A18', 'CHAN2': 'B17', 'CHAN3': 'A17', 'CHAN4': 'C16', 'CHAN5': 'D17',
        'CHAN6': 'H17', 'CHAN7': 'G17', 'CHAN8': 'J18', 'CHAN14': 'W17', 'CHAN15': 'V17', 'CHAN16': 'W16',
        'CHAN17': 'U16', 'CHAN18': 'V16', 'CHAN19': 'W15', 'CHAN20': 'V15', 'CHAN21': 'U15', 'CHAN22': 'W14'}
FIXED = {'CHAN-CLK': 'P18'}
FREED = ['J17', 'J19', 'K18', 'E19', 'H19', 'V14', 'U14', 'W13', 'V13', 'T18', 'T17',
         'U18', 'U19', 'W18', 'C17', 'R19', 'W19', 'V19', 'U17']


def main():
    u1 = {q[1]: ((q[3] + q[5]) / 2, (q[4] + q[6]) / 2) for q in V.abs_pads('U1')}
    x2 = {q[1]: ((q[3] + q[5]) / 2, (q[4] + q[6]) / 2) for q in V.abs_pads('X2') if q[1]}
    net_of_pad = {}
    for pad, (name, old, label) in M.FEATHER.items():
        net = 'CHAN%d' % (old - 3) if 3 <= old <= 11 else 'CHAN%d' % (old - 10) if 24 <= old <= 32 else None
        if net in USED:
            net_of_pad[pad] = net
    pads = sorted(net_of_pad)
    balls = sorted(set(USED.values()) | set(FREED))
    cost = np.array([[math.dist(x2[str(p)], u1[b]) for b in balls] for p in pads])
    rows, cols = linear_sum_assignment(cost)
    swap = {}
    for r, c in zip(rows, cols):
        net = net_of_pad[pads[r]]
        swap[net] = [USED[net], balls[c]]
    # permutation of balls over the pool: every old net ball goes to its new ball; freed balls fill the gaps
    perm = {old: new for old, new in swap.values()}
    leftover_targets = [b for b in balls if b not in perm.values()]
    leftover_sources = [b for b in balls if b not in perm]
    perm.update(dict(zip(leftover_sources, leftover_targets)))
    assert sorted(perm) == sorted(perm.values()) == balls
    before = sum(math.dist(x2[str(p)], u1[USED[net_of_pad[p]]]) for p in pads)
    after = cost[rows, cols].sum()
    json.dump({'swap': swap, 'perm': perm, 'fixed': FIXED, 'total_mm_before': round(before, 1),
               'total_mm_after': round(float(after), 1)}, open(os.path.join(HERE, 'pin_swap.json'), 'w'), indent=1)
    for p in pads:
        net = net_of_pad[p]
        print('pad %2d %-5s %-7s %4s -> %-4s  %5.1f -> %5.1f mm' % (
            p, M.FEATHER[p][0], net, swap[net][0], swap[net][1], math.dist(x2[str(p)], u1[swap[net][0]]),
            math.dist(x2[str(p)], u1[swap[net][1]])))
    print('total straight-line length %.1f -> %.1f mm' % (before, after))


if __name__ == '__main__':
    main()
