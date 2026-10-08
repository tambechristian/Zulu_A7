# KiCad copy: the author's name in every sheet's title block (2026-10-08, user request), as on the Altium copies
# (Zulu_Altium_VS_Code/tools/schematic_author.py). The imported DOCFIELD symbol carries property "AUTHOR" with the
# literal value "AUTHOR" and no "AUTHOR:" label. Per sheet this script:
#   1. sets the AUTHOR property's value to "Christian Tambe";
#   2. adds a property "AUTHOR_LABEL" = "AUTHOR:", a copy of the PROJECT: label property moved to the AUTHOR row,
#      so the row reads "AUTHOR: Christian Tambe" like the EAGLE original.
# Guards: exactly one DOCFIELD instance per sheet, AUTHOR still "AUTHOR", no AUTHOR_LABEL yet (a rerun stops).
#   python tools/apply_schematic_author.py kicad_project
import glob
import os
import re
import sys

NAME = 'Christian Tambe'


def prop_block(text, name, value):
    """Return (start, end) of the one '(property "name" "value"' block (tab-indented, closing at '\n\t\t)')."""
    key = '\t\t(property "%s" "%s"\n' % (name, value)
    i = text.find(key)
    if i < 0 or text.find(key, i + 1) >= 0:
        raise SystemExit('REFUSED: %d x %r' % (text.count(key), key.strip()))
    j = text.find('\n\t\t)\n', i)
    return i, j + len('\n\t\t)\n')


def main(folder):
    sheets = sorted(f for f in glob.glob(os.path.join(folder, 'zulu_a7_*.kicad_sch')))
    if len(sheets) != 7:
        raise SystemExit('REFUSED: expected 7 sheets, found %d' % len(sheets))
    for path in sheets:
        t = open(path, encoding='utf-8', newline='').read()
        if t.count('(lib_id "ctambe:DOCFIELD")') != 1:
            raise SystemExit('REFUSED %s: %d DOCFIELD instances' % (path, t.count('(lib_id "ctambe:DOCFIELD")')))
        if '(property "AUTHOR_LABEL"' in t:
            raise SystemExit('REFUSED %s: AUTHOR_LABEL already present' % path)
        a0, a1 = prop_block(t, 'AUTHOR', 'AUTHOR')
        p0, p1 = prop_block(t, 'PROJECT', 'PROJECT:')
        ay = re.search(r'\(at ([\d.]+) ([\d.]+) ([\d.]+)\)', t[a0:a1])
        px = re.search(r'\(at ([\d.]+) ([\d.]+) ([\d.]+)\)', t[p0:p1])
        label = t[p0:p1].replace('(property "PROJECT" "PROJECT:"', '(property "AUTHOR_LABEL" "AUTHOR:"', 1)
        label = label.replace(px.group(0), '(at %s %s %s)' % (px.group(1), ay.group(2), px.group(3)), 1)
        author = t[a0:a1].replace('(property "AUTHOR" "AUTHOR"', '(property "AUTHOR" "%s"' % NAME, 1)
        new = t[:a0] + author + label + t[a1:]
        open(path, 'w', encoding='utf-8', newline='').write(new)
        print('%-20s AUTHOR -> %s at (%s, %s); AUTHOR_LABEL "AUTHOR:" at (%s, %s)'
              % (os.path.basename(path), NAME, ay.group(1), ay.group(2), px.group(1), ay.group(2)))


if __name__ == '__main__':
    main(sys.argv[1])
