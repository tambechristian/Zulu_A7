"""Seed the Feather project from the production Zulu A7 Altium project (2026-10-23).

Copies the seven SchDocs, the PcbLib and the PcbDoc from Zulu_Altium_VS_Code (commit 8df3577) into
Asar_feather/Asar_feather.PrjPcb/, renames the board to asar_feather.PcbDoc and writes asar_feather.PrjPcb
with only those nine documents (the production project's .pas entries point at ../tools, which this
folder does not carry). The PcbDoc is copied so the 6-layer HDI stack, the via types, the rules and the
net classes come along; its copper and placement are replaced later.
Refuses to overwrite an existing project.
    python tools/make_project.py
"""
import hashlib
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, '..', 'Zulu_Altium_VS_Code', 'Imported zulu_a7.PrjPcb')
DST = os.path.join(ROOT, 'Asar_feather.PrjPcb')
SHEETS = ['zulu_a7_%d.SchDoc' % i for i in range(7)]
# the Feather was renamed Asar on 2026-10-25 (tools/rename_asar.py); a fresh seed writes the Asar names
RENAME = dict({s: 'asar' + s[4:] for s in SHEETS}, **{'zulu_a7.PcbDoc': 'asar_feather.PcbDoc', 'zulu_a7.PcbLib': 'asar_feather.PcbLib'})


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def main():
    if os.path.exists(os.path.join(DST, 'asar_feather.PrjPcb')):
        sys.exit('REFUSED: %s already holds asar_feather.PrjPcb' % DST)
    os.makedirs(DST, exist_ok=True)
    for name in RENAME:
        out = RENAME.get(name, name)
        shutil.copyfile(os.path.join(SRC, name), os.path.join(DST, out))
        if md5(os.path.join(SRC, name)) != md5(os.path.join(DST, out)):
            sys.exit('copy mismatch: ' + name)
        print('%-22s -> %-22s %s' % (name, out, md5(os.path.join(DST, out))))

    text = open(os.path.join(SRC, 'zulu_a7.PrjPcb'), encoding='latin-1').read()
    parts = re.split(r'(?m)^(?=\[)', text)
    keep, n = [], 0
    for p in parts:
        m = re.match(r'\[Document(\d+)\]', p)
        if m:
            path = re.search(r'(?m)^DocumentPath=(.*)$', p).group(1).strip()
            if path not in SHEETS and path not in RENAME:
                continue
            n += 1
            p = re.sub(r'^\[Document\d+\]', '[Document%d]' % n, p)
            p = p.replace('DocumentPath=' + path, 'DocumentPath=' + RENAME.get(path, path))
        keep.append(p)
    if n != 9:
        sys.exit('expected 9 documents, kept %d' % n)
    out = ''.join(keep).replace('zulu_a7.PrjPcb', 'asar_feather.PrjPcb')
    open(os.path.join(DST, 'asar_feather.PrjPcb'), 'w', encoding='latin-1', newline='').write(out)
    print('asar_feather.PrjPcb: %d documents' % n)


if __name__ == '__main__':
    main()
