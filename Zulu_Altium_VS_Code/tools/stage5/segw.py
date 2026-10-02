# -*- coding: utf-8 -*-
"""exact per-segment maximum legal width, using route_emit's own distance code"""
import io, json, os, sys, math
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import route_emit as re

# Stage 5 (the L5 VCC3V3 plane) is built against the SAME board as stage 4b: the board after stage 4a
# (tools/route_inputs.json as of commit 1f9073d/14a8511, PcbDoc md5 f8d8e62c959f5a8bd13a19def9fc0edf).
# Stage 4b was never placed, so the guard below is unchanged: GND still has 336 tracks and 128 vias.
# Once stage 5 is placed, route_inputs.json describes the new board; re-running then needs
#     git show 14a8511:Zulu_Altrium/tools/route_inputs.json > PRE.json
#     python tools/stage5/gen.py --inputs PRE.json
RI = sys.argv[sys.argv.index('--inputs') + 1] if '--inputs' in sys.argv else os.path.join(TOOLS, 'route_inputs.json')

def load():
    inp = json.load(io.open(RI, encoding='utf-8'))
    ng, nv = sum(1 for t in inp['tracks'] if t['net'] == 'GND'), sum(1 for v in inp['vias'] if v['net'] == 'GND')
    if (ng, nv) != (336, 128):
        sys.exit('stage5/segw.py: %s is not the post-stage-4a board (GND has %d tracks and %d vias, the stage-4a board '
                 'has 336 and 128); pass --inputs with tools/route_inputs.json from commit 1f9073d' % (RI, ng, nv))
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
