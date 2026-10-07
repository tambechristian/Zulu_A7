# -*- coding: utf-8 -*-
"""How much routing does the FPGA ball assignment cost, and what would a re-pin buy?

THE QUESTION. The XC7A35T ball map was checked for LEGALITY by tools/vivado_io_check.py -- clock
capability, bank voltage, config mode -- and it passes. It was never checked for PLACEMENT: whether
a net's ball leaves the package on the side the net has to go. Every ball is allocated (106 user I/O,
all used), so a re-pin is a permutation, not an addition, and the moment to do it is before the board
is routed, not after.

WHAT MAKES IT ALMOST FREE HERE. Every VCCO on this board is 3.3 V -- 27 of them, from
docs/connectivity_check.md -- so bank voltage constrains nothing: any LVCMOS33 net may sit in any
bank. No net on this board is differential and nothing needs VREF, so pair members and VREF pins are
ordinary I/O too. That leaves four real constraints:

    dedicated    TCK TMS TDI TDO CCLK DONE INIT_B PROGRAM_B M0 M1 M2   cannot move at all
    master SPI   FLASH-D00..D03, FLASH-CS#, and PUDC_B                 fixed-function balls
    XADC         AIN15/AIN16 must be an ADxxP/ADxxN pair (bank 35)     8 pairs exist
    clock in     CHAN-CLK and CLK-12M-FPGA on the P half of an         DRC PLIO-9 otherwise,
                 MRCC or SRCC pair                                     and place_design refuses

Everything else -- 38 SDRAM nets, 33 header nets, 6 microSD, 8 Pmod, the UART, the LEDs -- is freely
permutable. The clock rule is enforced here as an infinite cost rather than left to luck: the one
real defect vivado_io_check ever found was CHAN-CLK sitting on an N-half CCIO.

HOW COST IS MEASURED. Each ball has a position in the package (19x19 on a 0.5 mm pitch); each net has
somewhere on the board it must reach; the package sits at one of four rotations. A net costs the
Manhattan distance from its ball to its destination, plus a surcharge for how deep in the ball field
the ball sits -- ring 0 escapes on the top layer for free, rings 1 and 2 have to fight their way out.
The surcharge is reported separately because it is the same for every assignment: the set of balls
does not change, only which net sits on which.

Distance is a proxy and it says so. It knows nothing about crossings, layer changes or the header's
through-hole fence. It is good at the one thing that matters most, which is whether a net leaves the
package pointing at where it is going.

WHAT IT REPORTS. The cost of the current map at each rotation, broken down by group; the best legal
permutation as a lower bound; that permutation expressed as INDEPENDENT CYCLES, so a subset can be
adopted without taking all of it; and the worst individual nets, because the tail is what blocks a
route, not the average.

    python tools/repin_study.py tools
"""
import sys, os, re, io, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(os.path.dirname(HERE), 'Imported zulu_a7.PrjPcb')
NET = os.path.join(PRJ, 'Project Outputs for zulu_a7', 'zulu_a7.NET')
PINOUT = os.path.normpath(os.path.join(HERE, '..', '..', 'Datasheet',
                                       'xc7a35tcpg236pkg_pinout.txt'))

COLS = 'ABCDEFGHJKLMNPRTUVW'                 # the BGA skips I, O, Q and S
PITCH = 0.5
RAIL = {'GND', 'VCC3V3', 'VCC1V8', 'VCC1V0', 'VCCADC', 'GNDADC'}
RING_COST = {0: 0.0, 1: 3.0, 2: 6.0}
CLOCK_IN = ('CHAN-CLK', 'CLK-12M-FPGA')
BIG = 1e6

ROW_Y = {'top': 24.13, 'bot': 1.27}          # header rows, 22.86 mm apart on a 25.40 board
PIN_X = ([59.69 - 2.54 * k for k in range(9)]        # pins 1-9 and 21-29
         + [None] * 4                                 # the USB and LiPo landings
         + [26.67 - 2.54 * k for k in range(11)])     # pins 10-20 and 30-40
FPGA = (46.4, 11.9)                          # package centre, from the placement drawing
PARTS = {'microSD': (8.5, 12.5), 'BTN': (20.1, 12.5), 'LEDs': (25.2, 12.6),
         'FT2232': (33.0, 11.8), 'Pmod': (66.4, 11.8), 'Q1': (39.8, 19.8),
         'FLASH': (5.3, 9.6), 'ANALOG': (2.5, 1.27)}
SDRAM_C, SDRAM_ROW = (28.35, 11.85), 5.88    # centre, and half the TSOP-54 lead span
SDRAM_PIN1_RIGHT = True


def pinout():
    fn = {}
    for line in io.open(PINOUT, encoding='utf-8', errors='replace'):
        p = line.split()
        if len(p) >= 2 and re.fullmatch(r'[A-Z]{1,2}\d{1,2}', p[0]):
            fn[p[0]] = p[1:]
    return fn


def netlist():
    s = io.open(NET, encoding='utf-8', errors='replace').read()
    pads = collections.defaultdict(dict)
    for blk in re.findall(r'^\($(.*?)^\)$', s, re.S | re.M):
        L = [l.strip() for l in blk.strip().splitlines() if l.strip()]
        for p in L[1:]:
            part, _, d = p.partition('-')
            pads[part][d] = L[0]
    return pads


