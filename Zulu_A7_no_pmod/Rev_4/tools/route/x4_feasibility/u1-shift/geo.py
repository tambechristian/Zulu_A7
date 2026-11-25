import json, math, sys
sys.path.insert(0, r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools')
import body_check as bc
T = r'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_4/tools/route/bodies/'
M = json.load(open(T + 'base.json')); D = json.load(open(T + 'comps.json'))
W, H = 60.96, 25.4
def box(p): return (p['x']-p['w']/2, p['y']-p['h']/2, p['x']+p['w']/2, p['y']+p['h']/2)
def circ_gap(p, b):
    # gap between circle pad p and box b (treat circle exactly)
    r = p['w']/2; dx = max(b[0]-p['x'], 0, p['x']-b[2]); dy = max(b[1]-p['y'], 0, p['y']-b[3])
    return math.hypot(dx, dy) - r
def pgap(p, b):
    if p.get('shape') == 'circle': return circ_gap(p, b)
    return bc.gap(box(p), b)
def s2b(cx, cy=4.9):
    pads = [dict(ref='J', pad='1', x=cx+1, y=cy+2.85, w=1.0, h=3.5), dict(ref='J', pad='2', x=cx-1, y=cy+2.85, w=1.0, h=3.5),
            dict(ref='J', pad='MP1', x=cx-3.35, y=cy-2.9, w=1.5, h=3.4), dict(ref='J', pad='MP2', x=cx+3.35, y=cy-2.9, w=1.5, h=3.4)]
    body = (cx-3.95, cy-4.4, cx+3.95, cy+3.2)
    return pads, body
