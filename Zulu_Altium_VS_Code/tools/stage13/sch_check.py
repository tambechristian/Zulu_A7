# -*- coding: utf-8 -*-
"""Judge (read-only, olefile): for the 13 swapped U1 balls on zulu_a7_5.SchDoc, the drawn pin (owner U1, current
part), its location, and the net labels (RECORD=25) within 40 units of it, nearest first.  Checks each against the
plan's phase2_list section 4 claim (label text and coordinates).
    python sch_check.py <SchDoc>"""
import olefile, sys, math, hashlib
CLAIM = {'H19': ('CHAN7', 255, 952), 'K17': ('CHAN11', 255, 912), 'W19': ('CHAN12', 255, 892), 'W18': ('CHAN13', 255, 882),
         'K18': ('UART_FT_TXD', 935, 802), 'P17': ('FT-PWREN#', 235, 1132), 'E19': ('JA8', 935, 357), 'T17': ('JA7', 935, 367),
         'G17': ('JA3', 935, 387), 'N19': ('LED0_B', 740, 262), 'P19': ('LED0_R', 740, 252), 'N17': ('BTN', 740, 212),
         'R19': ('CHAN28', 740, 202)}
NEW = {'H19': 'CHAN13', 'K17': 'UART_FT_TXD', 'W19': 'JA8', 'W18': 'JA3', 'K18': 'CHAN11', 'P17': 'LED0_R', 'E19': 'CHAN12',
       'T17': 'CHAN28', 'G17': 'CHAN7', 'N19': 'BTN', 'P19': 'FT-PWREN#', 'N17': 'LED0_B', 'R19': 'JA7'}
path = sys.argv[1]
print('SchDoc md5', hashlib.md5(open(path, 'rb').read()).hexdigest())
o = olefile.OleFileIO(path); b = o.openstream('FileHeader').read(); o.close()
i = 0; recs = []
while i + 4 <= len(b):
    n = int.from_bytes(b[i:i + 3], 'little'); i += 4; recs.append(b[i:i + n]); i += n
def kv(raw):
    d = {}
    for part in raw.rstrip(b'\x00').decode('latin1').split('|'):
        if '=' in part:
            k, v = part.split('=', 1); d[k.upper()] = v
    return d
R = [kv(r) for r in recs]
comps = {k - 1: d for k, d in enumerate(R) if d.get('RECORD') == '1'}
desig = {int(d['OWNERINDEX']): d.get('TEXT') for d in R if d.get('RECORD') == '34' and d.get('OWNERINDEX')}
labels = [d for d in R if d.get('RECORD') == '25']
ok_all = True
for d in R:
    if d.get('RECORD') != '2' or d.get('DESIGNATOR') not in CLAIM:
        continue
    own = int(d.get('OWNERINDEX', -1))
    if desig.get(own) != 'U1' or comps.get(own, {}).get('CURRENTPARTID') != d.get('OWNERPARTID'):
        continue
    x, y = int(d.get('LOCATION.X', 0)), int(d.get('LOCATION.Y', 0))
    near = sorted(((math.hypot(int(L.get('LOCATION.X', 0)) - x, int(L.get('LOCATION.Y', 0)) - y), L.get('TEXT'),
                    int(L.get('LOCATION.X', 0)), int(L.get('LOCATION.Y', 0))) for L in labels))
    near = [z for z in near if z[0] <= 40]
    c = CLAIM[d['DESIGNATOR']]
    hit = any(z[1] == c[0] and z[2] == c[1] and z[3] == c[2] for z in near[:1])
    ok_all &= hit
    print('U1-%-4s pin (%d,%d) part %s: nearest labels %s | claim %s at (%d,%d) -> %s %s' % (
        d['DESIGNATOR'], x, y, d.get('OWNERPARTID'), [(z[1], z[2], z[3], round(z[0], 1)) for z in near[:2]], c[0], c[1], c[2],
        'MATCH' if hit else 'MISMATCH', '(rename to %s)' % NEW[d['DESIGNATOR']]))
print('ALL 13 CLAIMS MATCH' if ok_all else 'SOME CLAIMS DO NOT MATCH')
