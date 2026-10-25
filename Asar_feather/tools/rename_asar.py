"""Rename the Feather project from Zulu to Asar (2026-10-25, user request), contents only.

Every replacement keeps its length, so the Altium binaries (SchDoc, PcbDoc, PcbLib: OLE compound files) are
rewritten stream by stream with olefile and no record length changes:
    Zulu_feather -> Asar_feather   (the folder and the project directory)
    zulu_feather -> asar_feather   (project, board, library, XDC)
    zulu_a7_N    -> asar_a7_N      (the seven sheets, the sheet component classes, SOURCEHIERARCHICALPATH)
    zulu_a7      -> asar_a7        (sheet DRAWING_NAME, SOURCEFOOTPRINTLIBRARY), except the historical OriginPath
                                   ...\\Zulu_Altrium\\zulu_a7.sch
    ZULU A7      -> ASAR A7        (the board's silkscreen text, ASCII in Texts6 and UTF-16 in WideStrings6)
Text files (tools, docs, README, XDC, PrjPcb) get the same replacements, except references to the production
board (Zulu_Altium_VS_Code, Zulu_kicad, vivado/zulu_a7_pins.xdc, 'Imported zulu_a7.PrjPcb', zulu_a7.PcbDoc/
PcbLib of production in make_project.py / transplant_u1.py), which stay as they are. Part names ZULU-CONN and
ZULU-DIP37 are library names, not the board name, and are left alone. The file and folder renames are done
afterwards with git mv.

    python tools/rename_asar.py [--dry]      (Altium must have the project closed)
"""
import os
import re
import sys

import olefile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRJ = os.path.join(ROOT, 'Zulu_feather.PrjPcb')

BIN = [(b'Zulu_feather', b'Asar_feather'), (b'zulu_feather', b'asar_feather'), (b'ZULU A7', b'ASAR A7')]
KEEP = re.compile(r'(Zulu_Altium_VS_Code|Zulu_kicad|Zulu_Altrium|Imported zulu_a7\.PrjPcb|vivado/zulu_a7_pins'
                  r'|zulu_a7_pins\.xdc|zulu_a7\.sch|zulu_a7\.PrjPcb|zulu_a7\.PcbDoc|zulu_a7\.PcbLib'
                  r"|'zulu_a7\.PcbDoc'|zulu_a7\.LOG|Project Outputs for zulu_a7)")


def bin_replace(data):
    n = 0
    for a, b in BIN + [(x.decode().encode('utf-16-le'), y.decode().encode('utf-16-le')) for x, y in BIN]:
        n += data.count(a)
        data = data.replace(a, b)
    # zulu_a7 everywhere except the historical OriginPath ...\zulu_a7.sch
    for enc in ('latin-1', 'utf-16-le'):
        a, b, keep = ('zulu_a7'.encode(enc), 'asar_a7'.encode(enc), 'zulu_a7.sch'.encode(enc))
        parts = data.split(keep)
        n += sum(p.count(a) for p in parts)
        data = keep.join(p.replace(a, b) for p in parts)
    return data, n


def do_binary(path, dry):
    o = olefile.OleFileIO(path, write_mode=not dry)
    total = 0
    for s in o.listdir():
        if o.get_type(s) != olefile.STGTY_STREAM:
            continue
        d = o.openstream(s).read()
        nd, n = bin_replace(d)
        if n:
            assert len(nd) == len(d)
            total += n
            if not dry:
                o.write_stream(s, nd)
    o.close()
    return total


def text_replace(t):
    out, n = [], 0
    for line in t.split('\n'):
        new = line
        # protect production references, then rename the Feather ones
        prot = {}
        def hide(m):
            k = '\x00%d\x00' % len(prot)
            prot[k] = m.group(0)
            return k
        new = KEEP.sub(hide, new)
        new = new.replace('Zulu_feather', 'Asar_feather').replace('zulu_feather', 'asar_feather')
        new = new.replace('zulu_a7_', 'asar_a7_').replace('ZULU A7', 'ASAR A7')
        new = new.replace('Zulu A7 Feather', 'Asar A7 Feather')
        for k, v in prot.items():
            new = new.replace(k, v)
        n += new != line
        out.append(new)
    return '\n'.join(out), n


def main():
    dry = '--dry' in sys.argv
    for f in sorted(os.listdir(PRJ)):
        p = os.path.join(PRJ, f)
        if f.endswith(('.SchDoc', '.PcbDoc', '.PcbLib')):
            print('%-28s %4d binary replacements' % (f, do_binary(p, dry)))
    texts = [os.path.join(PRJ, 'zulu_feather.PrjPcb'), os.path.join(PRJ, 'zulu_feather.PrjPcbStructure'),
             os.path.join(ROOT, 'README.md'), os.path.join(ROOT, 'docs', 'routing.md'),
             os.path.join(ROOT, 'vivado', 'zulu_feather_pins.xdc')]
    for d in ('tools', 'docs'):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if f.endswith(('.py', '.pas', '.md')) and f != 'rename_asar.py':
                texts.append(os.path.join(ROOT, d, f))
    for p in sorted(set(texts)):
        if not os.path.exists(p):
            continue
        raw = open(p, 'rb').read()
        t = raw.decode('latin-1')
        nt, n = text_replace(t)
        if n:
            print('%-40s %3d lines' % (os.path.relpath(p, ROOT), n))
            if not dry:
                open(p, 'wb').write(nt.encode('latin-1'))


if __name__ == '__main__':
    main()
