"""Proofs for the 2026-11-20 schematic sync (Zulu_A7_no_pmod Rev 2 -> this board); see docs/sync_schematics.md.

    python tools/sync_sch_proof.py [--write]      exit code 0 = every check passed
                                                  --write also writes docs/sync_schematics_records.txt

Netlists come from Asar_feather/Rev_1/tools/sch_netlist.py (flat project: net labels and power ports name nets
project-wide; Altium's wire / pin / junction rules), run on
  BEFORE  backups/zulu_a7_0..4.SchDoc.pre-sync + the untouched sheets 5 and 6 (copied to a temporary folder),
  AFTER   Imported zulu_a7.PrjPcb,
  SOURCE  Zulu_A7_no_pmod/Rev_2/Imported zulu_a7.PrjPcb.
Checks:
 1. BEFORE -> AFTER is exactly: GND gains U2-EP; R119-R134 appear; each Dn = {U1 ball, U3 DQ pin} splits into
    SDRAM-Dn = {U3 DQ pin, R(119+n)-1} and Dn = {R(119+n)-2, U1 ball}.  Every other net keeps its name and pins.
 2. AFTER == SOURCE except the Pmod: drop J1 and R26-R33, nets JA* / PMOD-*, and the 8 U1 balls that carry JA* here
    become unconnected single-pin nets, as on the no-PMOD sheets.
 3. Record diff of each touched sheet, BEFORE vs AFTER: an alignment on bodies without OwnerIndex, with every matched
    record's owner checked to map onto the matched owner; every changed / inserted / deleted record is listed.
    Expected per sheet: 0 = 1 label; 1 = 6 records (X4); 2 = the X2 frame + 41 X2 NOTEs; 3 = 38 deleted + 505 + 62
    inserted; 4 = U2 (9 changed; EP pin, 2 parameters, 2 wires inserted), U10 (5 changed, 10 SI records inserted),
    title label / OriginDescription / Q1 Comment changed.
 4. No written text names the no-PMOD board, the west-edge JTAG column, a missing Pmod or 60.96 mm
    (stale_notes_sch.FORBIDDEN).
 5. Sheet 1's FileHeader equals the no-PMOD sheet 1 (TARGET sheet 1 was identical to it at 31df8a8).
"""
import difflib
import os
import re
import shutil
import sys
import tempfile
from collections import Counter

from sync_sch_common import (BAK, PRJ, REPO, REV2, SRC_PRJ, check_sheet, designators, duplicate_uids, field, load,
                             md5, owner, read_stream, sheet)
from stale_notes_sch import scan

sys.path.insert(0, os.path.join(REPO, 'Asar_feather', 'Rev_1', 'tools'))
import sch_netlist  # noqa: E402

TOUCHED = (0, 1, 2, 3, 4)
UNTOUCHED_MD5 = {5: '9c7543e6', 6: '59736165'}
PMOD_PARTS = re.compile(r'J1|R2[6-9]|R3[0-3]')
PMOD_NETS = re.compile(r'JA\d+|PMOD-\d+')
TEXT_KEYS = ('Text', 'ComponentDescription', 'Description', 'Name')
FAIL = []


def check(ok, msg):
    print(('PASS  ' if ok else 'FAIL  ') + msg)
    if not ok:
        FAIL.append(msg)


def netlist(folder):
    return {k: set(v) for k, v in sch_netlist.build(folder).items()}


def canon(nets):
    """{name: pins} with N$ (unnamed) nets keyed by their pin set, so only membership counts for them."""
    out = {}
    for k, v in nets.items():
        out['N$' + ','.join(sorted('%s-%s' % p for p in v)) if k.startswith('N$') else k] = frozenset(v)
    return out


def show(a, b, la, lb, cap=40):
    lines = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            x, y = a.get(k, frozenset()), b.get(k, frozenset())
            lines.append('    %s: only %s %s | only %s %s' % (k, la, sorted('%s-%s' % p for p in x - y)[:8],
                                                             lb, sorted('%s-%s' % p for p in y - x)[:8]))
    for line in lines[:cap]:
        print(line)
    if len(lines) > cap:
        print('    ... %d more' % (len(lines) - cap))


