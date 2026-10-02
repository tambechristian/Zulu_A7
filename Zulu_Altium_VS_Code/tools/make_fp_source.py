# -*- coding: utf-8 -*-
"""Build the EAGLE .brd that seeds the Altium PCB library.

Step 1 of the board work. The old 6-layer board is NOT being reused as a board: it is read only
because its <libraries> section carries the drawn geometry of 19 of the 28 footprints the
schematic asks for, and Altium's Import Wizard plus Design > Make PCB Library turns placed
elements into a PcbLib. Everything else in the file -- placement, routing, stack, rules -- is
discarded with the scratch project.

Four corrections are made here, in EAGLE XML, so the library arrives right instead of being
hand-fixed in the PCB editor afterwards:

  A  ZULU-DIP37   44 pads -> 40. The top row is already correct (1-20). The bottom row is a solid
                  24-pad run 21-44; delete the four at x 36.83/34.29/31.75/29.21 (named 30-33)
                  to open the LiPo landing opposite the micro-USB, then renumber 34-44 -> 30-40.
                  X2's contactrefs in <signals> are transformed the same way so the file stays
                  internally consistent (a malformed file makes Altium spin and eat the window).
  B  XC7A35T-CPG236  lands HELD at 0.225 mm, NOT raised to UG475's 0.275 mm maximum. Taking
                  that maximum closes the 0.5 mm-pitch escape gap and makes the board
                  unroutable on any through-via stack; see the long note at section B.
  C  SPI-8_SOIC_150  copied in from zulu_a7.sch, where it is defined but never placed on the
                  board. This is the narrow-SOIC pattern U10 (93LC46BT-I/SN) has to move to; the
                  300-mil SOIC8 it sits on now is unsolderable.
  D  EVERLIGHT-19-337  = the VS-NRD8 pattern with the pads renumbered 1/2/3 -> 2/4/6 and
                  4/5/6 -> 1/3/5, which is how LD0 was re-specified on 2026-09-08.

C and D are placed as unconnected dummy elements off the board, because Make PCB Library harvests
placed components, not the library section.

Writes the patched copy to the scratchpad; nothing in the repo is touched.
"""
import io
import os
import re
import sys
import collections
import xml.etree.ElementTree as ET

SRC = r'C:\Users\tambe\Documents\Electronics\Zulu_A7\zulu_a7.brd'
SCH = r'C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu_Altrium\zulu_a7.sch'
OUT = (r'C:\Users\tambe\AppData\Local\Temp\claude'
       '\\C--Users-tambe-Documents-Electronics-Zulu-A7-Zulu-Altrium'
       '\\1e3d9c42-62fe-43bd-a170-baf7d18a0d60\\scratchpad\\fplib\\zulu_fp.brd')

DROP_X = [36.83, 34.29, 31.75, 29.21]                  # the LiPo landing, bottom row
ROW_Y = 1.27
RENUM = {str(o): str(o - 4) for o in range(34, 45)}    # 34..44 -> 30..40
EPS = 0.001

s = io.open(SRC, encoding='utf-8').read()
orig_len = len(s)


def one(pat, text, what, flags=re.S):
    m = re.search(pat, text, flags)
    assert m, 'not found: ' + what
    return m


# ------------------------------------------------------------------ A: ZULU-DIP37
zm = one(r'<package name="ZULU-DIP37".*?</package>', s, 'ZULU-DIP37 package')
z = zm.group(0)

pads = re.findall(r'<pad name="([^"]+)" x="([-\d.]+)" y="([-\d.]+)"[^/]*/>', z)
assert len(pads) == 44, 'expected 44 pads, found %d' % len(pads)

drop_names = set()
for n, x, y in pads:
    if abs(float(y) - ROW_Y) < EPS and any(abs(float(x) - d) < EPS for d in DROP_X):
        drop_names.add(n)
assert drop_names == {'30', '31', '32', '33'}, 'drop set is %s' % sorted(drop_names)


def drop_pad(m):
    return '' if m.group(1) in drop_names else m.group(0)


z2 = re.sub(r'<pad name="([^"]+)"[^/]*/>\n?', drop_pad, z)


def drop_rect(m):
    x1, y1, x2, y2 = (float(v) for v in m.group(1, 2, 3, 4))
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    if abs(cy - ROW_Y) < EPS and any(abs(cx - d) < EPS for d in DROP_X):
        return ''
    return m.group(0)


z2, nrect = re.subn(
    r'<rectangle x1="([-\d.]+)" y1="([-\d.]+)" x2="([-\d.]+)" y2="([-\d.]+)"[^/]*/>\n?',
    drop_rect, z2)
assert nrect == 44, 'saw %d rectangles' % nrect

# renumber in ONE pass: sequential replaces would collide on 40
z2 = re.sub(r'(<pad name=")([^"]+)(")',
            lambda m: m.group(1) + RENUM.get(m.group(2), m.group(2)) + m.group(3), z2)
s = s[:zm.start()] + z2 + s[zm.end():]


def fix_cref(m):
    pad = m.group(1)
    if pad in drop_names:
        return ''
    return m.group(0).replace('pad="%s"' % pad, 'pad="%s"' % RENUM.get(pad, pad))


