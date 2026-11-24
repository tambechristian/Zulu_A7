"""Compare the saved board's printing overlay texts with geom (before) + ops (the script's operations).
usage: python verify_applied.py <before geom.json> <ops.json> <after PcbDoc>
Every printing Top/Bottom Overlay text (free texts + shown designators/comments) must match the expected set on
(layer, text, x, y, rot, h, stroke) within 0.001 mm; non-printing texts are compared too (hidden designators etc.)."""
import json
import struct
import sys

import olefile

U = 2.54e-6
G = json.load(open(sys.argv[1]))
E = json.load(open(sys.argv[2]))
f = olefile.OleFileIO(sys.argv[3])
comps = []
for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
    if 'PATTERN=' in r:
        comps.append(dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x))
d = f.openstream('Texts6/Data').read()
after, i = [], 0
while i + 5 <= len(d):
    i += 1
    subs = []
    for _ in range(2):
        n = struct.unpack('<I', d[i:i + 4])[0]
        subs.append(d[i + 4:i + 4 + n])
        i += 4 + n
    b, s = subs
    if b[0] not in (33, 34):
        continue
    ci = struct.unpack('<H', b[7:9])[0]
    txt = s[1:1 + s[0]].decode('latin-1', 'replace') if s else ''
    kind, shown, ref = 'free', True, None
    if ci != 0xFFFF:
        c = comps[ci]
        ref = c.get('SOURCEDESIGNATOR')
        kind = 'designator' if b[41] == 1 else 'comment'
        shown = (c.get('NAMEON') if kind == 'designator' else c.get('COMMENTON')) == 'TRUE'
    after.append((b[0], kind, ref, txt, round(struct.unpack('<i', b[13:17])[0] * U, 3),
                  round(struct.unpack('<i', b[17:21])[0] * U, 3), round(struct.unpack('<d', b[27:35])[0] % 360, 1),
                  round(struct.unpack('<i', b[21:25])[0] * U, 3), round(struct.unpack('<i', b[36:40])[0] * U, 3), shown))
exp = []
dele = set(int(x) for x in E['delete'])
for t in G['texts']:
    if t['idx'] in dele:
        continue
    t = dict(t)
    t.update(E['set'].get(str(t['idx']), {}))
    exp.append((t['layer'], t['kind'], t['ref'], t['text'], round(t['x'], 3), round(t['y'], 3), round(t['rot'] % 360, 1),
                round(t['h'], 3), round(t['stroke'], 3), bool(t['shown'])))
for t in E.get('add', []):
    exp.append((t['layer'], 'free', None, t['text'], round(t['x'], 3), round(t['y'], 3), round(t['rot'] % 360, 1),
                round(t['h'], 3), round(t['stroke'], 3), True))
A, X = sorted(after, key=str), sorted(exp, key=str)
miss = [e for e in X if e not in A]
extra = [a for a in A if a not in X]
print('overlay texts: expected %d, board %d' % (len(X), len(A)))
for m in miss:
    print('MISSING ', m)
for m in extra:
    print('EXTRA   ', m)
print('VERIFY_APPLIED', 'PASS' if not miss and not extra else 'FAIL')
