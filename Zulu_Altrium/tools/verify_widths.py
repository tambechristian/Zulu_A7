# -*- coding: utf-8 -*-
"""Read every Width rule back out of the saved PcbDoc and check it against the
target table below.  Exit 0 on PASS, 1 otherwise.

    python tools/verify_widths.py            check
    python tools/verify_widths.py --dump     print every key of every Width rule

WHY THIS EXISTS.  Altium's Width rule DRC-checks only min and max; the
preferred width is router guidance.  The power rails must neck to 3 mil on
Top under the BGA (VCC3V3 only -- its balls C18, V6, V9 and V11 are the only
rail balls boxed by foreign nets on all four sides), so the thermal floor on
the inner layers has to live in the PER-LAYER table.  Before 2026-09-14 no
Width rule on this board had ever carried a non-uniform table, so the keys
Altium writes for one were unknown: run --dump after the first save and put
the real spellings in LAYER_KEYS if the guess is wrong.  If the four rail
rules carry NO key beyond the 21 a uniform rule has, the table did not
persist -- STOP, do not route against it.

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
    'Width_PWR_VCC3V3': dict(scope="InNet('VCC3V3')", prio=1, layers={
        'Top': (0.0762, 0.20, 1.50), 'Mid1': (1.05, 1.05, 1.50),
        'Mid2': (1.05, 1.05, 1.50),  'Bottom': (0.20, 0.30, 1.50)}),
    'Width_PWR_U8': dict(scope="InNet('VU') Or InNet('USB5V0') Or InNet('VBATT')", prio=2, layers={
        'Top': (0.20, 0.30, 1.50), 'Mid1': (1.10, 1.10, 1.50),
        'Mid2': (1.10, 1.10, 1.50), 'Bottom': (0.20, 0.20, 1.50)}),
    'Width_PWR_VCC1V0': dict(scope="InNet('VCC1V0')", prio=3, layers={
        'Top': (0.15, 0.20, 1.50), 'Mid1': (0.50, 0.50, 1.50),
        'Mid2': (0.50, 0.50, 1.50), 'Bottom': (0.15, 0.30, 1.50)}),
    'Width_PWR_RAILS': dict(scope="InNetClass('PWR_RAILS')", prio=5, layers={
        'Top': (0.15, 0.20, 1.00), 'Mid1': (0.15, 0.20, 1.00),
        'Mid2': (0.15, 0.20, 1.00), 'Bottom': (0.15, 0.30, 1.00)}),
}

# the two rules that must NOT have moved, scalar form
UNTOUCHED = {
    'Width_PWR_SWITCH': dict(prio=4, minlimit=0.2, pref=0.5, maxlimit=1.5),
    'Width':            dict(prio=6, minlimit=0.0762, pref=0.0762, maxlimit=0.5),
}

# the per-layer keys as the file spells them -- A GUESS until the first --dump
LAYER_KEYS = {
    'Top':    ('MINWIDTH_TOP',    'PREFEREDWIDTH_TOP',    'MAXWIDTH_TOP'),
    'Mid1':   ('MINWIDTH_MID1',   'PREFEREDWIDTH_MID1',   'MAXWIDTH_MID1'),
    'Mid2':   ('MINWIDTH_MID2',   'PREFEREDWIDTH_MID2',   'MAXWIDTH_MID2'),
    'Bottom': ('MINWIDTH_BOTTOM', 'PREFEREDWIDTH_BOTTOM', 'MAXWIDTH_BOTTOM'),
}


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
    if len(rules) != 6:
        fails.append('expected 6 Width rules, file has %d' % len(rules))

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

        new_keys = sorted(k for k in kv if k not in UNIFORM_KEYS)
        if not new_keys:
            print('   NO per-layer keys in the record - the layer table did NOT persist')
            fails.append('%s carries no per-layer keys' % name)
        lay = want['layers']
        for L, (kmin, kpref, kmax) in LAYER_KEYS.items():
            emin, epref, emax = lay[L]
            chk(name, '%s min' % L, mm(kv.get(kmin)), emin)
            chk(name, '%s pref' % L, mm(kv.get(kpref)), epref)
            chk(name, '%s max' % L, mm(kv.get(kmax)), emax)
        # the uniform write-through values; they must not be TIGHTER than the table
        lo = min(v[0] for v in lay.values())
        hi = max(v[2] for v in lay.values())
        gmin, gmax = mm(kv.get('MINLIMIT')), mm(kv.get('MAXLIMIT'))
        print('   %-32s %-10s (table floor %.4f)' % ('MINLIMIT', '%.4f' % gmin if gmin is not None else '-', lo))
        print('   %-32s %-10s (table ceiling %.4f)' % ('MAXLIMIT', '%.4f' % gmax if gmax is not None else '-', hi))
        if gmin is None or gmin > lo + TOL:
            fails.append('%s MINLIMIT %r tighter than table floor %r' % (name, gmin, lo))
        if gmax is None or gmax < hi - TOL:
            fails.append('%s MAXLIMIT %r tighter than table ceiling %r' % (name, gmax, hi))
        if new_keys:
            unknown = [k for k in new_keys if k not in sum(LAYER_KEYS.values(), ())]
            if unknown:
                print('   keys not in LAYER_KEYS (fix the table above): %s' % unknown)

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

    print(chr(10) + '=' * 70)
    if fails:
        print('FAIL -- %d problem(s):' % len(fails))
        for x in fails:
            print('  * ' + x)
        return 1
    print('PASS -- every Width rule matches the target')
    return 0


if __name__ == '__main__':
    sys.exit(main())
