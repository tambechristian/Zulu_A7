# -*- coding: utf-8 -*-
"""Regenerate the master BOM, ../docs/zulu_a7-bom.csv, from the Altium sheets.

    python tools/master_bom.py            (from Zulu_Altrium; writes ../docs/zulu_a7-bom.csv)

Until 2026-09-09 that file came from the root tools/bom.py, which reads the EAGLE zulu_a7.sch;
the Altium project has since replaced the regulators, the oscillator, the SDRAM grade, the beads,
the button, the RGB LED, the USB bridge package and the microSD socket, and added the LiPo
charger, so the EAGLE list no longer describes the board. This script keeps that file's rules:

* one line per ORDERABLE IDENTITY -- MANF# where there is one, else the value (which for the
  connectors and pin headers is the part) -- and per footprint and fitting state; the distinct
  value spellings inside a line are shown joined with " / " (10K / 10k) rather than merged
  silently, because a split spelling is worth fixing in the schematic;
* fitted lines sorted by footprint then identity, DNP lines after them;
* Value = Comment, Package = footprint model, Manufacturer/MANF#/Spec = the MANF, MANF# and SPEC
  parameters, Fitted = DNP when the part carries DNS = Yes, Note = the NOTE parameter (the EAGLE
  notes were imported into it and the change records appended there). A line whose parts carry
  different notes gets them all, each prefixed with its designator.

The file is a pure function of the sheets: nothing is carried over from its previous version.

Frames and the licence logos are not parts. Prints the lines whose parts disagree on MANF or
SPEC, and the parts with no MANF# -- both are schematic defects to fix, not BOM decisions.
"""
import os, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bom_audit
from bom_audit import load_components, natkey

OUT = os.path.normpath(os.path.join(bom_audit.ROOT, '..', 'docs', 'zulu_a7-bom.csv'))
COLS = ['Item', 'Qty', 'Refdes', 'Value', 'Package', 'Manufacturer', 'MANF#', 'Spec', 'Fitted', 'Note']
NOT_PARTS = ('DOCFIELD', 'CC_BY', 'CC_CC', 'CC_SA', 'CC_COPYRIGHT')


def clean(s):
    return ' '.join((s or '').split())


def main():
    comps = load_components()
    groups, no_mpn = {}, []
    for d, c in comps.items():
        if c['lib'] in NOT_PARTS:
            continue
        p = c['params']
        mpn, value = clean(p.get('MANF#')), clean(p.get('Comment'))
        if not mpn:
            no_mpn.append(d)
        dnp = p.get('DNS') == 'Yes'
        groups.setdefault((mpn or value or '(unspecified)', c['fp'] or '', dnp), []).append(d)
    lines, disagree = [], []
    for (ident, fp, dnp), ds in groups.items():
        ds = sorted(ds, key=natkey)
        P = [comps[d]['params'] for d in ds]
        for k in ('MANF', 'SPEC'):
            if len({clean(p.get(k)) for p in P}) > 1:
                disagree.append((k, ' '.join(ds)))
        notes = []
        for d, p in zip(ds, P):
            n = clean(p.get('NOTE'))
            if n and n not in [x for _, x in notes]:
                notes.append((d, n))
        note = ' || '.join(f'{d}: {n}' for d, n in notes) if len(notes) > 1 else (notes[0][1] if notes else '')
        lines.append({
            'Qty': str(len(ds)), 'Refdes': ' '.join(ds),
            'Value': ' / '.join(sorted({clean(p.get('Comment')) for p in P if clean(p.get('Comment'))})),
            'Package': fp, 'Manufacturer': clean(P[0].get('MANF')), 'MANF#': clean(P[0].get('MANF#')),
            'Spec': clean(P[0].get('SPEC')), 'Fitted': 'DNP' if dnp else 'yes', 'Note': note,
            '_key': (dnp, fp, ident)})
    lines.sort(key=lambda l: l['_key'])
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction='ignore')
        w.writeheader()
        for n, line in enumerate(lines, 1):
            line['Item'] = str(n); w.writerow(line)
    fitted = sum(int(l['Qty']) for l in lines if l['Fitted'] == 'yes')
    dnp = sum(int(l['Qty']) for l in lines if l['Fitted'] != 'yes')
    print(f'{len(lines)} lines, {fitted} fitted parts, {dnp} DNP -> {OUT}')
    for k, ds in disagree:
        print(f'  {k} differs inside one line: {ds}')
    if no_mpn:
        print(f'  no MANF#: {" ".join(sorted(no_mpn, key=natkey))}')


if __name__ == '__main__':
    main()
