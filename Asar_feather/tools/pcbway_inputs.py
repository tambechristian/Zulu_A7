# -*- coding: utf-8 -*-
"""Readers for the Asar Feather PCBWay assembly generator (tools/generate_pcbway_assembly.py).

Copied 2026-11-11 from the Zulu A7 Fab B helpers and cut down to what the generator uses:
  * read_stream / split / field    from Zulu_A7_Fab_B/tools/fix_text_orientation.py (SchDoc records)
  * natkey / load_components       from Zulu_A7_Fab_B/tools/bom_audit.py, retargeted to asar_a7_0..6.SchDoc
  * kvs, LAYER, U                  from Zulu_A7_Fab_B/tools/route_inputs.py (PcbDoc records)
Fab B's bom_audit.py and route_inputs.py also carry Zulu-specific datasheet tables and routing inputs; those are
not copied, so nothing here can silently describe the Zulu board.
"""
import os
import re
from collections import OrderedDict, defaultdict

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PRJ = os.path.join(ROOT, 'Asar_feather.PrjPcb')
SHEETS = [os.path.join(PRJ, f'asar_a7_{n}.SchDoc') for n in range(7)]

U = 2.54e-6                     # Altium internal unit (1/10000 mil) in mm
# PcbDoc layer ids as used on this board: 1 Top, 4 L2 (GND pour), 2 L3, 3 L4, 5 L5 (VCC3V3 pour), 32 Bottom.
LAYER = {1: 'Top', 2: 'L3-SIG', 3: 'L4-SIG', 4: 'L2-GND', 5: 'L5-VCC3V3', 32: 'Bottom', 74: 'Multi'}


def read_stream(path, name):
    ole = olefile.OleFileIO(path)
    try:
        return ole.openstream(name).read()
    finally:
        ole.close()


def split(data):
    recs = []
    i = 0
    while i + 4 <= len(data):
        n = int.from_bytes(data[i:i + 2], 'little')
        hdr = data[i:i + 4]
        i += 4
        recs.append([hdr, data[i:i + n]])
        i += n
    assert i == len(data)
    return recs


def field(body, key):
    m = re.search(rb'\|(?:%UTF8%)?' + key.encode() + rb'=([^|\x00]*)', body, re.I)
    return m.group(1).decode('latin-1') if m else None


def natkey(s):
    m = re.match(r'([A-Za-z$]*)(\d*)', s)
    return (m.group(1), int(m.group(2) or 0), s)


def load_components():
    """{designator: {'sheet', 'lib', 'params', 'fp'}} from the seven Asar SchDocs (multi-gate parts merged)."""
    comps = OrderedDict()
    for n, path in enumerate(SHEETS):
        recs = split(read_stream(path, 'FileHeader'))
        desig = {int(field(b, 'OwnerIndex')) + 1: field(b, 'Text') for h, b in recs if b.startswith(b'|RECORD=34|')}
        params, fp = defaultdict(dict), {}
        for i, (h, b) in enumerate(recs):
            o = field(b, 'OwnerIndex')
            if o is None:
                continue
            o = int(o) + 1
            if b.startswith(b'|RECORD=41|'):
                params[o][field(b, 'Name')] = field(b, 'Text')
            elif b.startswith(b'|RECORD=44|'):
                for h3, b3 in recs:
                    if b3.startswith(b'|RECORD=45|') and field(b3, 'OwnerIndex') == str(i - 1):
                        fp[o] = field(b3, 'ModelName')
        for i, (h, b) in enumerate(recs):
            if not b.startswith(b'|RECORD=1|'):
                continue
            d = desig.get(i)
            if not d:
                continue
            c = comps.setdefault(d, {'sheet': n, 'lib': field(b, 'LibReference'), 'params': {}, 'fp': None})
            c['params'].update({k: v for k, v in params.get(i, {}).items() if v})
            c['fp'] = c['fp'] or fp.get(i)
    return comps


def kvs(f, stream, key):
    d = f.openstream(stream).read().decode('latin-1', 'replace')
    out = {}
    for i, r in enumerate(x for x in d.split(chr(0)) if key in x):
        kv = {}
        for item in r.strip('|').split('|'):
            if '=' in item:
                k, v = item.split('=', 1)
                kv[k] = v
        out[i] = kv
    return out
