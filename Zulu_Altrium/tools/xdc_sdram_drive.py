# -*- coding: utf-8 -*-
"""Write the SDRAM bus DRIVE / SLEW constraints into vivado/zulu_a7_pins.xdc,
deriving the 39 port names from the board rather than typing them.

    python tools/xdc_sdram_drive.py           report only
    python tools/xdc_sdram_drive.py --apply   insert the block (idempotent)

WHY.  docs/sdram_bus_widths.md: the bus is an unterminated 3.3 V LVTTL run of
9-33 mm, and overshoot at the open SDRAM inputs is set by the FPGA's DRIVE,
not by trace width -- 8 mA gives <= +0.24 V at any width, 12/16 mA FAST gives
+0.7..1.0 V at any width.  The XDC carried no DRIVE or SLEW at all, so Vivado's
default (DRIVE 12 SLEW SLOW) applied by omission.  This makes it explicit:
DRIVE 8 SLEW SLOW on the 38 data / address / control ports, DRIVE 8 SLEW FAST
on SDRAM_CLK (one monotonic step; its tAC penalty [(tr+tf)/2 - 1] ns is zero
up to a 2.0 ns edge).  Never FAST at 12 or 16 mA without a series resistor.

HOW THE NAMES ARE FOUND.  U1's balls and their nets come from Pads6 of the
PcbDoc; the XDC's own PACKAGE_PIN lines give ball -> port.  A port is on the
bus if its ball's net is one of the 39 SDRAM nets (SDRAM_DATA 16, SDRAM_ADDR
15, SDRAM_CTRL 8, the same classes the board's Width_SDRAM rule scopes).  If
the XDC and the board ever disagree on a ball, this script says so and stops.
"""
import io
import os
import re
import struct
import sys

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, '..', 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')
XDC = os.path.join(HERE, '..', '..', 'vivado', 'zulu_a7_pins.xdc')

DATA = {'D%d' % k for k in range(16)}
ADDR = {'A%d' % k for k in range(13)} | {'BS0', 'BS1'}
CTRL = {'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK'}
SDRAM = DATA | ADDR | CTRL

BEGIN = '# ---- SDRAM bus drive strength, 2026-09-15'
END = '# ---- end SDRAM bus drive strength'


def u1_balls():
    """ball name -> net name for every netted U1 ball"""
    f = olefile.OleFileIO(PCB)
    nd = f.openstream('Nets6/Data').read().decode('latin-1', 'replace')
    nets = {}
    for i, r in enumerate(x for x in nd.split(chr(0)) if 'NAME=' in x):
        kv = dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv)
        nets[i] = kv.get('NAME')
    cd = f.openstream('Components6/Data').read().decode('latin-1', 'replace')
    comps = {}
    for i, r in enumerate(x for x in cd.split(chr(0)) if 'SOURCEDESIGNATOR=' in x):
        kv = dict(kv.split('=', 1) for kv in r.strip('|').split('|') if '=' in kv)
        comps[i] = kv.get('SOURCEDESIGNATOR')
    d = f.openstream('Pads6/Data').read()
    f.close()
    out = {}
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        if t != 2:
            break
        name = d[i + 6:i + 6 + d[i + 5]].decode('latin-1')
        i += 5 + ln
        for k in range(3):
            l2 = struct.unpack('<I', d[i:i + 4])[0]
            i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        b = d[i + 4:i + 4 + l2]
        i += 4 + l2
        l2 = struct.unpack('<I', d[i:i + 4])[0]
        i += 4 + l2
        if comps.get(struct.unpack('<h', b[7:9])[0]) == 'U1':
            n = struct.unpack('<h', b[3:5])[0]
            if n >= 0:
                out[name] = nets.get(n)
    return out


def xdc_pins(text):
    """(ball, port) for every PACKAGE_PIN line"""
    return re.findall(r'PACKAGE_PIN\s+([A-Z]\d+)\s+IOSTANDARD\s+\w+\s*\}\s*\[get_ports\s*\{?\s*([^}\]\s]+)', text)


def norm(s):
    return s.upper().replace('#', '_N').replace('-', '_')


