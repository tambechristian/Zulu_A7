# -*- coding: utf-8 -*-
"""Read every Width rule back out of the saved PcbDoc and check it against the
target table below.  Exit 0 on PASS, 1 otherwise.

    python tools/verify_widths.py            check
    python tools/verify_widths.py --dump     print every key of every Width rule

WHY THIS EXISTS.  Altium's Width rule DRC-checks only min and max; the
preferred width is router guidance.  The power rails must neck to 3 mil on
Top under the BGA (VCC3V3 only -- its balls C18, V6, V9 and V11 are the only
rail balls boxed by foreign nets on all four sides), so the thermal floor on
the inner layers has to live in the PER-LAYER table.

HOW ALTIUM STORES IT (learned from the first save, 2026-09-14; no Width rule
on this board had ever carried a non-uniform table before): SPARSE DELTA.
MINLIMIT / PREFEREDWIDTH / MAXLIMIT are the defaults for every layer, and a
layer gets a  <LAYER>_MINWIDTH / <LAYER>_PREFWIDTH / <LAYER>_MAXWIDTH  key
only where its value differs from that default, with <LAYER> one of
TOPLAYER, MIDLAYER1..MIDLAYER30, BOTTOMLAYER.  Which value becomes the
default is Altium's choice (it picked the inner preferred, not the scalar
the script wrote first), so never read MINLIMIT as "the min" -- resolve
every layer through effective() below.  MINIMP / MAXIMP / FAVIMP (50 ohm)
also appear; they belong to the impedance-driven mode, which is off.

Targets: docs/pwr_rail_widths.md (the 2026-09-14 decision record).
"""
import sys

import olefile

PCB = ("C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_Altrium/"
       "Imported zulu_a7.PrjPcb/zulu_a7.PcbDoc")
MIL = 0.0254
TOL = 0.0005            # mm; the file quantises to 1e-4 mil

# the 21 keys every uniform Width rule carried before 2026-09-14
UNIFORM_KEYS = {
    'COMMENT', 'DEFINEDBYLOGICALDOCUMENT', 'ENABLED', 'KEEPOUT', 'LAYER',
    'LAYERKIND', 'LOCKED', 'MAXLIMIT', 'MINLIMIT', 'NAME', 'NETSCOPE',
    'POLYGONOUTLINE', 'PREFEREDWIDTH', 'PRIORITY', 'RULEKIND',
    'SCOPE1EXPRESSION', 'SCOPE2EXPRESSION', 'SELECTION', 'UNIONINDEX',
    'UNIQUEID', 'USERROUTED',
}

# ---- the target ------------------------------------------------------------
# Top: only VCC3V3 keeps the 3 mil neck.  Inner mins are the IPC-2221 10 C
# widths at MAX current on 0.0152 mm copper, rounded UP to 0.05 mm (VCC3V3
# 662 mA -> 1.0187 -> 1.05; VU 697 mA -> 1.0937 -> 1.10; VCC1V0 367 mA ->
# 0.4515 -> 0.50).  Outer mins are the 10 C outer widths (0.170 / 0.183 ->
# 0.20) or the 0.15 mm etch floor where the thermal width is smaller.
# Preferred is pad-entry guidance only: 0.20 under the 0.225 U1 land and the
# 0.28 LQFP pad, 0.30 at the 0.300 mm 0201 pads, 0.20 at U8's 0.24 VQFN pads.
EXPECT = {
    # 2026-09-14 (later): the SDRAM bus rule, docs/sdram_bus_widths.md.  Top keeps the 3 mil
    # escape (preferred = min, the router never necks by itself); L3/L4/Bottom neck at 0.10
    # (54 ohm), lay 0.125 (49.5 ohm = the 8 mA driver), cap at 0.15 (45 ohm).
    'Width_SDRAM': dict(scope="InNetClass('SDRAM_DATA') Or InNetClass('SDRAM_ADDR') Or InNetClass('SDRAM_CTRL')", prio=1, layers={
        'Top': (0.0762, 0.0762, 0.15), 'Mid1': (0.10, 0.125, 0.15),
        'Mid2': (0.10, 0.125, 0.15),   'Bottom': (0.10, 0.125, 0.15)}),
    'Width_PWR_VCC3V3': dict(scope="InNet('VCC3V3')", prio=2, layers={
        'Top': (0.0762, 0.20, 1.50), 'Mid1': (1.05, 1.05, 1.50),
        'Mid2': (1.05, 1.05, 1.50),  'Bottom': (0.20, 0.30, 1.50)}),
    'Width_PWR_U8': dict(scope="InNet('VU') Or InNet('USB5V0') Or InNet('VBATT')", prio=3, layers={
        'Top': (0.20, 0.30, 1.50), 'Mid1': (1.10, 1.10, 1.50),
        'Mid2': (1.10, 1.10, 1.50), 'Bottom': (0.20, 0.20, 1.50)}),
    'Width_PWR_VCC1V0': dict(scope="InNet('VCC1V0')", prio=4, layers={
        'Top': (0.15, 0.20, 1.50), 'Mid1': (0.50, 0.50, 1.50),
        'Mid2': (0.50, 0.50, 1.50), 'Bottom': (0.15, 0.30, 1.50)}),
    'Width_PWR_RAILS': dict(scope="InNetClass('PWR_RAILS')", prio=6, layers={
        'Top': (0.15, 0.20, 1.00), 'Mid1': (0.15, 0.20, 1.00),
        'Mid2': (0.15, 0.20, 1.00), 'Bottom': (0.15, 0.30, 1.00)}),
}