s, ncref = re.subn(r'<contactref element="X2" pad="([^"]+)"[^/]*/>\n?', fix_cref, s)
assert ncref == 44, 'saw %d X2 contactrefs' % ncref

# ------------------------------------------------------------------ B: CPG236 lands
# HELD AT 0.225 mm DELIBERATELY -- do not "correct" this to UG475's 0.275.
#
# Table A-1 gives 0.275 mm as the MAXIMUM PCB solder land for CPG, and the prose recommends a 1:1
# ratio to the package's own 0.275 mm SMD opening "for improved board level reliability". Taking
# that maximum makes the board unroutable. At 0.5 mm pitch the gap between adjacent lands is
# 0.5 - land, and a 3 mil trace with 3.5 mil clearance either side needs 0.0762 + 2(0.09) =
# 0.2562 mm to pass between two of them:
#
#     land 0.225 -> gap 0.275 -> margin +0.0188 mm   escape closes
#     land 0.275 -> gap 0.225 -> margin -0.0312 mm   escape is geometrically impossible
#
# Rings 1 and 2 have to cross a populated row to reach the depopulated annulus whichever way they
# leave, so that gap is unavoidable, and no layer count fixes it. Only via-in-pad HDI would keep
# the 1:1 land, and PCBWay declined HDI in writing on 2026-08-27 ("would add the manufacturing a
# lot, so planA would be recommended"). 0.225 mm is 0.82:1, and PCBWay build BGA lands down to
# 0.2032 mm at pitches to 0.4 mm, so it is inside their process with 0.022 mm to spare.
#
# This was already settled in board/STACKUP.md on 2026-08-30; it was re-derived independently on
# 2026-09-10 and is recorded here because the EAGLE source looks like an error and is not one.
LAND = '0.225'
fm = one(r'<package name="XC7A35T-CPG236".*?</package>', s, 'CPG236 package')
held = len(re.findall(r'dx="%s" dy="%s"' % (LAND, LAND), fm.group(0)))
assert held == 238, 'CPG236 lands are not %s mm: %d of 238 match' % (LAND, held)

# ------------------------------------------------------------------ C + D: new packages
sch = io.open(SCH, encoding='utf-8').read()
spi = one(r'<package name="SPI-8_SOIC_150".*?</package>', sch, 'SPI-8_SOIC_150 in the .sch').group(0)

vs = one(r'<package name="VS-NRD8".*?</package>', s, 'VS-NRD8 package').group(0)
LED_MAP = {'1': '2', '2': '4', '3': '6', '4': '1', '5': '3', '6': '5'}
ever = vs.replace('<package name="VS-NRD8">', '<package name="EVERLIGHT-19-337">')
ever = re.sub(r'(<smd name=")([^"]+)(")',
              lambda m: m.group(1) + LED_MAP[m.group(2)] + m.group(3), ever)
assert sorted(re.findall(r'<smd name="([^"]+)"', ever)) == ['1', '2', '3', '4', '5', '6']

lm = one(r'<library name="ctambe">.*?</library>', s, 'ctambe library')
lib = lm.group(0)
close = lib.rindex('</packages>')
lib2 = lib[:close] + spi + '\n' + ever + '\n' + lib[close:]
s = s[:lm.start()] + lib2 + s[lm.end():]

new_pkgs = ['SPI-8_SOIC_150', 'EVERLIGHT-19-337']

# ------------------------------------------------- E: the footprints drawn from datasheets
# tools/new_footprints.json holds the land patterns extracted from the manufacturers' sheets and
# checked by a second pass; fp_emit turns each into an EAGLE <package>.
try:
    import fp_emit
except ImportError:                                   # running from outside tools/
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import fp_emit

drawn = []
jpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'new_footprints.json')
if os.path.exists(jpath):
    drawn = fp_emit.load(jpath)

if drawn:
    lm = one(r'<library name="ctambe">.*?</library>', s, 'ctambe library (2)')
    lib = lm.group(0)
    close = lib.rindex('</packages>')
    lib = lib[:close] + '\n'.join(fp_emit.package_xml(fp) for fp in drawn) + '\n' + lib[close:]
    s = s[:lm.start()] + lib + s[lm.end():]
    new_pkgs += [fp['name'] for fp in drawn]