# ---------------------------------------------------------------- netlists
def netlist_checks():
    with tempfile.TemporaryDirectory() as tmp:
        for n in TOUCHED:
            shutil.copy2(os.path.join(BAK, 'zulu_a7_%d.SchDoc.pre-sync' % n), os.path.join(tmp, 'zulu_a7_%d.SchDoc' % n))
        for n, m in UNTOUCHED_MD5.items():
            check(md5(sheet(n)) == m, 'sheet %d untouched (md5 %s)' % (n, m))
            shutil.copy2(sheet(n), os.path.join(tmp, 'zulu_a7_%d.SchDoc' % n))
        before = netlist(tmp)
    after, source = netlist(PRJ), netlist(SRC_PRJ)
    print('nets: before %d, after %d, no-PMOD %d' % (len(before), len(after), len(source)))

    # 1. before -> after
    exp = {k: set(v) for k, v in before.items()}
    exp['GND'].add(('U2', 'EP'))
    for n in range(16):
        d = exp['D%d' % n]
        u3 = [p for p in d if p[0] == 'U3']
        u1 = [p for p in d if p[0] == 'U1']
        assert len(d) == 2 and len(u3) == 1 and len(u1) == 1, ('D%d' % n, d)
        r = 'R%d' % (119 + n)
        exp['D%d' % n] = {u1[0], (r, '2')}
        exp['SDRAM-D%d' % n] = {u3[0], (r, '1')}
    ok = canon(exp) == canon(after)
    check(ok, 'BEFORE -> AFTER: only GND+U2-EP, R119-R134 and the 16 Dn -> SDRAM-Dn / Dn splits')
    if not ok:
        show(canon(exp), canon(after), 'expected', 'after')
    added = sorted({p[0] for v in after.values() for p in v} - {p[0] for v in before.values() for p in v})
    check(added == sorted('R%d' % k for k in range(119, 135)), 'parts added: %s' % ' '.join(added))
    print('    D0..D15 now: ' + '; '.join('D%d={%s} SDRAM-D%d={%s}' % (
        n, ','.join(sorted('%s-%s' % p for p in after['D%d' % n])), n,
        ','.join(sorted('%s-%s' % p for p in after['SDRAM-D%d' % n]))) for n in (0, 15)) + ' ...')

    # 2. after vs no-PMOD
    exp2 = {}
    freed = []
    for k, v in after.items():
        keep = {p for p in v if not PMOD_PARTS.fullmatch(p[0])}
        if PMOD_NETS.fullmatch(k):
            freed += [p for p in keep]
            continue
        if keep:
            exp2[k] = keep
    for p in freed:
        exp2['N$%s-%s' % p] = {p}
    ok = canon(exp2) == canon(source)
    check(ok, 'AFTER == no-PMOD after removing the Pmod (J1, R26-R33, JA*/PMOD-*); freed U1 balls: %s'
          % ' '.join(sorted('%s-%s' % p for p in freed)))
    if not ok:
        show(canon(exp2), canon(source), 'expected', 'no-PMOD')
    check(len(freed) == 8 and all(p[0] == 'U1' for p in freed), '8 U1 balls carry the Pmod here')
    return before, after, source


# ---------------------------------------------------------------- record diff
def norm(b):
    return re.sub(rb'\|OwnerIndex=-?\d+', b'', b)


def label(recs, i, des):
    """Short description of record i: type, owning designator, name/text."""
    b = recs[i][1]
    r = field(b, 'RECORD')
    o, top = i, None
    while o is not None and o > 0:
        if field(recs[o][1], 'RECORD') == '1':
            top = o
            break
        o = owner(recs[o][1])
    who = des.get(top, '?') if top is not None else 'sheet'
    bits = [x for x in (field(b, 'Name'), field(b, 'Designator'), field(b, 'ModelName')) if x]
    t = field(b, 'Text')
    if r == '27':
        bits.append('(%s,%s)-(%s,%s)' % (field(b, 'X1'), field(b, 'Y1'), field(b, 'X2'), field(b, 'Y2')))
    elif t is not None and r != '41':
        bits.append(repr(t[:60]))
    elif r in ('25', '4'):
        bits.append('@(%s,%s)' % (field(b, 'Location.X'), field(b, 'Location.Y')))
    return 'R%s %s %s uid=%s' % (r, who, ' '.join(bits), field(b, 'UniqueID') or '-')


def segment(x, y, ctx=40, cap=2000):
    """'old' -> 'new', or for long texts only the part that differs, with ctx characters around it."""
    if len(x) + len(y) <= 400:
        return '%r -> %r' % (x, y)
    p = 0
    while p < min(len(x), len(y)) and x[p] == y[p]:
        p += 1
    s = 0
    while s < min(len(x), len(y)) - p and x[len(x) - 1 - s] == y[len(y) - 1 - s]:
        s += 1
    a, b = max(0, p - ctx), s - ctx if s > ctx else 0
    xs, ys = x[a:len(x) - b], y[a:len(y) - b]
    return '%s%r -> %r%s  (chars %d..%d of %d -> %d)' % ('...' if a else '', xs[:cap], ys[:cap], '...' if b else '',
                                                        a, len(x) - b, len(x), len(y))


def fields_of(b):
    out = {}
    for part in b.rstrip(b'\x00').split(b'|'):
        if b'=' in part:
            k, v = part.split(b'=', 1)
            out[k.decode('latin-1')] = v.decode('latin-1')
    return out


