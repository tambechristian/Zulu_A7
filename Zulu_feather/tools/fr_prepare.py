"""Routing stage 2 (2026-10-23): Feather -> Specctra DSN for Freerouting, with the placed copper locked.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/fr_prepare.py <workdir>              step 1: board, exit 127
    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/fr_prepare.py <workdir> --export     step 2: DSN + rules

Reads zulu_feather.PcbDoc through KiCad's Altium importer, locks every track and via (they export as
(type fix)), saves <workdir>/feather.kicad_pcb, exports <workdir>/feather.dsn and rewrites its rules:
  - L2-GND and L5-VCC3V3 become power layers: Freerouting does not route on them and treats the GND / VCC3V3
    pours as planes a via connects to
  - default class: 0.0762 mm tracks, 0.09 mm clearance (the board's Width and Clearance minimums; production
    routed U1's field at 0.0762)
  - classes sdram, v33, u8, v10, sw, rails, usb: the board's per-layer Width minimums (CLASSES below), written as
    (layer_rule ...) inside each class
  - run Freerouting with --router.automatic_neckdown=false (it otherwise necks tracks to 0.057 mm at pads)
  - vias: the board's own types only -- through 0.35/0.20, laser 0.30/0.15 Top-L2, L2-L3, L4-L5, L5-Bottom,
    buried 0.27/0.15 L3-L4 (the 0.6/0.3 default padstack is dropped)
  - keepouts: a 0.3 mm band inside the board edge and 1.2 mm squares in the rounded corners, on every routing
    layer (Freerouting keeps no clearance to the outline by itself)
"""
import os
import re
import sys

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'Zulu_feather.PrjPcb', 'zulu_feather.PcbDoc')
VIAS = ['Via[0-5]_350:200_um', 'Via[0-1]_300:150_um', 'Via[1-2]_300:150_um', 'Via[2-3]_270:150_um',
        'Via[3-4]_300:150_um', 'Via[4-5]_300:150_um']
SDRAM = ['D%d' % i for i in range(16)] + ['A%d' % i for i in range(13)] + [
    'BS0', 'BS1', 'CAS#', 'RAS#', 'WE#', 'CKE', 'LDQM', 'UDQM', 'SDRAM-CS#', 'SDRAM-CLK']
# per-class track widths (um) from the board's Width rules: (default width, {layer: minimum on that layer})
# Width_SDRAM 3 mil / 3.937 mil on L3, L4, Bottom; Width_PWR_VCC3V3 3 mil, 41.34 mil on L3/L4, 7.874 mil Bottom;
# Width_PWR_U8 7.874 mil, 43.31 mil on L3/L4; Width_PWR_VCC1V0 5.906 mil, 19.685 mil on L3/L4; PWR_SWITCH
# 7.874 mil; PWR_RAILS 5.906 mil; USB 0.150 mm (production's settled rule); everything else 3 mil
CLASSES = [
    ('sdram', SDRAM, 76.2, {'L3-SIG': 100, 'L4-SIG': 100, 'Bottom Layer': 100}),
    ('v33', ['VCC3V3'], 76.2, {'L3-SIG': 1050, 'L4-SIG': 1050, 'Bottom Layer': 200}),
    ('u8', ['VU', 'USB5V0', 'VBATT'], 200, {'L3-SIG': 1100, 'L4-SIG': 1100}),
    ('v10', ['VCC1V0'], 150, {'L3-SIG': 500, 'L4-SIG': 500}),
    ('sw', ['NetL1_1', 'NetL2_1', 'NetL3_1'], 200, {}),
    ('rails', ['VCC1V8', 'VCCADC', 'GNDADC', 'FT-VCORE', 'FT-VPHY', 'FT-VPLL'], 150, {}),
    ('usb', ['USB_D_P', 'USB_D_N'], 150, {}),
]
W_SIG, CLEAR = 76.2, 90                                   # um
CLASS = ('(class %s %s\n      (circuit\n        (use_via %s)\n      )\n      (rule\n        (width %g)\n'
         '        (clearance %g)\n      )%s\n    )')
LAYER_RULE = '\n      (layer_rule "%s"\n        (rule\n          (width %g)\n        )\n      )'
EDGE, CORNER = 300, 1200            # um: keepout band inside the board edge, squares in the rounded (r 2.54) corners