# every added package needs a placed element, because Make PCB Library harvests placed components
em = one(r'<elements>', s, '<elements>', flags=0)
dummies = ''.join(
    '\n<element name="FPX%d" library="ctambe" package="%s" value="PATTERN" x="%d" y="%d"/>'
    % (n + 1, name, 100 + 15 * (n % 6), 40 + 15 * (n // 6))
    for n, name in enumerate(new_pkgs))
s = s[:em.end()] + dummies + s[em.end():]

# ------------------------------------------------------------------ verify
root = ET.fromstring(s.encode('utf-8'))            # well-formed, or this raises

pkgs = {p.get('name'): p for p in root.iter('package')}
dip = pkgs['ZULU-DIP37']
names = [p.get('name') for p in dip.findall('pad')]          # EAGLE stores pads in creation order
assert sorted(names, key=int) == [str(i) for i in range(1, 41)], 'DIP37 pad names: %s' % names

# the real check: every pad must land on the position the schematic's pin field assumes.
# Each row is cut 9 + landing + 11, both landings on the same four x values.
want = {}
for n in range(1, 10):
    want[str(n)] = (round(59.69 - 2.54 * (n - 1), 3), 24.13)
for n in range(10, 21):
    want[str(n)] = (round(26.67 - 2.54 * (n - 10), 3), 24.13)
for n in range(21, 30):
    want[str(n)] = (round(59.69 - 2.54 * (n - 21), 3), 1.27)
for n in range(30, 41):
    want[str(n)] = (round(26.67 - 2.54 * (n - 30), 3), 1.27)
got = {p.get('name'): (round(float(p.get('x')), 3), round(float(p.get('y')), 3))
       for p in dip.findall('pad')}
off = {k: (got[k], want[k]) for k in want if got[k] != want[k]}
assert not off, 'pads off the intended grid: %s' % off

assert len(dip.findall('rectangle')) == 40, 'rectangles: %d' % len(dip.findall('rectangle'))
assert all(e.get('dx') == LAND for e in pkgs['XC7A35T-CPG236'].findall('smd'))
assert len(pkgs['SPI-8_SOIC_150'].findall('smd')) == 8
assert len(pkgs['EVERLIGHT-19-337'].findall('smd')) == 6

rows = collections.defaultdict(list)
for p in dip.findall('pad'):
    rows[round(float(p.get('y')), 3)].append((round(float(p.get('x')), 3), p.get('name')))

by_name = {e.get('name'): e.get('package') for e in root.iter('element')}
bad = []
for sig in root.iter('signal'):
    for c in sig.findall('contactref'):
        pk = pkgs[by_name[c.get('element')]]
        have = ({p.get('name') for p in pk.findall('pad')} |
                {p.get('name') for p in pk.findall('smd')})
        if c.get('pad') not in have:
            bad.append((c.get('element'), c.get('pad'), by_name[c.get('element')]))
assert not bad, 'dangling contactrefs: %s' % bad[:10]

placed = collections.Counter(e.get('package') for e in root.iter('element'))
NEED = ['1X03-NOSILK', '2X06', '742C083', 'C0201', 'C0402', 'C0603', 'C0805', 'EVERLIGHT-19-337',
        'IND0603', 'IND2520', 'LED0603', 'MOLEX-105017-0001', 'R0201', 'R0402', 'SOIC-8_208MIL',
        'SOT23-3', 'SPI-8_SOIC_150', 'TSOPII-54', 'XC7A35T-CPG236', 'ZULU-DIP37']
NEED += [fp['name'] for fp in drawn]
missing = [n for n in NEED if not placed.get(n)]
assert not missing, 'not placed: %s' % missing

# each drawn footprint must arrive with exactly the pads its schematic symbol asks for
for fp in drawn:
    got = sorted(p.get('name') for p in pkgs[fp['name']].findall('smd'))
    got += sorted(p.get('name') for p in pkgs[fp['name']].findall('pad'))
    want_pads = sorted(p['name'] for p in fp['pads'])
    assert sorted(got) == want_pads, '%s: pads %s, wanted %s' % (fp['name'], sorted(got), want_pads)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
io.open(OUT, 'w', encoding='utf-8', newline='\n').write(s)


def runs_of(row):
    r = sorted(row, reverse=True)
    out, cur = [], [r[0]]
    for prev, nxt in zip(r, r[1:]):
        if abs(prev[0] - nxt[0] - 2.54) < EPS:
            cur.append(nxt)
        else:
            out.append(cur)
            cur = [nxt]
    out.append(cur)
    return out


print('ZULU-DIP37  44 pads -> %d' % len(names))
for y in sorted(rows, reverse=True):
    gs = runs_of(rows[y])
    print('   y=%-6s %2d pads in %d runs: %s' % (
        y, len(rows[y]), len(gs),
        '  |  '.join('%s-%s (x %.2f..%.2f)' % (g[0][1], g[-1][1], g[0][0], g[-1][0]) for g in gs)))
print('CPG236      238 lands held at %s mm (0.82:1, for the escape gap; see section B)' % LAND)
print('added       SPI-8_SOIC_150 (8 smd) and EVERLIGHT-19-337 (6 smd), each on a dummy element')
for fp in drawn:
    p = pkgs[fp['name']]
    print('drawn       %-20s %2d pads, body %s x %s mm' % (
        fp['name'], len(p.findall('smd')) + len(p.findall('pad')),
        fp['body']['dx'], fp['body']['dy']))
print('contactrefs X2 44 -> %d, and no dangling contactref anywhere in the file' % sum(
    1 for sig in root.iter('signal') for c in sig.findall('contactref')
    if c.get('element') == 'X2'))
print('%d packages defined, %d placed; all %d needed footprints present' % (
    len(pkgs), len(placed), len(NEED)))
print('%d chars -> %d' % (orig_len, len(s)))
print('wrote %s' % OUT)
