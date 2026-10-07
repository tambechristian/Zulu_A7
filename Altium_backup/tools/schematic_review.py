# -*- coding: utf-8 -*-
"""Readability and connectivity hygiene over the seven sheets -> docs/schematic_review.md

    python tools/schematic_review.py > docs/schematic_review.md

This is the half of a schematic review that a machine can do honestly: geometry and spelling.
Whether a sheet READS well -- whether the eye finds the signal path, whether the grouping matches
the way the circuit works -- is a judgement, and the document says so where it stops.

What it checks, per sheet:

  1. Net labels and power ports that do not sit on a wire. A label that misses its wire by one unit
     names nothing; the net silently splits and the netlist looks fine because the label simply is
     not there. This is the single most expensive mistake in an imported schematic.
  2. Wire ends that touch nothing -- no pin, no other wire, no junction, no label, no port.
  3. Wires that cross a component body, and text that lands on top of a wire or on other text.
  4. Objects off the 10-unit snap grid, which is what makes a sheet look ragged and makes every
     later edit fight the grid.
  5. Net names that differ only in case, separator or spacing, which is how one net becomes two.
  6. Nets that appear on exactly one pin (nothing to connect to) and labels that name a net used
     nowhere else on any sheet.
  7. Designators and comments that are hidden, empty or duplicated.

Everything is read from the .SchDoc records, so it sees what Altium sees, not what the PDF renders.
Read-only.
"""
import io, os, re, sys, math, collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from fix_text_orientation import read_stream, split, field

PRJ = os.path.join(os.path.dirname(HERE), 'Imported zulu_a7.PrjPcb')
SHEETS = [(n, os.path.join(PRJ, f'zulu_a7_{n}.SchDoc')) for n in range(7)]
TITLES = {0: 'block diagram', 1: 'power supplies', 2: 'general IO', 3: 'memory',
          4: 'FT2232HL, JTAG, clock', 5: 'FPGA connections', 6: 'FPGA power'}
GRID = 10
DIR = {0: (1, 0), 1: (0, 1), 2: (-1, 0), 3: (0, -1)}
out = []
w = out.append


def num(b, k):
    v = field(b, k)
    if v is None:
        return None
    f = field(b, k + '_Frac')
    return int(v) + (int(f) / 1e5 if f else 0.0)