# the two rules that must NOT have moved, scalar form
UNTOUCHED = {
    'Width_PWR_SWITCH': dict(prio=5, minlimit=0.2, pref=0.5, maxlimit=1.5),
    'Width':            dict(prio=7, minlimit=0.0762, pref=0.0762, maxlimit=0.5),
}

# Altium's layer prefixes for this board's four routing layers
LAYER_PREFIX = {'Top': 'TOPLAYER', 'Mid1': 'MIDLAYER1', 'Mid2': 'MIDLAYER2', 'Bottom': 'BOTTOMLAYER'}
FIELD = (('min', 'MINWIDTH', 'MINLIMIT'), ('pref', 'PREFWIDTH', 'PREFEREDWIDTH'), ('max', 'MAXWIDTH', 'MAXLIMIT'))


def effective(kv, layer, field):
    """the value DRC uses on this layer: the per-layer override if present, else the default"""
    for name, suffix, default in FIELD:
        if name == field:
            return mm(kv.get('%s_%s' % (LAYER_PREFIX[layer], suffix), kv.get(default)))
    raise KeyError(field)


def mm(v):
    """'15.748mil' / '0.5mm' / '' -> mm or None"""
    if not v:
        return None
    v = v.strip()
    if v.endswith('mil'):
        return float(v[:-3]) * MIL
    if v.endswith('mm'):
        return float(v[:-2])
    return float(v) * MIL      # Altium's bare numbers are mils


# ---- the SDRAM clearance rules, L3/L4 only ---------------------------------
CLEARANCE_EXPECT = {
    'Clearance_SDRAM_CLK':   dict(prio=1, gap=0.20, scope="InNet('SDRAM-CLK') And (OnLayer('L3-SIG') Or OnLayer('L4-SIG'))"),
    'Clearance_SDRAM_INNER': dict(prio=2, gap=0.10, scope="(InNetClass('SDRAM_DATA') Or InNetClass('SDRAM_ADDR') Or InNetClass('SDRAM_CTRL')) And (OnLayer('L3-SIG') Or OnLayer('L4-SIG'))"),
    'Clearance':             dict(prio=3, gap=0.09, scope='All'),
}


def clearance_rules():
    f = olefile.OleFileIO(PCB)
    d = f.openstream('Rules6/Data').read().decode('latin-1', 'replace')
    f.close()
    out = []
    for r in d.split(chr(0)):
        if 'RULEKIND=Clearance|' not in r + '|':
            continue
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        if kv.get('RULEKIND') == 'Clearance':
            out.append(kv)
    return out


def width_rules():
    f = olefile.OleFileIO(PCB)
    d = f.openstream('Rules6/Data').read().decode('latin-1', 'replace')
    f.close()
    out = []
    for r in d.split(chr(0)):
        if 'RULEKIND=Width' not in r:
            continue
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        out.append(kv)
    return out


