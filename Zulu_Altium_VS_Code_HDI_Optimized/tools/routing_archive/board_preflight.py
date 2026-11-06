# -*- coding: utf-8 -*-
"""Check the design against itself before a PcbDoc is created, using primary sources only.

Written on 2026-09-10 after two stale numbers reached real work in one day: the board length
(a document still said 2.400 in after the board had gone back to 2.750) and the CPG236 land
(0.275 mm taken from a table that gives it as a maximum, which closes the escape). Both came from
believing prose. Nothing here reads a .md.

Every fact is derived from a file that IS the design:

    the Altium netlist  Imported zulu_a7.PrjPcb/Project Outputs for zulu_a7/zulu_a7.NET
    the PCB library     Imported zulu_a7.PrjPcb/zulu_a7.PcbLib
    the placement plan  docs/placement.html
    the land patterns   tools/new_footprints.json

The one check that matters most is the third: EVERY PAD THE NETLIST REFERENCES MUST EXIST IN THE
FOOTPRINT. That is what fails at Import Changes, one component at a time, after the board has been
started -- and it is fully answerable offline, now.
"""
import io
import json
import os
import re
import sys
import collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_pcblib import pads as lib_pads          # the OLE pad-record parser

import olefile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NET = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'Project Outputs for zulu_a7', 'zulu_a7.NET')
LIB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbLib')
PLAN = os.path.join(ROOT, 'docs', 'placement.html')
PCB = os.path.join(ROOT, 'Imported zulu_a7.PrjPcb', 'zulu_a7.PcbDoc')

BOARD = (69.85, 25.40)          # the outline about to be drawn; checked, not assumed


def read_netlist(path):
    s = io.open(path, encoding='latin-1').read()
    comp = {}
    for blk in re.findall(r'^\[\s*\n(.*?)^\]\s*$', s, re.M | re.S):
        L = [l.rstrip() for l in blk.splitlines()]
        comp[L[0]] = L[1] if len(L) > 1 else ''
    nets = {}
    for blk in re.findall(r'^\(\s*\n(.*?)^\)\s*$', s, re.M | re.S):
        L = [l.strip() for l in blk.splitlines() if l.strip()]
        nets[L[0]] = L[1:]
    return comp, nets


