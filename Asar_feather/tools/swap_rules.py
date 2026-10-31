"""Which FPGA ball may carry which net (2026-10-27, the ball-swap lever for the open connections).

Reads ../Datasheet/xc7a35tcpg236pkg_pinout.txt. Every I/O bank this board uses (14, 16, 34, 35) is at 3.3 V (every
line of vivado/asar_feather_pins.xdc is LVCMOS33), so a user net may move to any HR ball of those banks, except:
  - dedicated and config balls: bank 0 (JTAG, M0-M2, PROGRAM_B, DONE, CCLK, XADC supplies) and the bank-14 balls
    whose dual configuration function the board uses (D00_MOSI, D01_DIN, D02, D03, FCS_B, PUDC_B) stay as they are,
    and so do the nets on them;
  - XADC inputs (AIN*_P/_N) must sit on an ADnP/ADnN pair, P on P and N on N;
  - the 12 MHz clock input stays on an MRCC ball; the header clock CHAN-CLK (F_D4, SRCC) is left alone;
  - header pins (CHANn, driven from outside) avoid RDWR_B and EMCCLK, which the configuration logic samples;
  - SDRAM nets stay in banks 34/35/16 (the east and north faces, towards U3);
  - transceiver balls (bank 216) and power/ground are never I/O.

As a module: BALLS (ball -> {'name', 'bank', 'type'}), kind(net), legal(net, ball), fixed(net).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import router as R  # noqa: E402

PINOUT = os.path.join(HERE, '..', '..', 'Datasheet', 'xc7a35tcpg236pkg_pinout.txt')
HR_BANKS = {'14', '16', '34', '35'}
SDRAM_BANKS = {'34', '35', '16'}
CONFIG_FN = re.compile(r'_(D0[0-3]|DIN|MOSI|FCS_B|PUDC_B)(_|$)')
EXTERNAL_AVOID = re.compile(r'_(RDWR_B|EMCCLK)(_|$)')
AD = re.compile(r'_AD(\d+)([PN])_')
FIXED_NETS = {'CFG-M0', 'CFG-M1', 'CFG-M2', 'FPGA-TCK', 'FPGA-TDI', 'FPGA-TDO', 'FPGA-TMS', 'RST#', 'PUDC_B',
              'FLASH-D00', 'FLASH-D01', 'FLASH-D02', 'FLASH-D03', 'FLASH-CS#', 'FPGA-CCLK', 'FPGA-DONE',
              'FPGA-INIT#', 'PROG#', 'DONE', 'CHAN-CLK', 'VCCADC', 'GNDADC', 'DONE-PU'}
POWER = {'GND', 'VCC3V3', 'VCC1V0', 'VCC1V8', 'VU', 'VBATT', 'USB5V0', 'VCCADC', 'GNDADC'}


def _load():
    out = {}
    for line in open(PINOUT):
        f = line.split()
        if len(f) < 8 or f[0] in ('Pin', 'Device/Package'):
            continue
        out[f[0]] = {'name': f[1], 'bank': f[3], 'type': f[6]}      # columns: pin, name, byte group, bank, vccaux, slr, type, nc
    return out


BALLS = _load()


def kind(net):
    if net in FIXED_NETS or net in POWER or net.startswith('Net') or net.startswith('N$'):
        return 'fixed'
    if net in R.SDRAM:
        return 'sdram'
    if net.startswith('AIN'):
        return 'xadc'
    if net == 'CLK-12M-FPGA':
        return 'clock'
    if net.startswith('CHAN'):
        return 'header'
    return 'io'


def fixed(net):
    return kind(net) == 'fixed'


def ad_pair(ball):
    """('4', 'P') for IO_L1P_T0_AD4P_35, else None"""
    m = AD.search(BALLS.get(ball, {}).get('name', ''))
    return (m.group(1), m.group(2)) if m else None


def legal(net, ball):
    """may `net` be carried by `ball`? (electrical rules only; the other ball of a swap is judged separately)"""
    b = BALLS.get(ball)
    if not b or b['type'] != 'HR' or b['bank'] not in HR_BANKS or CONFIG_FN.search(b['name']):
        return False
    k = kind(net)
    if k == 'fixed':
        return False
    if k == 'sdram':
        return b['bank'] in SDRAM_BANKS
    if k == 'xadc':
        p = ad_pair(ball)
        return p is not None and p[1] == net[-1]
    if k == 'clock':
        return 'MRCC' in b['name']
    if k == 'header':
        return not EXTERNAL_AVOID.search(b['name'])
    return True


if __name__ == '__main__':
    import json
    M = json.load(open(os.path.join(HERE, 'route', 'model.json')))
    u1 = {p['pad']: p['net'] for p in M['pads'] if p['ref'] == 'U1'}
    for ball, net in sorted(u1.items()):
        b = BALLS[ball]
        print('%-4s %-30s bank %-3s %-6s %-14s %s' % (ball, b['name'], b['bank'], b['type'], net or '-',
                                                    kind(net) if net else ('free' if legal('LED1', ball) else '')))
