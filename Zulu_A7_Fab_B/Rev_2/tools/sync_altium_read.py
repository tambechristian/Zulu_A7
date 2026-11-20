# -*- coding: utf-8 -*-
"""Read-only PcbDoc reader for the Fab B Rev 2 <- no-PMOD Rev 2 sync tools (2026-11-20).

    import sync_altium_read as R
    B = R.read(path)        # dict: nets, comps, pads, texts, rules, classes, bodies, outline, md5

Self-contained (olefile only) so the sync tools in this folder do not import anything from the no-PMOD tree.
Record layouts as Zulu_A7_no_pmod/Rev_2/si/series_r/extract.py, tools/fab_facts.py and KiCad's
altium_parser_pcb.cpp:
  Components6  key=value records; X/Y in mil (board origin = Board6 ORIGINX/Y, 0,0 on both boards)
  Pads6        6 subrecords; 5th: layer@0 net@3 comp@7 x@13 y@17 size top@21/25 mid@29/33 bottom@37/41
               hole@45 shape top/mid/bot@49..51 rot(double)@52
  Texts6       2 subrecords; layer@0 comp@7 x@13 y@17 height@21 rot(double)@27 mirror@35 stroke@36
               comment@40 designator@41; 2nd subrecord = the string as a Pascal short string (length byte)
  ComponentBodies6  1 subrecord; layer@0 comp@7, then the key=value text of the body
Coordinates are returned in mm, unrounded (1 internal unit = 1/10000 mil = 2.54e-6 mm), board frame, y up.
"""
import hashlib
import math
import struct

import olefile

U = 2.54e-6
MIL = 0.0254
LAYER = {1: 'Top', 2: 'L3-SIG', 3: 'L4-SIG', 4: 'L2-GND', 5: 'L5-VCC3V3', 32: 'Bottom', 33: 'TopOverlay',
         34: 'BottomOverlay', 35: 'TopPaste', 36: 'BottomPaste', 37: 'TopSolder', 38: 'BottomSolder', 74: 'Multi'}
for _k in range(16):
    LAYER[57 + _k] = 'Mech%d' % (_k + 1)
SUBRECS = {1: 1, 2: 6, 3: 1, 4: 1, 5: 2, 6: 1, 11: 1, 12: 1}


def i32(b, o):
    return struct.unpack('<i', b[o:o + 4])[0]


def i16(b, o):
    return struct.unpack('<h', b[o:o + 2])[0]


def u16(b, o):
    return struct.unpack('<H', b[o:o + 2])[0]


def dbl(b, o):
    return struct.unpack('<d', b[o:o + 8])[0]


def kvparse(s):
    kv = {}
    for item in s.strip('|').split('|'):
        if '=' in item:
            k, v = item.split('=', 1)
            kv[k] = v
    return kv


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    return [kvparse(r) for r in d.split(chr(0)) if key in r]


def mil(v):
    v = (v or '').strip()
    if v.endswith('mil'):
        return float(v[:-3]) * MIL
    if v.endswith('mm'):
        return float(v[:-2])
    return float(v) * MIL


