"""Read the saved PcbDoc directly (read-only) and compare the SDRAM nets' tracks / vias / arcs with tools/route/model.json."""
import sys, os, struct, json, math, collections
import olefile
sys.path.insert(0, '../..')
import bus_sim as B

PCB = os.path.join(B.ROOT, 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc')
U = 2.54e-6
LAYER = {1: 'Top Layer', 2: 'L3-SIG', 3: 'L4-SIG', 4: 'L2-GND', 5: 'L5-VCC3V3', 32: 'Bottom Layer', 74: 'Multi'}
STACK = B.ORDER


def kvs(f, stream, key):
    d = f.openstream(stream).read()
    out, i, idx = {}, 0, 0
    while i + 4 <= len(d):
        ln = struct.unpack('<I', d[i:i + 4])[0]
        s = d[i + 4:i + 4 + ln].decode('latin-1').strip('\x00')
        i += 4 + ln
        kv = {}
        for part in s.split('|'):
            if '=' in part:
                k, v = part.split('=', 1)
                kv[k.upper()] = v
        out[idx] = kv
        idx += 1
    return out


f = olefile.OleFileIO(PCB)
nets = {i: kv.get('NAME') for i, kv in kvs(f, 'Nets6/Data', 'NAME=').items()}
want = set(B.NETS)


def records(stream, typ):
    d = f.openstream(stream).read()
    i = 0
    while i + 5 <= len(d):
        t = d[i]
        ln = struct.unpack('<I', d[i + 1:i + 5])[0]
        b = d[i + 5:i + 5 + ln]
        i += 5 + ln
        if t == typ:
            yield b


tracks = collections.defaultdict(list)
for b in records('Tracks6/Data', 4):
    n = struct.unpack('<h', b[3:5])[0]
    if nets.get(n) in want and b[0] in LAYER:
        x1, y1, x2, y2, w = [struct.unpack('<i', b[k:k + 4])[0] * U for k in (13, 17, 21, 25, 29)]
        tracks[nets[n]].append((LAYER[b[0]], round(w, 4), round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)))
vias = collections.defaultdict(list)
for b in records('Vias6/Data', 3):
    n = struct.unpack('<h', b[3:5])[0]
    if nets.get(n) in want:
        lo, hi = sorted((STACK.index(LAYER[b[29]]), STACK.index(LAYER[b[30]])))
        vias[nets[n]].append((round(struct.unpack('<i', b[13:17])[0] * U, 4), round(struct.unpack('<i', b[17:21])[0] * U, 4),
                              round(struct.unpack('<i', b[21:25])[0] * U, 4), round(struct.unpack('<i', b[25:29])[0] * U, 4), tuple(STACK[lo:hi + 1])))
arcs = collections.defaultdict(list)
try:
    for b in records('Arcs6/Data', 1):
        n = struct.unpack('<h', b[3:5])[0]
        if nets.get(n) in want:
            r = struct.unpack('<i', b[21:25])[0] * U
            a0, a1 = struct.unpack('<d', b[25:33])[0], struct.unpack('<d', b[33:41])[0]
            sweep = (a1 - a0) % 360
            arcs[nets[n]].append((LAYER.get(b[0], b[0]), round(r, 4), round(sweep, 2), round(r * math.radians(sweep), 4)))
except Exception as e:
    print('arcs:', e)
f.close()

M = json.load(open(B.MODEL))
bad = 0
for net in B.NETS:
    mt = sorted((t['layer'], round(t['w'], 4), round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4)) for t in M['tracks'] if t['net'] == net)
    pt = sorted(tracks[net])
    mv = sorted((round(v['x'], 4), round(v['y'], 4), round(v['size'], 4), round(v['hole'], 4), tuple(v['span'])) for v in M['vias'] if v['net'] == net)
    pv = sorted(vias[net])
    Lp = sum(math.hypot(t[4] - t[2], t[5] - t[3]) for t in pt) + sum(a[3] for a in arcs[net])
    same_t = mt == pt
    same_v = mv == pv
    if not (same_t and same_v and not arcs[net]):
        bad += 1
        print('%-10s tracks %s (model %d / pcb %d) vias %s arcs %s' % (net, same_t, len(mt), len(pt), same_v, arcs[net]))
        if not same_t:
            print('   only model:', [t for t in mt if t not in pt][:6]); print('   only pcb  :', [t for t in pt if t not in mt][:6])
    if net in ('SDRAM-CLK', 'D0', 'A9', 'WE#'):
        print('%-10s PcbDoc routed length %.3f mm = %.1f mil; tracks %d, vias %d, arcs %d' % (net, Lp, Lp / 0.0254, len(pt), len(pv), len(arcs[net])))
print('nets differing from model.json:', bad)
