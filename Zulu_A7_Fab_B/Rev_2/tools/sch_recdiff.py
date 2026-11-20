"""Record-level SchDoc diff: components keyed by (designator, CurrentPartId) with their children keyed by identity,
free records (wires, labels, ports, notes, junctions...) as multisets of content signatures, matched by UniqueID.
Used for the 2026-11-20 schematic sync (docs/sync_schematics.md) to compare this board's sheets with the no-PMOD ones.

    python tools/sch_recdiff.py A.SchDoc B.SchDoc [--brief] [--ignore-font] [--norm] [--max=N]

--norm ignores what an Altium re-save changes by itself: Orientation/Justification 0, the footprint records'
DatafileCount / ModelDatafileEntity0 / ModelDatafileKind0 and NotAutoPosition flags.  PinUniqueId texts are ignored.
"""
import sys
import json
from collections import Counter, defaultdict

from sync_sch_common import read_stream, split  # noqa: E402

DROP = {'UNIQUEID', 'OWNERINDEX', 'INDEXINSHEET'}
TYPES = {'1': 'Component', '2': 'Pin', '4': 'Label', '5': 'Bezier', '6': 'Polyline', '7': 'Polygon', '8': 'Ellipse',
         '10': 'RoundRect', '11': 'EllipticalArc', '12': 'Arc', '13': 'Line', '14': 'Rectangle', '15': 'SheetSymbol',
         '17': 'PowerPort', '18': 'Port', '22': 'NoERC', '25': 'NetLabel', '26': 'Bus', '27': 'Wire', '28': 'TextFrame',
         '29': 'Junction', '30': 'Image', '31': 'Sheet', '34': 'Designator', '37': 'BusEntry', '39': 'Template',
         '41': 'Parameter', '43': 'WarningSign', '44': 'ImplList', '45': 'Implementation', '46': 'MapDefinerList',
         '47': 'MapDefiner', '48': 'ImplParams', '209': 'Note', '215': 'CompileMask', '226': 'Hyperlink'}


def parse(body):
    s = body.rstrip(b'\x00')
    d = {}
    for part in s.split(b'|'):
        if not part or b'=' not in part:
            continue
        k, v = part.split(b'=', 1)
        k = k.decode('latin-1')
        utf = k.startswith('%UTF8%')
        if utf:
            k = k[6:]
            v = v.decode('utf-8', 'replace')
        else:
            v = v.decode('latin-1')
        if utf or k.upper() not in d:
            d[k.upper()] = v
    return d


class Sheet:
    def __init__(self, path, ignore_font=False):
        self.recs = [parse(b) for h, b in split(read_stream(path))]
        fonts = {}
        for r in self.recs:
            if r.get('RECORD') == '31':
                n = int(r.get('FONTIDCOUNT', 0))
                for i in range(1, n + 1):
                    fonts[str(i)] = '{}/{}/r{}{}{}{}'.format(
                        r.get('FONTNAME%d' % i), r.get('SIZE%d' % i), r.get('ROTATION%d' % i, '0'),
                        '/B' if r.get('BOLD%d' % i) else '', '/I' if r.get('ITALIC%d' % i) else '',
                        '/U' if r.get('UNDERLINE%d' % i) else '')
        self.fonts = fonts
        self.ignore_font = ignore_font
        n = len(self.recs)
        self.owner = [None] * n
        for i, r in enumerate(self.recs):
            if 'OWNERINDEX' in r:
                self.owner[i] = int(r['OWNERINDEX']) + 1
        kids = defaultdict(list)
        for i, o in enumerate(self.owner):
            if o is not None and o > 0:
                kids[o].append(i)
        self.kids = kids
        self.des = {}
        for i, r in enumerate(self.recs):
            if r.get('RECORD') == '34' and self.owner[i]:
                self.des[self.owner[i]] = r.get('TEXT')
        self.comps = {}
        for i, r in enumerate(self.recs):
            if r.get('RECORD') == '1':
                key = (self.des.get(i, '?%d' % i), r.get('CURRENTPARTID', '1'))
                if key in self.comps:
                    key = (key[0], key[1] + '#%d' % i)
                self.comps[key] = i

    NORM = False

    def sig(self, r):
        d = {}
        for k, v in r.items():
            if k in DROP:
                continue
            if Sheet.NORM:
                if k in ('ORIENTATION', 'JUSTIFICATION') and v == '0':
                    continue
                if k in ('DATAFILECOUNT', 'MODELDATAFILEENTITY0', 'MODELDATAFILEKIND0', 'NOTAUTOPOSITION',
                         'OVERRIDENOTAUTOPOSITION'):
                    continue
            if k.endswith('FONTID') and not k.startswith('SYSTEM'):
                v = 'IGN' if self.ignore_font else self.fonts.get(v, 'font?' + v)
            d[k] = v
        if r.get('RECORD') == '41' and r.get('NAME', '').upper() == 'PINUNIQUEID':
            d.pop('TEXT', None)
        return d

    def subtree(self, i):
        out = []
        stack = list(self.kids.get(i, []))
        while stack:
            j = stack.pop()
            out.append(j)
            stack.extend(self.kids.get(j, []))
        return out

    def comp_children(self, ci):
        """{child key: signature} for one component's subtree."""
        out = {}
        cnt = Counter()
        for j in sorted(self.subtree(ci)):
            r = self.recs[j]
            t = r.get('RECORD')
            if t == '2':
                k = ('pin', r.get('DESIGNATOR'), r.get('OWNERPARTID'))
            elif t == '41':
                o = self.owner[j]
                po = ''
                if o != ci:
                    pr = self.recs[o]
                    po = '{}:{}'.format(TYPES.get(pr.get('RECORD'), pr.get('RECORD')),
                                        pr.get('DESIGNATOR') or pr.get('MODELNAME') or '')
                k = ('param', po, r.get('NAME'))
            elif t == '34':
                k = ('designator',)
            elif t == '44':
                k = ('implist',)
            elif t == '45':
                k = ('impl', r.get('MODELTYPE'), r.get('MODELNAME'))
            elif t in ('46', '47', '48'):
                pr = self.recs[self.owner[j]]
                k = (TYPES[t], pr.get('MODELTYPE'), pr.get('MODELNAME'))
            else:
                k = ('gfx', TYPES.get(t, t), r.get('OWNERPARTID'))
            cnt[k] += 1
            if cnt[k] > 1:
                k = k + ('#%d' % cnt[k],)
            out[k] = self.sig(r)
        return out

    def _under_comp(self, i):
        o = self.owner[i]
        while o:
            if self.recs[o].get('RECORD') == '1':
                return True
            o = self.owner[o]
        return False

    def free(self):
        out = []
        for i, r in enumerate(self.recs[1:], 1):
            if r.get('RECORD') == '1':
                continue
            if not self._under_comp(i):
                out.append(i)
        return out