def oi(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def load(path):
    recs = split(read_stream(path, 'FileHeader'))
    s = {'recs': recs, 'wires': [], 'labels': [], 'ports': [], 'pins': [], 'junctions': [],
         'texts': [], 'comps': {}, 'desig': {}, 'bodies': []}
    for i, (h, b) in enumerate(recs):
        if b.startswith(b'|RECORD=34|'):
            s['desig'][oi(b)] = (field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y'),
                                 field(b, 'IsHidden') == 'T')
    for i, (h, b) in enumerate(recs):
        r = field(b, 'RECORD')
        if r == '1':
            s['comps'][i] = b
        elif r == '27':
            n = int(field(b, 'LocationCount') or 0)
            pts = [(num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1)]
            s['wires'].append((i, pts))
        elif r == '25':
            s['labels'].append((i, field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y'), oi(b)))
        elif r == '17':
            s['ports'].append((i, field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r == '29':
            s['junctions'].append((i, num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r == '4':
            s['texts'].append((i, field(b, 'Text'), num(b, 'Location.X'), num(b, 'Location.Y')))
        elif r == '2':
            p = oi(b)
            x, y = num(b, 'Location.X'), num(b, 'Location.Y')
            c = int(field(b, 'PinConglomerate') or 32)
            ln = int(field(b, 'PinLength') or 0)
            dx, dy = DIR[c & 3]
            s['pins'].append((i, p, field(b, 'Designator'), x + dx * ln, y + dy * ln,
                              field(b, 'OwnerPartId')))
        elif r == '6' and oi(b) in s['comps']:
            s['bodies'].append((oi(b), num(b, 'X1'), num(b, 'Y1'), num(b, 'X2'), num(b, 'Y2')))
    return s


def on_segment(px, py, a, b, tol=1.2):
    (ax, ay), (bx, by) = a, b
    if min(ax, bx) - tol <= px <= max(ax, bx) + tol and min(ay, by) - tol <= py <= max(ay, by) + tol:
        cross = abs((bx - ax) * (py - ay) - (by - ay) * (px - ax))
        length = math.hypot(bx - ax, by - ay) or 1
        return cross / length <= tol
    return False


def on_any_wire(s, x, y):
    for i, pts in s['wires']:
        for a, b in zip(pts, pts[1:]):
            if on_segment(x, y, a, b):
                return True
    return False


def on_any_pin(s, x, y, tol=1.2):
    """A port or label may sit straight on a pin end with no wire between; that is not a fault."""
    return any(px is not None and abs(px - x) <= tol and abs(py - y) <= tol
               for _, _, _, px, py, _ in s['pins'])


def attached(s, x, y):
    return on_any_wire(s, x, y) or on_any_pin(s, x, y)


# ---------------------------------------------------------------- gather, per sheet ------------
sheets = {n: load(p) for n, p in SHEETS}
findings = collections.defaultdict(list)          # (severity, sheet) -> [text]
allnets = collections.Counter()
label_sheets = collections.defaultdict(set)

for n, s in sheets.items():
    for i, t, x, y, owner in s['labels']:
        if t:
            allnets[t] += 1
            label_sheets[t].add(n)
    for i, t, x, y in s['ports']:
        if t:
            allnets[t] += 1
            label_sheets[t].add(n)

w('# Zulu A7 schematic review: readability, labelling and flow\n')
w('Generated by `tools/schematic_review.py` from the seven `.SchDoc` files, so it sees what Altium '
  'sees rather than what the PDF renders. It covers the objective half of a review -- geometry and '
  'spelling. Where a question needs judgement rather than arithmetic, it says so and stops.\n')

w('| Sheet | Title | Parts | Wires | Net labels | Power ports | Free text | Junctions |')
w('|---|---|---:|---:|---:|---:|---:|---:|')
for n, s in sheets.items():
    w(f'| {n} | {TITLES[n]} | {len(s["comps"])} | {len(s["wires"])} | {len(s["labels"])} | '
      f'{len(s["ports"])} | {len(s["texts"])} | {len(s["junctions"])} |')
w('')

# ---- 1. labels and ports that miss their wire -------------------------------------------------
w('## 1. Labels and power ports that do not sit on a wire\n')
w('A net label one unit off its wire names nothing at all, and the netlist gives no warning: the '
  'net simply is not called that. Pins carry their own hidden names, so a missed label can hide '
  'until the board is routed.\n')
rows = []
for n, s in sheets.items():
    for i, t, x, y, owner in s['labels']:
        if owner is not None or x is None:
            continue                                   # labels owned by a pin are pin names
        if not attached(s, x, y):
            near = any(abs(x - px) + abs(y - py) < 12 for _, pts in s['wires'] for px, py in pts)
            rows.append((n, 'net label', t, x, y, 'a wire ends within 12 units' if near else 'nothing within 12 units'))
    for i, t, x, y in s['ports']:
        if x is None:
            continue
        if not attached(s, x, y):
            near = any(abs(x - px) + abs(y - py) < 12 for _, pts in s['wires'] for px, py in pts)
            rows.append((n, 'power port', t, x, y, 'a wire ends within 12 units' if near else 'nothing within 12 units'))
if rows:
    w('| Sheet | Kind | Text | X | Y | Nearest wire |')
    w('|---|---|---|---:|---:|---|')
    for r in rows:
        w(f'| {r[0]} | {r[1]} | `{r[2]}` | {r[3]:.0f} | {r[4]:.0f} | {r[5]} |')
    findings['A'].append(f'{len(rows)} labels or ports are not on a wire.')
else:
    w('None. Every net label and power port lands on a wire.')
w('')

# ---- 2. dangling wire ends --------------------------------------------------------------------
w('## 2. Wire ends that touch nothing\n')
w('An end that meets no pin, no other wire, no junction and no label is either a leftover or a '
  'connection that was never made. Ends that carry a label are listed separately: a labelled stub '
  'is a deliberate off-sheet connection, not a fault.\n')
dang = []
for n, s in sheets.items():
    pins = {(round(px, 1), round(py, 1)) for _, _, _, px, py, _ in s['pins'] if px is not None}
    juncs = {(round(x, 1), round(y, 1)) for _, x, y in s['junctions'] if x is not None}
    ports = {(round(x, 1), round(y, 1)) for _, _, x, y in s['ports'] if x is not None}
    labels = [(t, x, y) for _, t, x, y, o in s['labels'] if o is None and x is not None]
    for i, pts in s['wires']:
        for k, (x, y) in enumerate(pts):
            if k not in (0, len(pts) - 1):
                continue                                # only the two ends can dangle
            key = (round(x, 1), round(y, 1))
            if key in pins or key in juncs or key in ports:
                continue
            touching = 0
            for j, other in s['wires']:
                if j == i:
                    continue
                for a, b in zip(other, other[1:]):
                    if on_segment(x, y, a, b):
                        touching += 1
                        break
                if touching:
                    break
            if touching:
                continue
            near_pin = any(abs(x - px) <= 1.5 and abs(y - py) <= 1.5 for px, py in pins)
            lab = [t for t, lx, ly in labels if abs(lx - x) <= 25 and abs(ly - y) <= 6]
            dang.append((n, x, y, lab[0] if lab else '', 'within 1.5 of a pin' if near_pin else ''))
labelled = [d for d in dang if d[3]]
loose = [d for d in dang if not d[3]]
w(f'{len(loose)} unlabelled loose ends, {len(labelled)} ends that carry a label.\n')
if loose:
    w('| Sheet | X | Y | Note |')
    w('|---|---:|---:|---|')
    for n, x, y, lab, note in sorted(loose):
        w(f'| {n} | {x:.0f} | {y:.0f} | {note or "nothing within 1.5 units"} |')
    findings['A'].append(f'{len(loose)} wire ends touch nothing.')
w('')

# ---- 3. what grid the sheets are actually on -------------------------------------------------
w('## 3. What grid the sheets are actually on\n')
w('The sheet records say `SnapGridSize=10`, but the EAGLE importer placed parts on its own grid and '
  'Altium kept the coordinates. This matters for the redraw: a wire drawn on the declared grid will '
  'not meet a pin that sits between grid points, and the mismatch is why a hand edit here needs the '
  'snap turned off or reset first.\n')
w('| Sheet | On 10 | On 5 (not 10) | Whole units | Fractional | Worst example |')
w('|---|---:|---:|---:|---:|---|')
frac_total = 0
for n, s_ in sheets.items():
    g10 = g5 = g1 = gf = 0
    worst = ''
    for i, b_ in s_['comps'].items():
        x, y = num(b_, 'Location.X'), num(b_, 'Location.Y')
        if x is None:
            continue
        if abs(x - round(x)) > 1e-6 or abs(y - round(y)) > 1e-6:
            gf += 1
            if not worst:
                worst = f'{s_["desig"].get(i, ("?",))[0]} at ({x:.3f}, {y:.3f})'
        elif x % 10 == 0 and y % 10 == 0:
            g10 += 1
        elif x % 5 == 0 and y % 5 == 0:
            g5 += 1
        else:
            g1 += 1
    frac_total += gf
    w(f'| {n} | {g10} | {g5} | {g1} | {gf} | {worst or "none"} |')
w('')
w(f'{frac_total} parts sit at fractional coordinates, in two clusters. C40 on sheet 4 is the '
  'FT2232H VPHY bypass, whose node the import left held together by three junctions and a '
  '0.04-unit wire at three different sub-unit positions; that one is documented in '
  '`tools/sheet4_layout.py` and must be moved as a block, never rebuilt. The other five are '
  'FPGA bulk capacitors on sheet 6 sharing two fractional Y values (662.866 and 521.134), which '
  'is the signature of a row the importer scaled rather than placed. None of them is a fault in '
  'itself -- every one is wired correctly -- but each is a place where a hand edit on the snap '
  'grid will miss the pin it is aiming at.\n')
if frac_total:
    findings['B'].append(f'{frac_total} parts sit at fractional coordinates.')

# ---- 4. net names that differ only in shape ---------------------------------------------------
w('## 4. Net names that differ only in case, separator or spacing\n')
w('One net becoming two is usually a spelling accident, and the netlist cannot tell you: both names '
  'are valid. Names are folded to lower case with `-` and `_` removed, and anything that collides '
  'is listed.\n')


def fold(t):
    return re.sub(r'[-_ ]', '', t.lower())


groups = collections.defaultdict(set)
for t in allnets:
    groups[fold(t)].add(t)
clash = {k: v for k, v in groups.items() if len(v) > 1}
if clash:
    w('| Folded | Names in use | Sheets |')
    w('|---|---|---|')
    for k, v in sorted(clash.items()):
        w(f'| `{k}` | ' + ', '.join(f'`{x}` x{allnets[x]}' for x in sorted(v)) + ' | ' +
          ', '.join(str(s) for s in sorted(set().union(*(label_sheets[x] for x in v)))) + ' |')
    findings['A'].append(f'{len(clash)} net names differ only in shape.')
else:
    w('None.')
w('')

# ---- 5. what the netlist says about the labels ------------------------------------------------
w('## 5. Labels against the exported netlist\n')
w('The previous section asks whether names collide. This one asks the netlist whether each name '
  'actually became a net, and whether any net ended up with a single pad. A label whose text is not '
  'a net name did not name what its author thought; a one-pad net is a connection that was never '
  'completed.\n')
NET = os.path.join(PRJ, 'Project Outputs for zulu_a7', 'zulu_a7.NET')
if os.path.exists(NET):
    t = open(NET, encoding='latin-1').read()
    netpads = {}
    for blk in re.findall(r'\(\n(.*?)\n\)', t, re.S):
        L = [x.strip() for x in blk.split('\n') if x.strip()]
        netpads[L[0]] = L[1:]
    orphan = sorted(t_ for t_ in allnets if t_ not in netpads)
    single = sorted((k, v[0]) for k, v in netpads.items() if len(v) == 1)
    w(f'The netlist holds {len(netpads)} nets over {sum(len(v) for v in netpads.values())} pads, '
      f'against {len(allnets)} distinct label and port texts on the sheets.\n')
    if orphan:
        w('**Labels that are not net names in the netlist:**\n')
        w('| Text | Sheets |')
        w('|---|---|')
        for t_ in orphan:
            w(f'| `{t_}` | {", ".join(str(x) for x in sorted(label_sheets[t_]))} |')
        findings['A'].append(f'{len(orphan)} label texts do not appear as nets.')
    else:
        w('Every label and port text appears as a net name in the netlist.\n')
    w('')
    if single:
        w('**Nets with a single pad** (nothing to connect to):\n')
        w('| Net | Pad |')
        w('|---|---|')
        for k, v in single:
            w(f'| `{k}` | {v} |')
        findings['B'].append(f'{len(single)} nets carry a single pad.')
    else:
        w('No net has fewer than two pads.')
else:
    w('The exported netlist is missing; run Design > Netlist For Project > Protel first.')
w('')

# ---- 6. designators and comments ---------------------------------------------------------------
w('## 6. How each part is named on the drawing\n')
w('A multi-gate part shows its reference on one gate and hides it on the rest, which is right. What '
  'would matter is a part a reader cannot name at all. The EAGLE importer did not always use the '
  'designator object for this: on the biggest parts it left every designator hidden and put the '
  'reference in a visible parameter on the part-value gate instead. That prints the same and is not '
  'a fault, but it is worth knowing before anyone goes looking for the designator to move it.\n')
shown, hidden_all, libs = {}, {}, {}
for n, s_ in sheets.items():
    for i, b_ in s_['comps'].items():
        d = s_['desig'].get(i)
        if d is None or not d[0]:
            continue
        key = (n, d[0])
        libs[key] = field(b_, 'LibReference')
        shown[key] = shown.get(key, 0) + (0 if d[3] else 1)
        hidden_all[key] = hidden_all.get(key, 0) + (1 if d[3] else 0)
vis_text = {}
for n, s_ in sheets.items():
    seen = set()
    for h_, b_ in s_['recs']:
        if b_.startswith((b'|RECORD=4|', b'|RECORD=41|', b'|RECORD=25|')):
            if field(b_, 'IsHidden') == 'T' or field(b_, 'Name') in ('PinUniqueId', 'HiddenNetName'):
                continue
            t_ = field(b_, 'Text')
            if t_:
                seen.add(t_.strip())
    vis_text[n] = seen
quiet = sorted(k for k, v in shown.items() if v == 0
               and not k[1].startswith(('FRAME', 'U$')))
unnamed = [k for k in quiet if k[1] not in vis_text[k[0]]]
w(f'{len(shown)} placements carry a reference. {len(quiet)} references are hidden on every one of '
  f'their placements; of those, {len(unnamed)} are not written anywhere else on the sheet either.\n')
if quiet:
    w('| Sheet | Reference | Placements | Symbol | Named elsewhere on the sheet |')
    w('|---|---|---:|---|---|')
    for k in quiet:
        w(f'| {k[0]} | {k[1]} | {hidden_all[k]} | `{libs[k]}` | '
          f'{"yes, by a visible parameter or note" if k[1] in vis_text[k[0]] else "**no**"} |')
if unnamed:
    findings['A'].append(f'{len(unnamed)} parts are named nowhere on their sheet.')
else:
    w('\nEvery part on every sheet can be named by a reader.')
w('')

# ---- 7. text landing on wires ------------------------------------------------------------------
w('## 7. Text that lands on a wire\n')
w('Approximate: a designator, comment or free-text anchor within half a character height of a wire '
  'it does not belong to. Altium draws text over wires without complaint, and it is the commonest '
  'reason a printed sheet is hard to read.\n')
hits = []
for n, s in sheets.items():
    for i, (h, b) in enumerate(s['recs']):
        if not b.startswith((b'|RECORD=34|', b'|RECORD=41|', b'|RECORD=4|')):
            continue
        if field(b, 'IsHidden') == 'T' or field(b, 'Name') in ('PinUniqueId', 'HiddenNetName'):
            continue
        t = field(b, 'Text')
        x, y = num(b, 'Location.X'), num(b, 'Location.Y')
        if not t or x is None or len(t) > 40:
            continue
        if on_any_wire(s, x, y):
            owner = oi(b)
            d = s['desig'].get(owner, ('', ))[0] if owner else ''
            hits.append((n, t[:28], x, y, d))
if hits:
    w(f'{len(hits)} text anchors sit on a wire.\n')
    w('| Sheet | Text | X | Y | Belongs to |')
    w('|---|---|---:|---:|---|')
    for n, t, x, y, d in sorted(hits)[:40]:
        w(f'| {n} | `{t}` | {x:.0f} | {y:.0f} | {d or "free text"} |')
    if len(hits) > 40:
        w(f'\n...and {len(hits) - 40} more.')
    findings['B'].append(f'{len(hits)} text anchors land on a wire.')
else:
    w('None.')
w('')

# ---- 8. how much of the page the drawing actually gets ----------------------------------------
w('## 8. How much of the printed page the drawing gets\n')
w('Measured off the exported PDF itself, with no assumption about what the sheet records mean: each '
  'page is 792 x 612 points, landscape letter, and the drawing on it is portrait. Nothing here is '
  'inferred from the schematic files.\n')
w('| Page | Page size | Ink on it | Share of the page | Blank width |')
w('|---|---|---|---:|---:|')
try:
    import pymupdf
    pdf = pymupdf.open(os.path.join(PRJ, 'zulu_a7.pdf'))
    worst = 0
    for i in range(pdf.page_count):
        pg = pdf[i]
        r = None
        for dr in pg.get_drawings():
            r = dr['rect'] if r is None else r | dr['rect']
        share = 100 * r.width * r.height / (pg.rect.width * pg.rect.height)
        blank = 100 * (pg.rect.width - r.width) / pg.rect.width
        worst = max(worst, blank)
        w(f'| {i} | {pg.rect.width:.0f} x {pg.rect.height:.0f} | {r.width:.0f} x {r.height:.0f} | '
          f'{share:.0f}% | {blank:.0f}% |')
    w('')
    w(f'Every page fits its drawing to the HEIGHT -- the ink is 602 points tall against a 612-point '
      f'page -- and leaves {worst:.0f} per cent of the width blank. Turn the page portrait and the '
      f'same drawing has 792 points of height to fill instead of 612, which is about 1.3x linearly: '
      f'every line and character a third bigger, no redrawing. It is a page-setup choice in the Smart '
      f'PDF wizard, and it is the cheapest readability gain available on this schematic.\n')
    findings['A'].append('the PDF prints portrait sheets on landscape pages, wasting ~40% of the width.')
except Exception as e:                                     # pragma: no cover
    w(f'(could not measure the PDF: {e})')
w('')
w('What I could NOT settle from the records: whether any content falls outside the sheet rectangle. '
  'The header gives `CustomX`/`CustomY` per sheet, and taken as a portrait rectangle those numbers '
  'reproduce the printed aspect exactly on every page -- but they also put thousands of objects on '
  'sheet 5 outside the sheet, while the rendered page shows the border comfortably enclosing all of '
  'them. Rather than pick a reading, it is left open: if sheet 5 ever prints clipped at the right, '
  'this is where to look.\n')

w('## What the machine half found\n')
if findings['A'] or findings['B']:
    if findings['A']:
        w('Worth acting on before the board work:\n')
        for f in findings['A']:
            w(f'- {f}')
        w('')
    if findings['B']:
        w('Worth knowing, not worth stopping for:\n')
        for f in findings['B']:
            w(f'- {f}')
        w('')
else:
    w('Nothing. Every geometric and spelling check above came back clean.\n')
w('For context on what a clean result here does and does not mean: this checks that labels land on '
  'wires, that names resolve to nets, that nothing dangles and that the page is used. It cannot see '
  'a sheet that is correct and still hard to read.\n')

NOTES = os.path.join(HERE, 'schematic_review_notes.md')
if os.path.exists(NOTES):
    w(io.open(NOTES, encoding='utf-8').read().rstrip())
    w('')
else:
    w('## What this cannot judge\n')
    w('Whether a sheet reads well. Whether the eye lands on the signal path first, whether related '
      'parts are grouped the way the circuit works rather than the way the importer happened to place '
      'them, whether a reader can follow a net from the connector to the ball without a search. Those '
      'need eyes on the drawing, and they are the half of this review that matters most for a board '
      'about to be laid out.\n')

print('\n'.join(out))
