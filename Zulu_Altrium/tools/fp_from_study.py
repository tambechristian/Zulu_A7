# -*- coding: utf-8 -*-
"""Turn the land-pattern study into tools/new_footprints.json and docs/footprint_lands.md.

The study ran eight datasheet readers and eight independent verifiers, each told to refute the
reader's numbers from the primary source rather than check them (workflow zulu-footprint-lands,
2026-09-10). This script takes that run's result file and distils it into the two things the rest
of the pipeline needs: the pad geometry fp_emit.py turns into EAGLE packages, and a readable record
of where every number came from.

Where a verifier returned CORRECTED, its pad list wins; otherwise the reader's is used.

    python tools/fp_from_study.py <path to the workflow result .output file>
"""
import io
import json
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# what the schematic symbols demand; the build fails rather than ship a footprint that cannot mate
WANT = {
    'SOT23-5':           [str(i) for i in range(1, 6)],
    'PTS810':            ['1', '2', '3', '4'],
    'JST-B2B-PH-SM4-TB': ['1', '2', 'MP1', 'MP2'],
    'VQFN16-3X3-RGT':    [str(i) for i in range(1, 18)],
    'FT2232HL-LQFP64':   [str(i) for i in range(1, 65)],
    'DM3D-SF':           [str(i) for i in range(1, 9)] + ['A', 'B', 'G1', 'G2', 'G3', 'G4'],
    '742C163':           [str(i) for i in range(1, 17)],
    '742C043':           ['1', '2', '3', '4'],
}

USED_BY = {
    'SOT23-5':           'U5, U6, U7 - Semtech SC189 bucks',
    'PTS810':            'BTN - C&K/Littelfuse PTS810SJM250SMTR LFS tact switch',
    'JST-B2B-PH-SM4-TB': 'X4 - JST PH 2-circuit top-entry SMT header, the LiPo connector',
    'VQFN16-3X3-RGT':    'U8 - TI bq24232 charger and power path',
    'FT2232HL-LQFP64':   'U2 - FTDI FT2232HL USB bridge',
    'DM3D-SF':           'X3 - Hirose DM3D-SF microSD socket',
    '742C163':           'R4 - CTS 742C163, eight isolated elements',
    '742C043':           'R1 - CTS 742C043, two isolated elements',
}


def load(path):
    top = json.loads(io.open(path, encoding='utf-8').read())
    res = top['result'] if isinstance(top, dict) else top
    if isinstance(res, str):
        res = json.loads(res)
    return res


def main(path):
    res = load(path)
    fps, doc = [], []
    for e in sorted(res, key=lambda r: r['key']):
        key = e['key']
        spec = e.get('spec') or {}
        vd = e.get('verdict') or {}
        pads = vd.get('corrected_pads') or spec.get('pads') or []
        body = vd.get('corrected_body') or spec.get('body') or {}
        src = spec.get('source') or {}

        got = sorted(p['name'] for p in pads)
        want = sorted(WANT[key])
        assert got == want, '%s: pads %s, symbol wants %s' % (key, got, want)
        assert body.get('dx') and body.get('dy'), '%s: no body' % key

        basis = ('manufacturer recommended land' if src.get('used_recommended_land')
                 else 'DERIVED, no manufacturer land exists')
        cite = '%s p%s, %s' % (os.path.basename(str(src.get('file', '?'))),
                               src.get('page'), str(src.get('figure', '')).split('(')[0].strip())
        fps.append(dict(
            name=key,
            description='%s. %s. %s.' % (USED_BY[key], cite, basis),
            body={'dx': round(float(body['dx']), 4), 'dy': round(float(body['dy']), 4)},
            pads=[dict(name=p['name'], x=round(float(p['x']), 4), y=round(float(p['y']), 4),
                       dx=round(float(p['dx']), 4), dy=round(float(p['dy']), 4),
                       shape=p.get('shape', 'rect'), drill=round(float(p.get('drill', 0)), 4))
                  for p in pads],
        ))

        doc.append(dict(key=key, basis=basis, cite=cite, verdict=vd.get('verdict'),
                        npads=len(pads), body=body,
                        pin1=str(spec.get('pin1_note', '')).strip(),
                        warn=str(spec.get('warnings', '')).strip(),
                        problems=vd.get('problems') or []))

    out = os.path.join(HERE, 'new_footprints.json')
    io.open(out, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(fps, indent=1) + '\n')
    print('wrote %s  (%d footprints, %d pads)'
          % (out, len(fps), sum(len(f['pads']) for f in fps)))

    def wrap(s, n=110):
        return '\n'.join(textwrap.fill(par, n) for par in s.split('\n') if par.strip())

    md = ['# Footprint land patterns', '',
          'Where every pad in the eight footprints drawn on 2026-09-10 comes from. Each was read out of the',
          "manufacturer's datasheet by one agent and then re-derived from the same primary source by a second",
          'told to refute it, not to confirm it (workflow `zulu-footprint-lands`). Six came back CONFIRMED,',
          'one CORRECTED, and none rejected. Geometry is in millimetres with the origin at the body centre,',
          'viewed from the top.', '',
          '| Footprint | Used by | Pads | Basis | Verdict |', '|---|---|---|---|---|']
    for d in doc:
        md.append('| `%s` | %s | %d | %s | %s |'
                  % (d['key'], USED_BY[d['key']], d['npads'],
                     'recommended land' if 'recommended' in d['basis'] else '**derived**',
                     d['verdict']))
    md.append('')
    for d in doc:
        md += ['## %s' % d['key'], '',
               '**%s** &middot; %d pads &middot; body %.3f x %.3f mm &middot; verdict %s'
               % (USED_BY[d['key']], d['npads'], d['body']['dx'], d['body']['dy'], d['verdict']),
               '', 'Source: %s. %s.' % (d['cite'], d['basis']), '',
               '### Pin 1 and numbering', '', wrap(d['pin1']), '']
        if d['warn']:
            md += ['### Cautions carried forward', '', wrap(d['warn']), '']
        if d['problems']:
            md += ['### What the verifier challenged', '']
            for i, p in enumerate(d['problems']):
                md += ['%d. %s' % (i + 1, wrap(str(p)).replace('\n', '\n   ')), '']
    dpath = os.path.join(ROOT, 'docs', 'footprint_lands.md')
    io.open(dpath, 'w', encoding='utf-8', newline='\n').write('\n'.join(md) + '\n')
    print('wrote %s  (%d chars)' % (dpath, len('\n'.join(md))))


if __name__ == '__main__':
    main(sys.argv[1])
