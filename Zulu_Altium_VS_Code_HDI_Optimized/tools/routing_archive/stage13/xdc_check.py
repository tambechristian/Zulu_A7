# judge (read-only): apply the 13 PACKAGE_PIN edits to an IN-MEMORY copy of the XDC and check the result:
# each edited line names the expected port and old pin; afterwards every PACKAGE_PIN is unique, the 13 balls are a
# permutation, every moved ball is bank 14 per the Xilinx pinout file, and no create_clock port moved.
#   python xdc_check.py <zulu_a7_pins.xdc> <xc7a35tcpg236pkg_pinout.txt> [edited.xdc to check instead of simulating]
import io, re, sys, collections
EDITS = [(80, 'JA3', 'G17', 'W18'), (49, 'CHAN7', 'H19', 'G17'), (28, 'CHAN13', 'W18', 'H19'), (82, 'JA7', 'T17', 'R19'),
         (44, 'CHAN28', 'R19', 'T17'), (83, 'JA8', 'E19', 'W19'), (27, 'CHAN12', 'W19', 'E19'), (104, 'UART_FT_TXD', 'K18', 'K17'),
         (26, 'CHAN11', 'K17', 'K18'), (86, 'LED0_B', 'N19', 'N17'), (21, 'BTN', 'N17', 'N19'), (76, 'FT_PWREN_N', 'P17', 'P19'),
         (88, 'LED0_R', 'P19', 'P17')]
lines = io.open(sys.argv[1], encoding='utf-8').read().split('\n')
pin = {}
for l in io.open(sys.argv[2], encoding='latin-1'):
    p = l.split()
    if len(p) >= 4 and re.match(r'^[A-W]\d+$', p[0]):
        pin[p[0]] = (p[1], p[3])
ok = True
if len(sys.argv) > 3:
    new = io.open(sys.argv[3], encoding='utf-8').read().split('\n')
else:
    new = list(lines)
    for ln, port, old, nw in EDITS:
        l = new[ln - 1]
        m = re.search(r'PACKAGE_PIN (\S+) .*get_ports \{([^}]*)\}', l)
        if not m or m.group(1) != old or m.group(2) != port:
            print('LINE %d does not read PACKAGE_PIN %s ... {%s}: %r' % (ln, old, port, l)); ok = False; continue
        new[ln - 1] = l.replace('PACKAGE_PIN %s ' % old, 'PACKAGE_PIN %s ' % nw, 1)
for ln, port, old, nw in EDITS:
    m = re.search(r'PACKAGE_PIN (\S+) .*get_ports \{([^}]*)\}', new[ln - 1])
    if not m or m.group(1) != nw or m.group(2) != port:
        print('after: line %d is %r, expected %s on %s' % (ln, new[ln - 1], port, nw)); ok = False
pins = collections.Counter(m.group(1) for l in new for m in [re.search(r'PACKAGE_PIN (\S+)', l)] if m)
dup = [p for p, n in pins.items() if n > 1]
print('PACKAGE_PIN entries %d, duplicates %s' % (sum(pins.values()), dup or 'none')); ok &= not dup
frm, to = sorted(e[2] for e in EDITS), sorted(e[3] for e in EDITS)
print('from-balls == to-balls (a permutation): %s' % (frm == to)); ok &= frm == to
for ln, port, old, nw in EDITS:
    print('   line %3d %-12s %s -> %s  %s bank %s' % (ln, port, old, nw, pin[nw][0], pin[nw][1]))
    ok &= pin[nw][1] == '14'
clk = [m.group(1) for l in new for m in [re.search(r'create_clock.*get_ports \{?([^}\]\s]*)', l)] if m]
print('create_clock ports: %s; moved among them: %s' % (clk, [e[1] for e in EDITS if e[1] in clk] or 'none'))
std = [l for l in new if 'PACKAGE_PIN' in l and 'LVCMOS33' not in l]
print('PACKAGE_PIN lines not LVCMOS33: %d' % len(std))
print('XDC_CHECK %s' % ('PASS' if ok else 'FAIL'))
sys.exit(0 if ok else 1)
