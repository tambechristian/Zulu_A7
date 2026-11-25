exec(open('v4.py').read().split("import collections\nprint")[0])
import collections
moved = {'C107','C108','C109','C110','C111','C112','C113','C114','C115','C119','C121','C122','C123','C140','C141','C142','C143','C144','C145','C146','C157','C85','C86','C89','C90','C91','C92','C93','C95','C96','C97','C98','Q1','R127','R128','R129','R130','R131','R132','R134','R25','U1','U2','U4','X4'}
allnets = collections.Counter(p['net'] for p in M['pads'])
def L(t): return math.hypot(t['x2']-t['x1'], t['y2']-t['y1'])
POWER_RE = re.compile(r'^(GND|GNDADC|VCC.*|FT-V.*|VBATT|USB5V0|VU|VIN.*|V\d.*)$')
oldp = [p for p in M['pads'] if p['ref'] in moved]; newp = [p for p in M2['pads'] if p['ref'] in moved]
mnets = {p['net'] for p in oldp if p['net']}
power = sorted(n for n in mnets if POWER_RE.match(n)); sig = sorted(n for n in mnets if not POWER_RE.match(n))
print('power nets on moved pads', power)
tl = collections.defaultdict(float); vc = collections.Counter()
for t in M['tracks']: tl[t['net']] += L(t)
for v in M['vias']: vc[v['net']] += 1
print('signal nets', len(sig), 'mm', round(sum(tl[n] for n in sig),1), 'vias', sum(vc[n] for n in sig))
print('board', round(sum(tl.values()),1), len(M['vias']))
# nets that have pads on moved parts AND on unmoved parts - all of them; list signal nets with every pad moved? irrelevant
# foreign copper conflicts with new pads (clearance 0.1), excluding ripped signal nets and same-net
def segd(t, s):
    n = max(2, int(L(t)/0.02)); best = 9
    for i in range(n+1):
        x = t['x1']+(t['x2']-t['x1'])*i/n; y = t['y1']+(t['y2']-t['y1'])*i/n
        c = ('c', x, y, t['w']/2)
        best = min(best, g_cr(c, s) if s[0]=='r' else math.hypot(x-s[1], y-s[2])-s[3]-t['w']/2)
    return best
def vlay(v):
    sp = v['span']; return set(STACK[STACK.index(sp[0]):STACK.index(sp[-1])+1])
conf = collections.defaultdict(lambda: [0, 0.0, 0])
SIGRIP = set(sig)
for p in newp:
    s = shp(p); pl = lays(p)
    for t in M['tracks']:
        if t['net'] in SIGRIP or t['net'] == p['net'] or t['layer'] not in pl: continue
        if min(t['x1'],t['x2']) > p['x']+3 or max(t['x1'],t['x2']) < p['x']-3 or min(t['y1'],t['y2']) > p['y']+3 or max(t['y1'],t['y2']) < p['y']-3: continue
        if segd(t, s) < 0.1:
            conf[t['net']][0] += 1; conf[t['net']][1] += L(t)
    for v in M['vias']:
        if v['net'] in SIGRIP or v['net'] == p['net'] or not (vlay(v) & pl): continue
        c = ('c', v['x'], v['y'], v['size']/2)
        d = g_cr(c, s) if s[0]=='r' else math.hypot(v['x']-s[1], v['y']-s[2])-s[3]-v['size']/2
        if d < 0.1: conf[v['net']][2] += 1
print('foreign copper conflicts with new pads (segments may repeat across pads):')
for n, c in sorted(conf.items(), key=lambda kv: -kv[1][1]): print('  ', n, c[0], round(c[1],2), c[2], 'POWER' if POWER_RE.match(n) else 'SIGNAL-NOT-RIPPED')