def main():
    text = io.open(XDC, encoding='utf-8').read()
    balls = u1_balls()
    pins = xdc_pins(text)
    print('XDC: %d PACKAGE_PIN lines; board: %d netted U1 balls' % (len(pins), len(balls)))

    ports = {'data': [], 'addr': [], 'ctrl': [], 'clk': []}
    bad = []
    for ball, port in pins:
        net = balls.get(ball)
        if net is None:
            bad.append('%s -> %s: not a netted ball on the board' % (ball, port))
            continue
        if norm(net) != norm(port):
            bad.append('%s: XDC port %s, board net %s' % (ball, port, net))
            continue
        if net == 'SDRAM-CLK':
            ports['clk'].append(port)
        elif net in DATA:
            ports['data'].append(port)
        elif net in ADDR:
            ports['addr'].append(port)
        elif net in CTRL:
            ports['ctrl'].append(port)
    if bad:
        print('XDC AND BOARD DISAGREE - not touching the file:')
        for x in bad:
            print('  ', x)
        return 1
    found = sum(len(v) for v in ports.values())
    print('SDRAM ports found: data %d, addr+bank %d, ctrl %d, clk %d = %d (want 39)'
          % (len(ports['data']), len(ports['addr']), len(ports['ctrl']), len(ports['clk']), found))
    if found != 39 or len(ports['clk']) != 1:
        print('WRONG COUNT - not touching the file')
        return 1

    def natural(p):
        m = re.match(r'([A-Z_]+)(\d*)', p)
        return (m.group(1), int(m.group(2) or 0))

    block = [
        BEGIN + ' -----------------------------------------------',
        '# Derived from the board by tools/xdc_sdram_drive.py: the 39 SDRAM nets on U1',
        '# (Zulu_Altrium/docs/sdram_bus_widths.md).  The bus is an unterminated 3.3 V',
        '# LVTTL run of 9-33 mm; overshoot at the open SDRAM inputs is set by DRIVE, not',
        '# by trace width: 8 mA gives <= +0.24 V at any width, 12/16 mA FAST gives',
        '# +0.7..1.0 V.  Vivado\'s default (DRIVE 12 SLEW SLOW) was acceptable only by',
        '# omission.  NEVER FAST at 12 or 16 mA without a series resistor -- that is a',
        '# schematic change, not a constraint.  SDRAM_CLK gets FAST at 8 mA: it wants',
        '# one monotonic step, and its tAC penalty [(tr+tf)/2 - 1] ns is zero up to a',
        '# 2.0 ns edge.',
        'set_property -dict {DRIVE 8 SLEW SLOW} [get_ports {%s}]  ;# SDRAM data'
        % ' '.join(sorted(ports['data'], key=natural)),
        'set_property -dict {DRIVE 8 SLEW SLOW} [get_ports {%s}]  ;# SDRAM address + bank'
        % ' '.join(sorted(ports['addr'], key=natural)),
        'set_property -dict {DRIVE 8 SLEW SLOW} [get_ports {%s}]  ;# SDRAM control'
        % ' '.join(sorted(ports['ctrl'], key=natural)),
        'set_property -dict {DRIVE 8 SLEW FAST} [get_ports {%s}]  ;# SDRAM clock: one clean edge'
        % ports['clk'][0],
        END + ' -------------------------------------------------',
    ]
    print('\n'.join(block))

    if '--apply' not in sys.argv:
        print('\n(report only; --apply writes it)')
        return 0

    # idempotent: replace an existing block, else insert before the create_clock lines
    if BEGIN in text:
        s = text.index(BEGIN)
        e = text.index(END)
        e = text.index('\n', e) + 1
        text = text[:s] + '\n'.join(block) + '\n' + text[e:]
    else:
        anchor = text.index('\ncreate_clock')
        text = text[:anchor] + '\n' + '\n'.join(block) + '\n' + text[anchor:]
    io.open(XDC, 'w', encoding='utf-8', newline='\n').write(text)
    print('\nwritten: %s' % os.path.normpath(XDC))
    return 0


if __name__ == '__main__':
    sys.exit(main())