def records(data):
    i = 0
    while i + 5 <= len(data):
        t = data[i]
        n = SUBRECS.get(t)
        if n is None:
            raise ValueError('unknown record type %d at %d' % (t, i))
        i += 1
        subs = []
        for _ in range(n):
            ln = struct.unpack('<I', data[i:i + 4])[0]
            subs.append(data[i + 4:i + 4 + ln])
            i += 4 + ln
        yield t, subs


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def read(path):
    f = olefile.OleFileIO(path)
    nets = [kv.get('NAME') for kv in kvs(f, 'Nets6/Data', 'NAME=')]
    netname = lambda k: nets[k] if 0 <= k < len(nets) else None  # noqa: E731
    comps = []
    for i, kv in enumerate(kvs(f, 'Components6/Data', 'SOURCEDESIGNATOR=')):
        comps.append(dict(index=i, ref=kv.get('SOURCEDESIGNATOR'), x=mil(kv['X']), y=mil(kv['Y']),
                          x_mil=kv['X'], y_mil=kv['Y'], rot=float(kv.get('ROTATION', '0')) % 360.0,
                          side='Bottom' if kv.get('LAYER') == 'BOTTOM' else 'Top', pattern=kv.get('PATTERN'),
                          name_on=kv.get('NAMEON') == 'TRUE', comment_on=kv.get('COMMENTON') == 'TRUE',
                          name_autopos=int(kv.get('NAMEAUTOPOSITION', '0')),
                          comment_autopos=int(kv.get('COMMENTAUTOPOSITION', '0')),
                          libref=kv.get('SOURCELIBREFERENCE'), fpdesc=kv.get('FOOTPRINTDESCRIPTION'),
                          height=mil(kv.get('HEIGHT', '0mil'))))
    cref = lambda k: comps[k]['ref'] if 0 <= k < len(comps) else None  # noqa: E731
    pads = []
    for t, subs in records(f.openstream('Pads6/Data').read()):
        if t != 2:
            continue
        name = subs[0][1:1 + subs[0][0]].decode('latin-1')
        b = subs[4]
        if len(b) < 60:
            continue
        sx, sy = i32(b, 21) * U, i32(b, 25) * U
        rot = dbl(b, 52) % 360.0
        c, s = abs(math.cos(math.radians(rot))), abs(math.sin(math.radians(rot)))
        pads.append(dict(ref=cref(u16(b, 7)), pad=name, layer=LAYER.get(b[0], str(b[0])), net=netname(i16(b, 3)),
                         x=i32(b, 13) * U, y=i32(b, 17) * U, sx=sx, sy=sy, rot=rot,
                         w=sx * c + sy * s, h=sx * s + sy * c, hole=i32(b, 45) * U, shape=b[49]))
    texts = []
    for t, subs in records(f.openstream('Texts6/Data').read()):
        b, s = subs[0], subs[1]
        texts.append(dict(text=s[1:1 + s[0]].decode('latin-1', 'replace') if s else '',
                          layer=LAYER.get(b[0], str(b[0])), comp=cref(u16(b, 7)) if u16(b, 7) != 65535 else None,
                          x=i32(b, 13) * U, y=i32(b, 17) * U, height=i32(b, 21) * U, rot=dbl(b, 27) % 360.0,
                          mirror=b[35] == 1, stroke=i32(b, 36) * U, comment=b[40] == 1, designator=b[41] == 1))
    bodies = []
    if f.exists('ComponentBodies6/Data'):
        for t, subs in records(f.openstream('ComponentBodies6/Data').read()):
            b = subs[0]
            ci = u16(b, 7)
            pl = struct.unpack('<I', b[18:22])[0] if len(b) > 22 else 0
            props = kvparse(b[22:22 + pl].decode('latin-1', 'replace').rstrip(chr(0)))
            bodies.append(dict(comp=cref(ci) if ci != 65535 else None, layer=LAYER.get(b[0], str(b[0])),
                               overall_height=mil(props['OVERALLHEIGHT']) if 'OVERALLHEIGHT' in props else None,
                               projection=props.get('BODYPROJECTION'), props=props))
    rules = kvs(f, 'Rules6/Data', 'RULEKIND=')
    classes = kvs(f, 'Classes6/Data', 'NAME=')
    board = kvparse(f.openstream('Board6/Data').read().decode('latin-1', 'replace').replace(chr(0), '|'))
    f.close()
    verts, k = [], 0
    while 'VX%d' % k in board:
        verts.append((mil(board['VX%d' % k]), mil(board['VY%d' % k])))
        k += 1
    return dict(nets=nets, comps=comps, pads=pads, texts=texts, bodies=bodies, rules=rules, classes=classes,
                outline=verts, origin=(mil(board.get('ORIGINX', '0mil')), mil(board.get('ORIGINY', '0mil'))),
                md5=md5(path))


def class_members(cls):
    """Members of a Classes6 record (M0, M1, ...)."""
    out, k = [], 0
    while 'M%d' % k in cls:
        out.append(cls['M%d' % k])
        k += 1
    return out