def main():
    fails, warns = [], []
    comp, nets = read_netlist(NET)
    print('netlist   %d components, %d nets, %d pad references'
          % (len(comp), len(nets), sum(len(v) for v in nets.values())))

    f = olefile.OleFileIO(LIB)
    skip = {'FileHeader', 'Library', 'Textures', 'Models', 'ComponentParamsTOC',
            'LayerKindMapping', 'FileVersionInfo'}
    fps = sorted({e[0] for e in f.listdir() if len(e) > 1} - skip)
    lib = {name: {p[0] for p in lib_pads(f, name)} for name in fps}
    print('library   %d footprints, %d pads total'
          % (len(lib), sum(len(v) for v in lib.values())))

    # ---- 1. every component names a footprint, and that footprint is in the library
    print('\n1. footprint assignment')
    missing_fp = sorted({v for v in comp.values() if v and v not in lib})
    blank = sorted(k for k, v in comp.items() if not v)
    if blank:
        fails.append('%d components carry no footprint: %s' % (len(blank), blank[:8]))
    if missing_fp:
        fails.append('footprints named but not in the library: %s' % missing_fp)
    used = collections.Counter(v for v in comp.values() if v)
    print('   %d components -> %d distinct footprints, all present: %s'
          % (len(comp), len(used), 'yes' if not missing_fp and not blank else 'NO'))
    unused = sorted(set(lib) - set(used))
    if unused:
        print('   %d library footprints unused (harmless): %s' % (len(unused), unused))

    # ---- 2. every pad the netlist references exists in that component's footprint
    print('\n2. pad references resolve  <- the check that fails at Import Changes')
    bad = collections.defaultdict(set)
    refs = 0
    for netname, padlist in nets.items():
        for p in padlist:
            ref, pin = p.split('-', 1)
            refs += 1
            fp = comp.get(ref)
            if fp is None:
                bad['<no such component>'].add(p)
            elif fp in lib and pin not in lib[fp]:
                bad['%s (%s)' % (ref, fp)].add(pin)
    if bad:
        for k in sorted(bad)[:12]:
            fails.append('%s: pads not in the footprint: %s' % (k, sorted(bad[k])[:10]))
    print('   %d pad references checked, %d unresolved' % (refs, sum(len(v) for v in bad.values())))

    # ---- 3. pads that exist but no net uses (open by design, or a missed connection)
    print('\n3. footprint pads no net uses')
    usedpads = collections.defaultdict(set)
    for padlist in nets.values():
        for p in padlist:
            ref, pin = p.split('-', 1)
            usedpads[ref].add(pin)
    loose = []
    for ref, fp in sorted(comp.items()):
        if fp not in lib:
            continue
        spare = lib[fp] - usedpads.get(ref, set())
        if spare:
            loose.append((ref, fp, sorted(spare)))
    tot = sum(len(x[2]) for x in loose)
    print('   %d pads on %d components are on no net' % (tot, len(loose)))
    for ref, fp, spare in loose[:14]:
        print('      %-6s %-20s %s' % (ref, fp, ' '.join(spare[:12])))
    if tot:
        warns.append('%d unconnected pads across %d components - each is either an intended '
                     'no-connect or a missed net; check before routing' % (tot, len(loose)))

    # ---- 4. the placement plan against the outline and against the netlist
    print('\n4. placement plan')
    s = io.open(PLAN, encoding='utf-8').read()
    ext = []
    for name in ('FRONT', 'BACK'):
        m = re.search(r'%s\s*=\s*\[(.*?)\];' % name, s, re.S)
        for r in re.findall(r'\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,'
                            r'\s*[\'"]([^\'"]*)[\'"]', m.group(1)):
            ext.append((r[4], float(r[0]), float(r[1]), float(r[2]), float(r[3])))
    over = [e for e in ext if e[3] > BOARD[0] + 1e-6 or e[4] > BOARD[1] + 1e-6
            or e[1] < -1e-6 or e[2] < -1e-6]
    print('   %d blocks, extents x %.1f..%.1f  y %.1f..%.1f  against a %.2f x %.2f board'
          % (len(ext), min(e[1] for e in ext), max(e[3] for e in ext),
             min(e[2] for e in ext), max(e[4] for e in ext), BOARD[0], BOARD[1]))
    if over:
        fails.append('placement blocks outside the outline: %s'
                     % [(e[0], e[1], e[3]) for e in over])
    else:
        print('   every block is inside the outline')

    # ---- 5. the BGA land against the escape it has to support
    print('\n5. BGA escape arithmetic')
    with io.open(os.path.join(HERE, 'new_footprints.json'), encoding='utf-8') as fh:
        json.load(fh)                                    # parses, or this raises
    cp = lib_pads(f, 'XC7A35T-CPG236')
    land = round(sorted({round(p[3], 4) for p in cp})[0], 4)
    xs = sorted({round(p[1], 3) for p in cp})
    pitch = round(xs[1] - xs[0], 3)
    need = 0.0762 + 2 * 0.09                             # 3 mil trace, 3.5 mil clearance
    margin = (pitch - land) - need
    print('   %d lands at %.4f mm on %.3f mm pitch -> gap %.4f, a 3 mil trace at 3.5 mil '
          'clearance needs %.4f' % (len(cp), land, pitch, pitch - land, need))
    print('   escape margin %+.4f mm  %s' % (margin, 'OK' if margin > 0 else 'IMPOSSIBLE'))
    if margin <= 0:
        fails.append('the BGA land closes the escape: margin %+.4f mm at a %.4f mm land'
                     % (margin, land))
    f.close()

    # ---- 6. the PcbDoc itself: outline, stack, and whether the planes agree with the board
    print('\n6. the PcbDoc')
    if not os.path.exists(PCB):
        print('   no PcbDoc yet')
    else:
        pf = olefile.OleFileIO(PCB)
        b6 = pf.openstream(['Board6', 'Data']).read()[4:].decode('latin-1')
        vx = {int(k): v for k, v in re.findall(r'\|VX(\d+)=([^|]*)', b6)}
        vy = {int(k): v for k, v in re.findall(r'\|VY(\d+)=([^|]*)', b6)}

        def mil(s):
            m = re.fullmatch(r'\s*(-?[\d.]+)\s*mil\s*', s)
            return float(m.group(1)) if m else None

        pts = [(mil(vx[i]), mil(vy[i])) for i in sorted(vx) if i in vy]
        xs = [p[0] for p in pts if p[0] is not None]
        ys = [p[1] for p in pts if p[1] is not None]
        w = (max(xs) - min(xs)) * 0.0254
        h = (max(ys) - min(ys)) * 0.0254
        print('   board shape %d vertices, %.3f x %.3f mm, lower-left (%.3f, %.3f) mm'
              % (len(pts), w, h, min(xs) * 0.0254, min(ys) * 0.0254))
        if abs(w - BOARD[0]) > 0.01 or abs(h - BOARD[1]) > 0.01:
            fails.append('board shape is %.3f x %.3f mm, wanted %.2f x %.2f'
                         % (w, h, BOARD[0], BOARD[1]))
        elif abs(min(xs)) > 0.01 or abs(min(ys)) > 0.01:
            warns.append('board shape is the right size but its lower-left corner is at '
                         '(%.3f, %.3f) mm, not the origin' % (min(xs) * 0.0254, min(ys) * 0.0254))

        # Altium sizes each split-plane polygon to the board shape. If the shape was changed by
        # poking the file instead of through the editor, the planes stay on the old board -- so
        # compare them rather than trusting that they followed.
        try:
            pg = pf.openstream(['Polygons6', 'Data']).read().decode('latin-1')
        except Exception:
            pg = ''
        pv = [mil(v) for _, v in re.findall(r'\|(VX\d+)=([^|]*)', pg)]
        pv = [v for v in pv if v is not None]
        if pv:
            pw = (max(pv) - min(pv)) * 0.0254
            gap = (w - pw) / 2.0
            print('   plane polygons span %.3f mm in x, inset %.3f mm from the board edge'
                  % (pw, gap))
            if gap < 0 or gap > 2.0:
                fails.append('plane polygons do not match the board shape (inset %.3f mm) - they '
                             'were not regenerated when the outline changed' % gap)
        # the stack as stored, and the one thing that cannot be set until Import Changes has
        # brought the nets across: an internal Plane layer with no net is floating copper, and
        # every GND pad and stitch via on it would connect to nothing
        lay = collections.defaultdict(dict)
        for m in re.finditer(r'\|V9_STACK_LAYER(\d+)_([A-Z0-9_]+)=([^|]*)', b6):
            lay[int(m.group(1))][m.group(2)] = m.group(3)

        def milv(s):
            mm = re.fullmatch(r'\s*([\d.]+)\s*mil\s*', s or '')
            return float(mm.group(1)) if mm else 0.0

        cu = [(d['NAME'], d.get('COPTHICK', '')) for i, d in sorted(lay.items())
              if d.get('NAME') and d.get('COPTHICK')]
        thick = sum(milv(d.get('COPTHICK')) + milv(d.get('DIELHEIGHT'))
                    for d in lay.values())
        print('   stack %d copper layers, %.3f mm total: %s'
              % (len(cu), thick * 0.0254, ', '.join('%s %s' % c for c in cu)))
        # PLANEnNETNAME is indexed from 1 and there are 16 slots whatever the stack holds, so
        # take only as many as the stack actually has planes, and sort NUMERICALLY -- a string
        # sort puts PLANE10 before PLANE1 and names the wrong layers in the warning
        planes = {int(k): v for k, v in re.findall(r'\|PLANE(\d+)NETNAME=([^|\r]*)', b6)}
        nplane = sum(1 for d in lay.values()
                     if d.get('COPTHICK') and d.get('NAME', '').endswith('GND'))
        unset = ['PLANE%dNETNAME' % k for k in sorted(planes)[:nplane]
                 if planes[k].strip() == '(No Net)']
        if unset:
            warns.append('%d internal plane(s) still have no net assigned (%s). A Plane layer '
                         'with no net is floating copper. This CANNOT be set until Design > '
                         'Import Changes has brought GND onto the board - do it immediately '
                         'after.' % (len(unset), ', '.join(unset)))
        pf.close()

    print('\n' + '=' * 70)
    for w in warns:
        print('WARN  %s' % w)
    for x in fails:
        print('FAIL  %s' % x)
    if not fails:
        print('PREFLIGHT CLEAN - every pad the netlist names exists in its footprint, every')
        print('placed block is inside the outline, and the BGA land supports its escape.')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
