# -*- coding: utf-8 -*-
"""exact per-segment maximum legal width, using route_emit's own distance code"""
import io, json, os, sys, math
TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)
import route_emit as re

# Stage 6 IS the stage-4b job -- the last 140 signal connections -- retried on the board that
# stages 5 and 5b freed.  The first attempt (docs/stage4b_attempt.md) closed 92 of 140 and was never
# placed; it planned seven regions in parallel with nothing arbitrating the shared corridors, on a
# board where VCC3V3's trunks blocked 370 mm2.  Those trunks are gone: L5 carries VCC3V3, the north
# band has 669 lanes instead of 439 (L4 alone 0 -> 205) and the U1 east corridor 382 instead of 248.
#
# The board this measures against is commit a87c4af, PcbDoc md5 33aece2b03e9037466e366447c81a32d,
# tools/route_inputs.json md5 1c187fd975046aaf8cc93216abb4d863: 1498 tracks, 371 vias, GND 341/133,
# VCC3V3 168/86 (a plane net now -- tie_check.py, not signals_check, proves it complete).
# Once a stage-6 block is placed, route_inputs.json describes the routed board; re-running then needs
#     git show a87c4af:Zulu_Altrium/tools/route_inputs.json > PRE.json
#     python tools/stage6/gen.py --inputs PRE.json
RI = sys.argv[sys.argv.index('--inputs') + 1] if '--inputs' in sys.argv else os.path.join(TOOLS, 'route_inputs.json')

def load():
    inp = json.load(io.open(RI, encoding='utf-8'))
    ng, nv = sum(1 for t in inp['tracks'] if t['net'] == 'GND'), sum(1 for v in inp['vias'] if v['net'] == 'GND')
    nt, nvv = len(inp['tracks']), len(inp['vias'])
    if (ng, nv, nt, nvv) != (341, 133, 1498, 371):
        sys.exit('stage6/segw.py: %s is not the post-stage-5b board (it has %d tracks and %d vias, GND %d/%d; '
                 'the stage-5b board has 1498 and 371, GND 341/133).  Pass --inputs with\n'
                 '    git show a87c4af:Zulu_Altrium/tools/route_inputs.json > PRE.json'
                 % (RI, nt, nvv, ng, nv))
    return inp

def clr(net, layer, inp):
    return re.clearance(net, layer, inp) if hasattr(re, 'clearance') else 0.09

def maxwidth(inp, net, layer, seg, plan_tracks=(), plan_vias=(), report=False):
    """largest w such that the segment keeps every rule clearance; also the binding object"""
    best = 9.0; who = None
    C = 0.09
    # BOTH nets' clearances, and hoisted above EVERY loop.  Until 2026-09-28 gap_for() was defined
    # below and used only in the track loop, so the via, through-hole and SMD-pad loops all measured
    # a flat 0.09 -- an SDRAM via on L3/L4 was allowed at 0.09 where Clearance_SDRAM_INNER needs 0.10
    # (0.20 for SDRAM-CLK).  It also ignored the ROUTED net's own class, so an SDRAM track was sized
    # at 0.09 to non-SDRAM copper.  Found by the stage-6 judge; tools/route_emit.py had the same hole
    # in its track-vs-via and track-vs-TH-pad loops and is fixed too.  The placed board audits clean
    # either way -- 0 violations over its 1498 tracks.
    _sdram = {n for n, v in inp['nets'].items() if (v.get('cls') or '').startswith('SDRAM')}

    def gap_for(onet):
        if layer in ('L3-SIG', 'L4-SIG'):
            if net == 'SDRAM-CLK' or onet == 'SDRAM-CLK':
                return 0.20
            if net in _sdram or onet in _sdram:
                return 0.10
        return C

    def upd(d, gap, tag):
        nonlocal best, who
        v = 2.0 * (d - gap)
        if v < best:
            best = v; who = (tag, d, gap)
    # existing vias
    for v in inp['vias']:
        if v['net'] == net: continue
        d = re.seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - v.get('size', 0.35)/2
        upd(d, gap_for(v['net']), 'via %s %.3f,%.3f' % (v['net'], v['x'], v['y']))
    for v in plan_vias:
        if v['net'] == net: continue
        d = re.seg_dist(seg, (v['x'], v['y'], v['x'], v['y'])) - 0.175
        upd(d, gap_for(v['net']), 'planvia %s %.3f,%.3f' % (v['net'], v['x'], v['y']))
    # through-hole pads: every layer
    for p in inp['th_pads']:
        if p['net'] == net: continue
        d = re.seg_rect(seg, p['x'], p['y'], p['sx'], p['sy'])
        upd(d, gap_for(p['net']), 'th %s-%s' % (p['ref'], p['pad']))
    # smd pads on this layer
    if layer in ('Top', 'Bottom'):
        key = 'top_pads' if layer == 'Top' else 'bottom_pads'
        for p in inp[key]:
            if p['net'] == net: continue
            d = re.seg_rect(seg, p['x'], p['y'], p['sx'], p['sy'])
            upd(d, gap_for(p['net']), 'pad %s-%s' % (p['ref'], p['pad']))
    # tracks on this layer
    for t in list(inp['tracks']) + list(plan_tracks):
        if t['net'] == net: continue
        if t['layer'] != layer: continue
        d = re.seg_dist(seg, (t['x1'], t['y1'], t['x2'], t['y2'])) - t['width']/2
        upd(d, gap_for(t['net']), 'trk %s %.3f,%.3f-%.3f,%.3f' % (t['net'], t['x1'], t['y1'], t['x2'], t['y2']))
    # keep-outs
    for k in inp.get('keepouts', []):
        if k.get('layer') != layer: continue
        d = re.seg_rect(seg, (k['x0']+k['x1'])/2, (k['y0']+k['y1'])/2, k['x1']-k['x0'], k['y1']-k['y0'])
        upd(d, gap_for(None), 'keepout')
    # board edge
    ol = inp['outline']; e = inp.get('edge_clearance', 0.25)
    d = min(min(seg[0], seg[2]) - ol['x0'], ol['x1'] - max(seg[0], seg[2]),
            min(seg[1], seg[3]) - ol['y0'], ol['y1'] - max(seg[1], seg[3]))
    upd(d, e, 'edge')
    return best, who
