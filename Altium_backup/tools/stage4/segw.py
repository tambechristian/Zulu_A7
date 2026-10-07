# -*- coding: utf-8 -*-
"""exact per-segment maximum legal width, using route_emit's own distance code"""
import io, json, os, sys, math
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import route_emit as re

# Stage 4 plans are built against the board AFTER stage 3 (tools/route_inputs.json as of commit a7aa623).  Once a
# stage-4 block is placed, route_inputs.json describes the routed board; re-running then needs
#     git show a7aa623:Zulu_Altrium/tools/route_inputs.json > PRE.json
#     python tools/stage4/gen.py --inputs PRE.json
RI = sys.argv[sys.argv.index('--inputs') + 1] if '--inputs' in sys.argv else os.path.join(TOOLS, 'route_inputs.json')

def load():
    inp = json.load(io.open(RI, encoding='utf-8'))
    n3 = sum(1 for t in inp['tracks'] if t['net'] == 'VCC3V3')
    if n3 != 354:
        sys.exit('stage4/segw.py: %s is not the post-stage-3 board (VCC3V3 has %d tracks, the stage-3 board has 354); '
                 'pass --inputs with tools/route_inputs.json from commit a7aa623' % (RI, n3))
    ng, nv = sum(1 for t in inp['tracks'] if t['net'] == 'GND'), sum(1 for v in inp['vias'] if v['net'] == 'GND')
    if (ng, nv) != (168, 64):
        sys.exit('stage4/segw.py: %s already carries stage-4 copper (GND has %d tracks and %d vias, the pre-stage-4 board '
                 'has 168 and 64); pass --inputs with tools/route_inputs.json from commit a7aa623' % (RI, ng, nv))
    return inp

def clr(net, layer, inp):
    return re.clearance(net, layer, inp) if hasattr(re, 'clearance') else 0.09

def maxwidth(inp, net, layer, seg, plan_tracks=(), plan_vias=(), report=False):
    """largest w such that the segment keeps every rule clearance; also the binding object"""
    best = 9.0; who = None
    C = 0.09
    def upd(d, gap, tag):
        nonlocal best, who
        v = 2.0 * (d - gap)
        if v < best:
            best = v; who = (tag, d, gap)
    # existing vias
    for v in inp['vias']:
        if v['net'] == net: continue
        d = re.seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - v.get('size', 0.35)/2
        upd(d, C, 'via %s %.3f,%.3f' % (v['net'], v['x'], v['y']))
    for v in plan_vias:
        if v['net'] == net: continue
        d = re.seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - 0.175
        upd(d, C, 'planvia %s %.3f,%.3f' % (v['net'], v['x'], v['y']))
    # through-hole pads: every layer
    for p in inp['th_pads']:
        if p['net'] == net: continue
        d = re.seg_rect(seg, p['x'], p['y'], p['sx'], p['sy'])
        upd(d, C, 'th %s-%s' % (p['ref'], p['pad']))
    # smd pads on this layer
    if layer in ('Top', 'Bottom'):
        key = 'top_pads' if layer == 'Top' else 'bottom_pads'
        for p in inp[key]:
            if p['net'] == net: continue
            d = re.seg_rect(seg, p['x'], p['y'], p['sx'], p['sy'])
            upd(d, C, 'pad %s-%s' % (p['ref'], p['pad']))
    # tracks on this layer
    sdram = {n for n, v in inp['nets'].items() if v.get('cls', '').startswith('SDRAM')}
    def gap_for(onet):
        if layer in ('L3-SIG', 'L4-SIG'):
            if onet == 'SDRAM-CLK': return 0.20
            if onet in sdram: return 0.10
        return C
    for t in list(inp['tracks']) + list(plan_tracks):
        if t['net'] == net: continue
        if t['layer'] != layer: continue
        d = re.seg_dist(seg, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['width']/2
        upd(d, gap_for(t['net']), 'trk %s %.3f,%.3f-%.3f,%.3f' % (t['net'], t['x1'], t['y1'], t['x2'], t['y2']))
    # keep-outs
    for k in inp.get('keepouts', []):
        if k.get('layer') != layer: continue
        d = re.seg_rect(seg, (k['x0']+k['x1'])/2, (k['y0']+k['y1'])/2, k['x1']-k['x0'], k['y1']-k['y0'])
        upd(d, C, 'keepout')
    # board edge
    ol = inp['outline']; e = inp.get('edge_clearance', 0.25)
    d = min(min(seg[0], seg[2]) - ol['x0'], ol['x1'] - max(seg[0], seg[2]),
            min(seg[1], seg[3]) - ol['y0'], ol['y1'] - max(seg[1], seg[3]))
    upd(d, e, 'edge')
    return best, who
