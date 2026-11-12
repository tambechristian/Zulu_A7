"""Strategy D step 1: hand-built USB pair + the extra rips it needs.  Writes D/usb_plan.json (rip + extra rip + USB
copper + relocated U10 GND/VCC3V3 ties) and D/extra_rip.json."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, '..', 'prep', 'rip.json')))
M = json.load(open(os.path.join(HERE, '..', 'prep', 'base_moved.json')))
TOP = 'Top Layer'
W = 0.15

def poly(net, pts, layer=TOP, w=W):
    return [dict(net=net, layer=layer, w=w, x1=round(a[0], 4), y1=round(a[1], 4), x2=round(b[0], 4), y2=round(b[1], 4))
            for a, b in zip(pts, pts[1:]) if a != b]

def L(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))

XP, XN = 27.0, 26.70          # vertical runs west of MH1
A = 0.25; B = A + 0.3 * (2 - math.sqrt(2)) / math.sqrt(2) * 0 + 0.17574  # outer chamfer = inner + 0.3*(sqrt2-1)*... (0.1757)
P = [(30.48, 21.2585), (30.75, 21.2585), (30.75, 22.1879), (30.5879, 22.35), (XP + A, 22.35), (XP, 22.35 - A),
     (XP, 45.0446 - XP), (27.7825, 17.2621), (27.7825, 14.4079), (27.3946, 14.02), (25.775, 14.02), (25.775, 13.85)]
N = [(31.13, 21.2585), (31.05, 21.2585), (31.05, 22.3121), (30.7121, 22.65), (XN + B, 22.65), (XN, 22.65 - B),
     (XN, 44.6204 - XN), (27.4825, 17.1379), (27.4825, 14.5321), (27.2704, 14.32), (25.775, 14.32), (25.775, 14.3501)]
import sys
bump = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
if bump:
    # length-match bump on D_P's horizontal run, toward the X1 pads (-y); 45 deg flanks of rise h add 2h(sqrt2-1)
    h = bump / (2 * (math.sqrt(2) - 1))
    x0 = 29.70
    i = P.index((30.5879, 22.35)) + 1
    P[i:i] = [(x0, 22.35), (x0 - h, 22.35 - h), (x0 - h - 0.1, 22.35 - h), (x0 - 2 * h - 0.1, 22.35)]
print('D_P %.4f  D_N %.4f  diff %.4f' % (L(P), L(N), L(P) - L(N)))
json.dump({'P': P, 'N': N}, open(os.path.join(HERE, 'usb_pts.json'), 'w'))

def key(t): return (t['net'],t['layer'],frozenset([(round(t['x1'],3),round(t['y1'],3)),(round(t['x2'],3),round(t['y2'],3))]))
def near(v,x,y): return abs(v['x']-x)<0.002 and abs(v['y']-y)<0.002
extra_t=[t for t in M['tracks'] if t['net']=='CHAN10' and t['layer']==TOP and min(t['x1'],t['x2'])>21 and min(t['x1'],t['x2'])<28]
extra_t+=[t for t in M['tracks'] if t['net']=='GND' and t['layer']=='Bottom Layer' and key(t)==key(dict(net='GND',layer='Bottom Layer',x1=27.215,y1=21.9,x2=27.215,y2=22.505))]
extra_v=[v for v in M['vias'] if v['net']=='CHAN10' and (near(v,27.9,22.45) or near(v,21.25,22.9)) and v['span'][-1]!='L4-SIG']
extra_v+=[v for v in M['vias'] if (v['net']=='GND' and near(v,27.215,21.9)) or (v['net']=='VCC3V3' and near(v,27.22,19.22))]
print('extra rip', len(extra_t), len(extra_v))
for t in extra_t: print('  ',t)
for v in extra_v: print('  ',v)
json.dump({'remove':extra_t,'remove_vias':extra_v},open(os.path.join(HERE,'extra_rip.json'),'w'),indent=1)
STACK=['Top Layer','L2-GND','L3-SIG','L4-SIG','L5-VCC3V3','Bottom Layer']
ties_t=[dict(net='GND',layer='Bottom Layer',w=0.3,x1=26.0,y1=21.9,x2=26.4,y2=22.4)]
ties_v=[dict(net='GND',x=26.0,y=21.9,size=0.35,hole=0.2,span=STACK),
        dict(net='VCC3V3',x=27.22,y=19.22,size=0.3,hole=0.15,span=['L5-VCC3V3','Bottom Layer'])]
usb=poly('USB_D_P',P)+poly('USB_D_N',N)
json.dump({'tracks':usb,'vias':[]},open(os.path.join(HERE,'usb_tracks.json'),'w'),indent=1)
json.dump({'tracks':ties_t,'vias':ties_v},open(os.path.join(HERE,'ties.json'),'w'),indent=1)
plan={'remove':R['remove']+extra_t,'remove_vias':R['remove_vias']+extra_v,'tracks':usb+ties_t,'vias':ties_v}
json.dump(plan,open(os.path.join(HERE,'usb_plan.json'),'w'),indent=1)
print('D_P %.4f  D_N %.4f  diff %.4f' % (L(P), L(N), L(P) - L(N)))