def recdiff(n, out):
    A = load(os.path.join(BAK, 'zulu_a7_%d.SchDoc.pre-sync' % n))
    B = load(sheet(n))
    da, db = designators(A), designators(B)
    sm = difflib.SequenceMatcher(None, [norm(b) for h, b in A], [norm(b) for h, b in B], autojunk=False)
    amap = {}
    changed, inserted, deleted = [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
        elif tag == 'replace' and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):
                amap[i1 + k] = j1 + k
                changed.append((i1 + k, j1 + k))
        else:
            deleted += list(range(i1, i2))
            inserted += list(range(j1, j2))
    # same UniqueID on both sides of a delete/insert pair = a changed record that moved
    ua = {field(A[i][1], 'UniqueID'): i for i in deleted if field(A[i][1], 'UniqueID')}
    for j in list(inserted):
        u = field(B[j][1], 'UniqueID')
        if u in ua:
            i = ua.pop(u)
            deleted.remove(i)
            inserted.remove(j)
            amap[i] = j
            changed.append((i, j))
    # every matched record's owner must map onto the matched owner
    bad = 0
    for i, j in amap.items():
        oa, ob = owner(A[i][1]), owner(B[j][1])
        if (oa is None or oa <= 0) != (ob is None or ob <= 0) or (oa and oa > 0 and amap.get(oa) != ob):
            bad += 1
    try:
        check_sheet(B, duplicate_uids(A))      # Weight, NULs, owners before children, no new duplicate UniqueIDs
        struct = True
    except AssertionError:
        struct = False
    check(bad == 0 and struct,
          'sheet %d: %d -> %d records, owners consistent, structure ok (Weight, NULs, no new duplicate UniqueIDs); '
          '%d changed, %d inserted, %d deleted'
          % (n, len(A), len(B), len(changed) - (1 if (0, 0) in changed else 0), len(inserted), len(deleted)))
    out.append('== sheet %d (zulu_a7_%d.SchDoc): %d -> %d records; md5 %s -> %s' % (
        n, n, len(A), len(B), md5(os.path.join(BAK, 'zulu_a7_%d.SchDoc.pre-sync' % n)), md5(sheet(n))))
    texts = []
    for i, j in sorted(changed, key=lambda t: t[1]):
        fa, fb = fields_of(A[i][1]), fields_of(B[j][1])
        diffs = [(k, fa.get(k), fb.get(k)) for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)
                 and k != 'OwnerIndex' and not (i == 0 and k == 'Weight')]
        if not diffs:
            continue
        out.append('  ~ #%d->#%d %s' % (i, j, label(B, j, db)))
        for k, x, y in diffs:
            out.append('      %s: %s' % (k, segment(x or '', y or '')))
            if k in TEXT_KEYS and y:
                texts.append((n, j, y))
    for i in deleted:
        out.append('  - #%d %s' % (i, label(A, i, da)))
    for j in inserted:
        out.append('  + #%d %s' % (j, label(B, j, db)))
        for k in TEXT_KEYS:
            t = field(B[j][1], k)
            if t:
                texts.append((n, j, t))
    return dict(changed=[c for c in changed if c != (0, 0)], inserted=inserted, deleted=deleted, texts=texts,
                summary=Counter(label(B, j, db).split(' uid=')[0].split(' ')[1] for j in inserted))


def main():
    write = '--write' in sys.argv[1:]
    netlist_checks()
    lines, texts = [], []
    res = {}
    for n in TOUCHED:
        r = recdiff(n, lines)
        res[n] = r
        texts += r['texts']
    check((len(res[3]['deleted']), len(res[3]['inserted'])) == (38, 505 + 62),
          'sheet 3: 38 records deleted (18 stubs, 18 labels, 2 caption lines), 567 inserted (16 R subtrees 432, '
          '34 wires, 34 labels, 5 caption lines, 62 SI)')
    check(len(res[4]['inserted']) == 5 + 10, 'sheet 4: 15 records inserted (U2 EP pin + 2 params + 2 wires, U10 SI 10)')
    check(not res[0]['inserted'] and not res[1]['inserted'] and not res[2]['inserted'], 'sheets 0-2: nothing inserted')
    # 4. texts
    bad = [(n, j, scan(t)) for n, j, t in texts if scan(t)]
    check(not bad, 'no written text describes the no-PMOD board / west-edge JTAG / missing Pmod / 60.96 mm %s'
          % (bad[:5] if bad else ''))
    # 5. sheet 1
    check(read_stream(sheet(1)) == read_stream(sheet(1, src=True)), 'sheet 1 FileHeader == no-PMOD sheet 1')
    if write:
        p = os.path.join(REV2, 'docs', 'sync_schematics_records.txt')
        with open(p, 'w', newline='\n') as f:
            f.write('Generated by tools/sync_sch_proof.py --write: every record changed (~), inserted (+) or deleted (-)\n'
                    'by the 2026-11-20 schematic sync, BEFORE = backups/*.pre-sync, AFTER = the project sheets.\n'
                    '#i->#j are record indices before -> after (record 0 is the header; its Weight changes with the\n'
                    'count and is not listed).  OwnerIndex renumbering is not listed; the proof checks it.\n\n')
            f.write('\n'.join(lines) + '\n')
        print('wrote %s (%d lines)' % (os.path.relpath(p, REV2), len(lines)))
    else:
        for line in lines:
            if line.startswith('=='):
                print(line)
    print('ALL CHECKS PASSED' if not FAIL else '%d CHECK(S) FAILED' % len(FAIL))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