def ball_xy(b):
    m = re.match(r'([A-Z]+)(\d+)', b)
    return (int(m.group(2)) - 10) * PITCH, (COLS.index(m.group(1)) - 9) * PITCH


def ring(b):
    m = re.match(r'([A-Z]+)(\d+)', b)
    c, r = COLS.index(m.group(1)), int(m.group(2)) - 1
    return min(c, r, len(COLS) - 1 - c, 18 - r)


def rotate(p, deg):
    x, y = p
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[deg]


def board_pos(b, deg):
    px, py = rotate(ball_xy(b), deg)
    return FPGA[0] + px, FPGA[1] + py


def sdram_pin_xy(n):
    """TSOP-54: pins 1-27 down one long side, 28-54 back along the other."""
    n = int(n)
    i = n - 1 if n <= 27 else 54 - n
    off = (i - 13) * 0.8
    return (SDRAM_C[0] + (off if SDRAM_PIN1_RIGHT else -off),
            SDRAM_C[1] + (SDRAM_ROW if n <= 27 else -SDRAM_ROW))


def clock_ok(fn, b):
    f = fn.get(b, [''])[0]
    return ('MRCC' in f or 'SRCC' in f) and re.search(r'_L\d+P_', f) is not None


def destinations(pads):
    dst = {}
    for pin, net in pads['X2'].items():
        if net in RAIL:
            continue
        k = int(pin)
        idx = (k - 1) % 20
        dst[net] = (PIN_X[idx if idx < 9 else idx + 4], ROW_Y['top' if k <= 20 else 'bot'])
    for pin, net in pads['U3'].items():
        if net not in RAIL:
            dst[net] = sdram_pin_xy(pin)
    for net, where in (('SD-CLK', 'microSD'), ('SD-CMD', 'microSD'), ('SD-DAT0', 'microSD'),
                       ('SD-DAT1', 'microSD'), ('SD-DAT2', 'microSD'), ('SD-DAT3', 'microSD'),
                       ('BTN', 'BTN'), ('LED0_R', 'LEDs'), ('LED0_G', 'LEDs'), ('LED0_B', 'LEDs'),
                       ('LED1', 'LEDs'), ('LED2', 'LEDs'), ('CLK-12M-FPGA', 'Q1'),
                       ('FLASH-CS#', 'FLASH'), ('FLASH-D00', 'FLASH'), ('FLASH-D01', 'FLASH'),
                       ('FLASH-D02', 'FLASH'), ('FLASH-D03', 'FLASH'), ('AIN15_P', 'ANALOG'),
                       ('AIN15_N', 'ANALOG'), ('AIN16_P', 'ANALOG'), ('AIN16_N', 'ANALOG')):
        dst[net] = PARTS[where]
    dst['FPGA-CCLK'] = PARTS['FLASH']            # CCLK drives the flash, not the bridge
    for net in ('CFG-M0', 'CFG-M1', 'CFG-M2', 'PUDC_B'):
        dst[net] = FPGA                          # a strap resistor follows its ball anywhere
    for net in ('UART_FT_TXD', 'UART_FT_RXD', 'UART_FT_RTS#', 'UART_FT_DTR#', 'UART_FT_CTS#',
                'FT-PWREN#', 'FPGA-TCK', 'FPGA-TMS', 'FPGA-TDI', 'FPGA-TDO', 'FPGA-DONE',
                'FPGA-INIT#', 'RST#'):
        dst.setdefault(net, PARTS['FT2232'])
    for k in range(1, 11):
        dst[f'JA{k}'] = PARTS['Pmod']
    return dst


def dist(b, net, dst, deg):
    if net not in dst:
        return 0.0
    bx, by = board_pos(b, deg)
    dx, dy = dst[net]
    return abs(bx - dx) + abs(by - dy)


def cost(b, net, dst, deg, fn=None):
    if fn is not None and net in CLOCK_IN and not clock_ok(fn, b):
        return BIG
    return dist(b, net, dst, deg) + RING_COST[ring(b)]