def q(n):
    return '"%s"' % n if re.search(r'[^A-Za-z0-9_$]', n) else n


def main():
    wd = sys.argv[1]
    pcb = os.path.join(wd, 'feather.kicad_pcb')
    if '--export' not in sys.argv:
        # step 1; step 2 (--export) must be a separate run, because the process ends at SaveBoard
        os.makedirs(wd, exist_ok=True)
        app = wx.App(False)  # noqa: F841
        wx.Log.SetActiveTarget(wx.LogStderr())
        b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
        for t in b.GetTracks():
            t.SetLocked(True)
        pcbnew.SaveBoard(pcb, b)
        print('saved', pcb)          # KiCad's python exits 127 right after SaveBoard: the file is complete
        return
    b = pcbnew.LoadBoard(pcb)
    dsn = os.path.join(wd, 'feather.dsn')
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        sys.exit('DSN export failed')
    s = open(dsn).read()
    nets = set(str(n) for n in b.GetNetsByName().keys() if str(n))
    for lay in ('L2-GND', 'L5-VCC3V3'):
        a = '(layer "%s"\n      (type signal)' % lay
        assert a in s, lay
        s = s.replace(a, '(layer "%s"\n      (type power)' % lay)
    s = re.sub(r'\(via "Via\[0-5\]_600:300_um"[^)]*\)', '(via %s)' % ' '.join('"%s"' % v for v in VIAS), s, count=1)
    s = re.sub(r'(\(structure.*?\(rule\s*)\(width \d+\)\s*\(clearance \d+\)\s*\(clearance \d+ \(type smd_smd\)\)',
               r'\1(width %g)\n      (clearance %g)\n      (clearance %g (type smd_smd))' % (W_SIG, CLEAR, CLEAR), s,
               count=1, flags=re.S)
    # board-edge keepout: Freerouting keeps no clearance to the outline (run 3 put VBATT copper on the edge), so
    # every routing layer gets a 0.3 mm band inside the board box, plus squares in the four rounded corners
    bx = [float(v) for v in re.search(r'\(boundary\s*\(path pcb 0\s+([^)]*)\)', s).group(1).split()]
    xs, ys = bx[0::2], bx[1::2]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    E, R = EDGE, CORNER
    rects = [(x0, y0, x1, y0 + E), (x0, y1 - E, x1, y1), (x0, y0, x0 + E, y1), (x1 - E, y0, x1, y1),
             (x0, y0, x0 + R, y0 + R), (x1 - R, y0, x1, y0 + R), (x0, y1 - R, x0 + R, y1), (x1 - R, y1 - R, x1, y1)]
    ko = ''.join('    (keepout "" (rect "%s" %.1f %.1f %.1f %.1f))\n' % ((lay,) + r)
                 for lay in ('Top Layer', 'L3-SIG', 'L4-SIG', 'Bottom Layer') for r in rects)
    s = s.replace('    (via "Via[0-5]_350', ko + '    (via "Via[0-5]_350', 1)
    m = re.search(r'\(class kicad_default (.*?)\n\s*\(circuit', s, re.S)
    members = m.group(1).split()
    special = {n for _, ns, _, _ in CLASSES for n in ns}
    keep = [n for n in members if n.strip('"') not in special]
    def cls(name, ns, w, lay):
        lr = ''.join(LAYER_RULE % (l, v) for l, v in lay.items())
        return CLASS % (name, ' '.join(ns), ' '.join('"%s"' % v for v in VIAS), w, CLEAR, lr)
    start = s.index('(class kicad_default')
    end = s.index('(wiring')
    end = s.rindex(')', start, end)            # closes (network
    block = '    ' + cls('kicad_default', keep, W_SIG, {}) + '\n'
    for name, ns, w, lay in CLASSES:
        block += '    ' + cls(name, [q(n) for n in ns if n in nets], w, lay) + '\n'
    block += '  '
    s = s[:start] + block.lstrip() + s[end:]
    open(dsn, 'w').write(s)
    print('%s: %d nets default; %s' % (dsn, len(keep), ', '.join('%s %d' % (c, sum(n in nets for n in ns))
                                                               for c, _ns, _w, _l in CLASSES for ns in [_ns])))


if __name__ == '__main__':
    main()