def main():
    rules = width_rules()
    if '--dump' in sys.argv:
        for kv in rules:
            print('=== %s  (priority %s) ===' % (kv.get('NAME'), kv.get('PRIORITY')))
            for k in sorted(kv):
                tag = '' if k in UNIFORM_KEYS else '   <-- NEW'
                print('   %-34s %s%s' % (k, kv[k], tag))
        return 0

    fails = []
    byname = {kv.get('NAME'): kv for kv in rules}
    print('FILE: %s' % PCB)
    print('Width rules in file: %s' % ', '.join(
        '%s(p%s)' % (kv.get('NAME'), kv.get('PRIORITY')) for kv in
        sorted(rules, key=lambda k: int(k.get('PRIORITY', 99)))))
    if len(rules) != 7:
        fails.append('expected 7 Width rules, file has %d' % len(rules))

    def chk(name, label, got, exp):
        ok = got is not None and abs(got - exp) <= TOL
        print('   %-32s %-10s want %-8s %s' % (
            label, ('%.4f' % got) if got is not None else '-', '%.4f' % exp, 'OK' if ok else 'BAD'))
        if not ok:
            fails.append('%s %s got %r want %r' % (name, label, got, exp))

    for name, want in EXPECT.items():
        kv = byname.get(name)
        print(chr(10) + '[%s]' % name)
        if kv is None:
            print('   MISSING')
            fails.append('%s missing' % name)
            continue
        if kv.get('SCOPE1EXPRESSION') != want['scope']:
            print('   scope %r != %r' % (kv.get('SCOPE1EXPRESSION'), want['scope']))
            fails.append('%s scope' % name)
        else:
            print('   scope                            %s  OK' % want['scope'])
        if int(kv.get('PRIORITY', -1)) != want['prio']:
            print('   priority %s != %d' % (kv.get('PRIORITY'), want['prio']))
            fails.append('%s priority %s want %d' % (name, kv.get('PRIORITY'), want['prio']))
        else:
            print('   priority                         %d  OK' % want['prio'])
        if kv.get('ENABLED') != 'TRUE':
            fails.append('%s not enabled' % name)

        new_keys = sorted(k for k in kv if k not in UNIFORM_KEYS and not k.endswith('IMP'))
        if not new_keys:
            print('   NO per-layer keys in the record - the layer table did NOT persist')
            fails.append('%s carries no per-layer keys' % name)
        for L, (emin, epref, emax) in want['layers'].items():
            chk(name, '%s min' % L, effective(kv, L, 'min'), emin)
            chk(name, '%s pref' % L, effective(kv, L, 'pref'), epref)
            chk(name, '%s max' % L, effective(kv, L, 'max'), emax)
        print('   defaults MINLIMIT / PREFEREDWIDTH / MAXLIMIT = %s / %s / %s;  %d per-layer overrides'
              % (kv.get('MINLIMIT'), kv.get('PREFEREDWIDTH'), kv.get('MAXLIMIT'), len(new_keys)))

    for name, want in UNTOUCHED.items():
        kv = byname.get(name)
        print(chr(10) + '[%s]  must be untouched' % name)
        if kv is None:
            fails.append('%s missing' % name)
            print('   MISSING')
            continue
        chk(name, 'MINLIMIT', mm(kv.get('MINLIMIT')), want['minlimit'])
        chk(name, 'PREFEREDWIDTH', mm(kv.get('PREFEREDWIDTH')), want['pref'])
        chk(name, 'MAXLIMIT', mm(kv.get('MAXLIMIT')), want['maxlimit'])
        if int(kv.get('PRIORITY', -1)) != want['prio']:
            fails.append('%s priority %s want %d' % (name, kv.get('PRIORITY'), want['prio']))
            print('   priority %s != %d' % (kv.get('PRIORITY'), want['prio']))
        else:
            print('   priority                         %d  OK' % want['prio'])
        extra = sorted(k for k in kv if k not in UNIFORM_KEYS)
        if extra:
            fails.append('%s gained keys %s' % (name, extra))
            print('   GAINED keys: %s' % extra)

    cls = {kv.get('NAME'): kv for kv in clearance_rules()}
    print(chr(10) + '[Clearance rules]  %s' % ', '.join('%s(p%s)' % (kv.get('NAME'), kv.get('PRIORITY')) for kv in sorted(cls.values(), key=lambda k: int(k.get('PRIORITY', 99)))))
    if len(cls) != len(CLEARANCE_EXPECT):
        fails.append('expected %d Clearance rules, file has %d' % (len(CLEARANCE_EXPECT), len(cls)))
    for name, want in CLEARANCE_EXPECT.items():
        kv = cls.get(name)
        if kv is None:
            print('   %-24s MISSING' % name); fails.append('%s missing' % name); continue
        chk(name, '%s GAP' % name, mm(kv.get('GAP')), want['gap'])
        chk(name, '%s GENERICCLEARANCE' % name, mm(kv.get('GENERICCLEARANCE')), want['gap'])
        if int(kv.get('PRIORITY', -1)) != want['prio']:
            fails.append('%s priority %s want %d' % (name, kv.get('PRIORITY'), want['prio']))
            print('   %-24s priority %s != %d' % (name, kv.get('PRIORITY'), want['prio']))
        if kv.get('SCOPE1EXPRESSION') != want['scope']:
            fails.append('%s scope %r' % (name, kv.get('SCOPE1EXPRESSION')))
            print('   %-24s scope %r != %r' % (name, kv.get('SCOPE1EXPRESSION'), want['scope']))
        if kv.get('NETSCOPE') != 'DifferentNets':
            fails.append('%s NETSCOPE %r (want DifferentNets)' % (name, kv.get('NETSCOPE')))
            print('   %-24s NETSCOPE %r' % (name, kv.get('NETSCOPE')))

    print(chr(10) + '=' * 70)
    if fails:
        print('FAIL -- %d problem(s):' % len(fails))
        for x in fails:
            print('  * ' + x)
        return 1
    print('PASS -- every Width and Clearance rule matches the target')
    return 0


if __name__ == '__main__':
    sys.exit(main())