def hungarian(m):
    """minimum-cost assignment on a square matrix, O(n^3)."""
    n = len(m)
    INF = float('inf')
    u, v = [0.0] * (n + 1), [0.0] * (n + 1)
    p, way = [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        minv, used = [INF] * (n + 1), [False] * (n + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = m[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j], way[j] = cur, j0
                if minv[j] < delta:
                    delta, j1 = minv[j], j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0], j0 = p[j1], j1
    out = [0] * n
    for j in range(1, n + 1):
        out[p[j] - 1] = j - 1
    return out


def main(_):
    fn, pads = pinout(), netlist()
    ball = {d: n for d, n in pads['U1'].items() if n not in RAIL}
    dst = destinations(pads)

    DEDICATED = {b for b in ball if len(fn.get(b, [])) > 1 and fn[b][1] == 'NA'}
    FIXEDFN = {b for b, n in ball.items()
               if n in ('FLASH-D00', 'FLASH-D01', 'FLASH-D02', 'FLASH-D03', 'FLASH-CS#', 'PUDC_B')}
    XADC = {b for b, n in ball.items() if n.startswith('AIN')}
    free = sorted(b for b in ball if b not in (DEDICATED | FIXEDFN | XADC))
    missing = sorted(n for n in ball.values() if n not in dst)
    print(f'{len(ball)} signal balls: {len(DEDICATED)} dedicated, {len(FIXEDFN)} fixed-function, '
          f'{len(XADC)} XADC, {len(free)} freely permutable')
    if missing:
        print(f'   no destination modelled for: {missing}')

    U3, X2 = set(pads['U3'].values()), set(pads['X2'].values())

    def group(n):
        return ('SDRAM' if n in U3 else 'header' if n in X2 else
                'microSD' if n.startswith('SD-') else 'Pmod' if n.startswith('JA') else
                'flash' if n.startswith('FLASH') else 'XADC' if n.startswith('AIN') else
                'config' if re.match(r'(FPGA-|CFG-|PUDC|RST)', n) else 'other')

    r1 = sum(1 for b in ball if ring(b) == 1)
    r2 = sum(1 for b in ball if ring(b) == 2)
    print(f'\nring surcharge, identical for every assignment: {sum(RING_COST[ring(b)] for b in ball):.0f}'
          f' mm-equivalent ({r1} balls in ring 1, {r2} in ring 2)')
    print('\nrotation   distance (mm)   by group')
    best = None
    for deg in (0, 90, 180, 270):
        per = collections.Counter()
        for b, n in ball.items():
            per[group(n)] += dist(b, n, dst, deg)
        tot = sum(per.values())
        top = '  '.join(f'{k} {v:.0f}' for k, v in sorted(per.items(), key=lambda kv: -kv[1]))
        print(f'  {deg:3} deg      {tot:8.0f}   {top}')
        if best is None or tot < best[1]:
            best = (deg, tot)
    deg = best[0]
    print(f'-> the package should sit at {deg} degrees')

    nets = [ball[b] for b in free]
    M = [[cost(b, n, dst, deg, fn) for n in nets] for b in free]
    got = hungarian(M)
    opt = sum(M[i][got[i]] for i in range(len(free)))
    base = sum(cost(b, ball[b], dst, deg, fn) for b in free)
    gap = base - opt
    print(f'\nthe {len(free)} permutable nets cost {base:.0f} as assigned; the best legal '
          f'permutation costs {opt:.0f}')
    print(f'-> a full re-pin takes {gap:.0f} mm out, {gap / base * 100:.0f}% of what those nets cost')

    want = {free[i]: nets[got[i]] for i in range(len(free))}
    where = {n: b for b, n in ball.items()}
    seen, cycles = set(), []
    for b in free:
        if b in seen or want[b] == ball[b]:
            continue
        cyc, cur = [], b
        while cur in want and cur not in seen:
            seen.add(cur)
            cyc.append(cur)
            cur = where[want[cur]]
        if len(cyc) > 1:
            g = sum(cost(x, ball[x], dst, deg, fn) - cost(x, want[x], dst, deg, fn) for x in cyc)
            cycles.append((g, cyc))
    cycles.sort(reverse=True)
    print(f'\nthat permutation is {len(cycles)} INDEPENDENT cycles -- each is a self-contained '
          f'rotation of nets between balls, adoptable on its own:')
    run = 0.0
    for k, (g, cyc) in enumerate(cycles, 1):
        run += g
        print(f'  {k:2}. {len(cyc)}-cycle  saves {g:6.1f} mm   cumulative {run / gap * 100:3.0f}%')
        print('      ' + '  ->  '.join(f'{ball[x]}@{x}' for x in cyc) +
              f'  ->  back to {ball[cyc[0]]}@{cyc[0]}')
        if k == 10 and len(cycles) > 10:
            print(f'      ... {len(cycles) - 10} smaller cycles hold the last {gap - run:.0f} mm')
            break

    print('\nthe tail -- the worst nets now, and what the optimum does with them:')
    worst = sorted(((dist(b, n, dst, deg), b, n) for b, n in ball.items()), reverse=True)
    for d, b, n in worst[:14]:
        if b in want:
            goes = [x for x in want if want[x] == n]
            print(f'  {n:12} {b:4} ring {ring(b)}  {d:5.1f} mm  ->  moves to '
                  f'{goes[0] if goes else "?":4} ({dist(goes[0], n, dst, deg) if goes else 0:5.1f} mm)')
        else:
            print(f'  {n:12} {b:4} ring {ring(b)}  {d:5.1f} mm  (fixed, cannot move)')

    out = os.path.join(os.path.dirname(HERE), 'docs', 'repin_study.json')
    io.open(out, 'w', encoding='utf-8').write(json.dumps(
        {'rotation': deg, 'movable_cost_now': base, 'movable_cost_ideal': opt,
         'cycles': [{'saves': g, 'balls': c, 'nets_now': [ball[x] for x in c]} for g, c in cycles],
         'ideal_map': want}, indent=1, sort_keys=True))
    print(f'\nwritten: {out}')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'tools')