def fmt(d, keys=None, maxlen=160):
    items = [(k, d[k]) for k in (keys or sorted(d)) if k in d]
    s = ' '.join('{}={}'.format(k, v) for k, v in items)
    return s if len(s) <= maxlen else s[:maxlen] + '...'


def short(r, maxlen=220):
    t = TYPES.get(r.get('RECORD'), r.get('RECORD'))
    keys = ['TEXT', 'NAME', 'LOCATION.X', 'LOCATION.Y', 'X1', 'Y1', 'X2', 'Y2', 'X3', 'Y3', 'LOCATIONCOUNT', 'CORNER.X',
            'CORNER.Y', 'STYLE', 'ORIENTATION', 'ISHIDDEN']
    return '{} {}'.format(t, fmt(r, keys, maxlen))


def fdiff(a, b):
    ks = sorted(set(a) | set(b))
    return [(k, a.get(k), b.get(k)) for k in ks if a.get(k) != b.get(k)]


def cut(v, n=110):
    if v is None:
        return None
    return v if len(v) <= n else v[:n] + '...'


def compare(pa, pb, brief=False, ignore_font=False, out=print, maxshow=100000):
    A, B = Sheet(pa, ignore_font), Sheet(pb, ignore_font)
    res = {}
    ka, kb = set(A.comps), set(B.comps)
    res['comps_only_a'] = sorted(ka - kb)
    res['comps_only_b'] = sorted(kb - ka)
    out('records A {} B {}; components A {} B {}'.format(len(A.recs), len(B.recs), len(ka), len(kb)))
    if res['comps_only_a']:
        out('components only in A: ' + ' '.join('{}/{}'.format(*k) for k in res['comps_only_a']))
    if res['comps_only_b']:
        out('components only in B: ' + ' '.join('{}/{}'.format(*k) for k in res['comps_only_b']))
    res['comp_changes'] = {}
    for k in sorted(ka & kb):
        ia, ib = A.comps[k], B.comps[k]
        ch = []
        d = fdiff(A.sig(A.recs[ia]), B.sig(B.recs[ib]))
        if d:
            ch.append(('component', d))
        ca, cb = A.comp_children(ia), B.comp_children(ib)
        for ck in sorted(set(ca) | set(cb), key=str):
            if ck not in cb:
                ch.append(('-' + ' '.join(map(str, ck)), fmt(ca[ck])))
            elif ck not in ca:
                ch.append(('+' + ' '.join(map(str, ck)), fmt(cb[ck])))
            else:
                d = fdiff(ca[ck], cb[ck])
                if d:
                    ch.append((' '.join(map(str, ck)), d))
        if ch:
            res['comp_changes']['{}/{}'.format(*k)] = ch
    out('components changed: {}'.format(len(res['comp_changes'])))
    stats = Counter()
    for k, ch in res['comp_changes'].items():
        for what, d in ch:
            if isinstance(d, list):
                for f, x, y in d:
                    stats[(what.split()[0], f)] += 1
            else:
                stats[(what.split()[0][:1] + what.split()[1] if len(what.split()) > 1 else what, '')] += 1
    out('  component change stats: ' + ', '.join('{}.{}={}'.format(a, b, n) for (a, b), n in stats.most_common(40)))
    if not brief:
        shown = 0
        for k, ch in res['comp_changes'].items():
            out('  [{}]'.format(k))
            for what, d in ch:
                shown += 1
                if shown > maxshow:
                    break
                if isinstance(d, list):
                    out('    {}: {}'.format(what, '; '.join('{}: {!r} -> {!r}'.format(f, cut(x), cut(y)) for f, x, y in d)))
                else:
                    out('    {}  {}'.format(what, d))
    fa, fb = A.free(), B.free()
    sa = {i: A.sig(A.recs[i]) for i in fa}
    sb = {i: B.sig(B.recs[i]) for i in fb}
    js_a = {i: json.dumps(v, sort_keys=True) for i, v in sa.items()}
    js_b = {i: json.dumps(v, sort_keys=True) for i, v in sb.items()}
    ha = Counter(js_a.values())
    hb = Counter(js_b.values())
    only_a = ha - hb
    only_b = hb - ha
    ub = {B.recs[i].get('UNIQUEID'): i for i in fb if B.recs[i].get('UNIQUEID')}
    oa_idx, ob_idx = [], []
    rem = Counter(only_a)
    for i in fa:
        if rem[js_a[i]] > 0:
            rem[js_a[i]] -= 1
            oa_idx.append(i)
    rem = Counter(only_b)
    for i in fb:
        if rem[js_b[i]] > 0:
            rem[js_b[i]] -= 1
            ob_idx.append(i)
    obset = set(ob_idx)
    paired_b = set()
    changed, unpaired_a = [], []
    for i in oa_idx:
        j = ub.get(A.recs[i].get('UNIQUEID'))
        if j is not None and j in obset and j not in paired_b:
            paired_b.add(j)
            changed.append((i, j, fdiff(sa[i], sb[j])))
        else:
            unpaired_a.append(i)
    unpaired_b = [j for j in ob_idx if j not in paired_b]
    out('free records: A {} B {}; identical {}; changed (same UniqueID) {}; only A {}; only B {}'.format(
        len(fa), len(fb), sum((ha & hb).values()), len(changed), len(unpaired_a), len(unpaired_b)))
    out('  only A by type: {}'.format(dict(Counter(TYPES.get(A.recs[i].get('RECORD')) for i in unpaired_a))))
    out('  only B by type: {}'.format(dict(Counter(TYPES.get(B.recs[j].get('RECORD')) for j in unpaired_b))))
    out('  changed by type: {}'.format(dict(Counter(TYPES.get(A.recs[i].get('RECORD')) for i, j, d in changed))))
    out('  changed fields: {}'.format(dict(Counter(f for i, j, d in changed for f, x, y in d).most_common(20))))
    res['free_only_a'] = [short(A.recs[i]) for i in unpaired_a]
    res['free_only_b'] = [short(B.recs[j]) for j in unpaired_b]
    res['free_changed'] = [(short(A.recs[i]), d) for i, j, d in changed]
    if not brief:
        for n, (i, j, d) in enumerate(changed):
            if n >= maxshow:
                out('  ... {} more changed'.format(len(changed) - n))
                break
            out('  ~ {} :: {}'.format(short(A.recs[i], 120), '; '.join('{}: {!r} -> {!r}'.format(f, cut(x, 300), cut(y, 300)) for f, x, y in d)))
        for n, i in enumerate(unpaired_a):
            if n >= maxshow:
                out('  ... {} more only-A'.format(len(unpaired_a) - n))
                break
            out('  - ' + short(A.recs[i]))
        for n, j in enumerate(unpaired_b):
            if n >= maxshow:
                out('  ... {} more only-B'.format(len(unpaired_b) - n))
                break
            out('  + ' + short(B.recs[j]))
    return res


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    mx = 100000
    for a in sys.argv:
        if a.startswith('--max='):
            mx = int(a[6:])
    Sheet.NORM = '--norm' in sys.argv
    compare(args[0], args[1], brief='--brief' in sys.argv, ignore_font='--ignore-font' in sys.argv, maxshow=mx)
