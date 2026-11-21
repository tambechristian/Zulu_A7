import json, math, collections, re
exec(open('build.py').read())
M2 = json.load(open('candidate_model.json')); moves = json.load(open('moves.json'))
moved = set(moves)
oldp = [p for p in M['pads'] if p['ref'] in moved]
newp = [p for p in M2['pads'] if p['ref'] in moved]
POWER = {'GND','VCC3V3','VCC1V0','VCC1V8','VCC1V2','VCCAUX','VCCADC','GNDADC','FT-VCORE','FT-VPHY','FT-VPLL','VBATT','USB5V0','VU'}
def is_power(n): return n in POWER or n.startswith('VCC')
sig = sorted({p['net'] for p in oldp if p['net'] and not is_power(p['net'])})
pw = sorted({p['net'] for p in oldp if p['net'] and is_power(p['net'])})
def L(t): return math.hypot(t['x2']-t['x1'], t['y2']-t['y1'])
bynet = collections.defaultdict(list); vbynet = collections.defaultdict(list)
for t in M['tracks']: bynet[t['net']].append(t)
for v in M['vias']: vbynet[v['net']].append(v)
def near(x, y, pads, m):
    for p in pads:
        if abs(x-p['x']) <= p['w']/2+m and abs(y-p['y']) <= p['h']/2+m: return True
    return False
# 1) signal nets: whole-net rip
tot = 0; nv = 0; rows = []
for n in sig:
    l = sum(L(t) for t in bynet[n]); tot += l; nv += len(vbynet[n]); rows.append((n, round(l, 2), len(vbynet[n])))
# 2) power nets: copper within 1.0 mm of a moved pad (old position) = fan-out stubs and their vias
ptot = 0; pnv = 0; prow = []
for n in pw:
    ts = [t for t in bynet[n] if near(t['x1'], t['y1'], oldp, 1.0) or near(t['x2'], t['y2'], oldp, 1.0)]
    vs = [v for v in vbynet[n] if near(v['x'], v['y'], oldp, 1.0)]
    l = sum(L(t) for t in ts); ptot += l; pnv += len(vs); prow.append((n, round(l, 2), len(vs)))
# 3) foreign copper under the NEW pads (same side), nets not already ripped, clearance 0.1 mm
ripped = set(sig)
def seg_box_gap(t, b):
    # sample the segment
    n = max(2, int(L(t)/0.05)); g = 9
    for i in range(n+1):
        x = t['x1']+(t['x2']-t['x1'])*i/n; y = t['y1']+(t['y2']-t['y1'])*i/n
        dx = max(b[0]-x, 0, x-b[2]); dy = max(b[1]-y, 0, y-b[3]); g = min(g, math.hypot(dx, dy)-t['w']/2)
    return g
fx_t = collections.defaultdict(float); fx_v = collections.Counter(); fx_nets = set()
for p in newp:
    b = box(p); lays = set(p['layers'] or bc.STACK)
    for t in M['tracks']:
        if t['net'] in ripped or t['layer'] not in lays: continue
        if t['net'] == p['net'] and t['net'] in POWER: continue
        if max(t['x1'],t['x2'])+1 < b[0] or min(t['x1'],t['x2'])-1 > b[2] or max(t['y1'],t['y2'])+1 < b[1] or min(t['y1'],t['y2'])-1 > b[3]: continue
        if seg_box_gap(t, b) < 0.1:
            k = (t['net'], t['layer'], t['x1'], t['y1'], t['x2'], t['y2'])
            if k not in fx_t: fx_t[k] = L(t)
    for v in M['vias']:
        if v['net'] in ripped or not (set(v['span']) & lays) and not ('Top Layer' in lays and v['span'][0]=='Top Layer'): continue
        sp = v['span']; i0, i1 = bc.STACK.index(sp[0]), bc.STACK.index(sp[-1])
        vl = set(bc.STACK[i0:i1+1])
        if not (vl & lays): continue
        dx = max(b[0]-v['x'], 0, v['x']-b[2]); dy = max(b[1]-v['y'], 0, v['y']-b[3])
        if math.hypot(dx, dy) - v['size']/2 < 0.1 and not (v['net'] == p['net'] and p['net'] in POWER):
            fx_v[(v['net'], v['x'], v['y'])] += 1
fnets = collections.Counter([k[0] for k in fx_t] + [k[0] for k in fx_v])
SI = lambda n: ('USB' in n or n.startswith('SDRAM') or re.fullmatch(r'D\d+', n) or 'CLK' in n or n.startswith('FLASH') or n in ('TCK','TMS','TDI','TDO') or n.startswith('FPGA-T'))
out = dict(signal_nets=len(sig), signal_track_mm=round(tot, 1), signal_vias=nv,
           signal_SI=[r for r in rows if SI(r[0])], power_stub_mm=round(ptot, 1), power_stub_vias=pnv, power=prow,
           foreign_track_segments=len(fx_t), foreign_track_mm=round(sum(fx_t.values()), 1), foreign_vias=len(fx_v),
           foreign_nets=sorted(fnets.items(), key=lambda kv: -kv[1]))
json.dump(dict(out, signal=rows), open('rip_report.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('power',)}, indent=None)[:6000])
print('power', prow)
print('board total track mm', round(sum(L(t) for t in M['tracks']), 1), 'vias', len(M['vias']))
