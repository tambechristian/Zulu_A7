"""Read zulu_feather.PcbLib through KiCad's Altium reader and check every pad against tools/footprints.json.

KiCad's Y axis points down, so its Y is negated before comparing. Run with KiCad's python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" -u tools/verify_footprints.py
"""
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), 'Zulu_feather.PrjPcb', 'zulu_feather.PcbLib')
TOL = 0.002


def main():
    io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER)
    bad = 0
    for spec in json.load(open(os.path.join(HERE, 'footprints.json'))):
        fp = io.FootprintLoad(LIB, spec['name'])
        if fp is None:
            print('MISSING', spec['name'])
            bad += 1
            continue
        got = []
        for p in fp.Pads():
            pos, sz = p.GetPosition(), p.GetSize(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            dr = p.GetDrillSize()
            got.append((p.GetNumber(), pcbnew.ToMM(pos.x), -pcbnew.ToMM(pos.y), pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y),
                        pcbnew.ToMM(min(dr.x, dr.y)), pcbnew.ToMM(max(dr.x, dr.y)),
                        p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH))
        miss = 0
        for q in spec['pads']:
            want_slot = q.get('slot', 0) or q['drill']
            hit = [g for g in got if g[0] == q['name'] and abs(g[1] - q['x']) < TOL and abs(g[2] - q['y']) < TOL
                   and abs(g[3] - q['dx']) < TOL and abs(g[4] - q['dy']) < TOL and abs(g[5] - q['drill']) < TOL
                   and abs(g[6] - want_slot) < TOL and g[7] == (not q.get('plated', True))]
            if len(hit) != 1:
                miss += 1
                if miss <= 3:
                    print('  no match for', q)
        extra = len(got) - len(spec['pads'])
        print('%-26s %3d pads in spec, %3d read, %d unmatched, %d extra' % (spec['name'], len(spec['pads']), len(got), miss, extra))
        bad += miss + abs(extra)
    print('PASS' if bad == 0 else 'FAIL')
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
