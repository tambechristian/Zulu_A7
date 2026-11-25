"""Top/Bottom overlay geometry + pads/bodies of a Zulu PcbDoc, for silk placement design. Read-only.
usage: python geom.py <PcbDoc> <model.json> <comps.json> <body_check dir> <out.json>"""
import sys, struct, json, olefile, math
U = 2.54e-6
pcb, model, comps_p, bc_dir, out = sys.argv[1:6]
sys.path.insert(0, bc_dir); import body_check
f = olefile.OleFileIO(pcb)
comps = []
for r in f.openstream('Components6/Data').read().decode('latin-1', 'replace').split(chr(0)):
    if 'PATTERN=' in r:
        comps.append(dict(x.split('=', 1) for x in r.strip('|').split('|') if '=' in x))
def ref(ci): return None if ci == 0xFFFF else comps[ci].get('SOURCEDESIGNATOR')
def recs(stream, nsub):
    d = f.openstream(stream).read(); i = 0
    while i + 5 <= len(d):
        t = d[i]; i += 1; subs = []
        for _ in range(nsub):
            n = struct.unpack('<I', d[i:i + 4])[0]; subs.append(d[i + 4:i + 4 + n]); i += 4 + n
        yield t, subs
I = lambda b, o: struct.unpack('<i', b[o:o + 4])[0] * U
G = {'texts': [], 'tracks': [], 'arcs': [], 'fills': []}
for k, (t, (b, s)) in enumerate(recs('Texts6/Data', 2)):
    if b[0] not in (33, 34): continue
    ci = struct.unpack('<H', b[7:9])[0]
    txt = s[1:1 + s[0]].decode('latin-1', 'replace') if s else ''
    rec = dict(idx=k, layer=b[0], text=txt, ref=ref(ci), x=I(b, 13), y=I(b, 17), h=I(b, 21),
               rot=round(struct.unpack('<d', b[27:35])[0], 3) % 360, stroke=I(b, 36), kind='free')
    if ci != 0xFFFF:
        c = comps[ci]
        rec['kind'] = 'designator' if b[41] == 1 else 'comment'
        rec['shown'] = (c.get('NAMEON') if rec['kind'] == 'designator' else c.get('COMMENTON')) == 'TRUE'
    else:
        rec['shown'] = True
    n = len(txt); h = rec['h']; w = (n - 1) * h + 0.667 * h; e = rec['stroke'] / 2; x, y = rec['x'], rec['y']
    r = round(rec['rot']) % 360
    rec['box'] = [(x - e, y - e, x + w + e, y + h + e), (x - h - e, y - e, x + e, y + w + e),
                  (x - w - e, y - h - e, x + e, y + e), (x - e, y - w - e, x + h + e, y + e)][{0: 0, 90: 1, 180: 2, 270: 3}[r]]
    G['texts'].append(rec)
for t, (b,) in recs('Tracks6/Data', 1):
    if b[0] in (33, 34):
        G['tracks'].append(dict(layer=b[0], ref=ref(struct.unpack('<H', b[7:9])[0]), x1=I(b, 13), y1=I(b, 17), x2=I(b, 21), y2=I(b, 25), w=I(b, 29)))
for t, (b,) in recs('Arcs6/Data', 1):
    if b[0] in (33, 34):
        G['arcs'].append(dict(layer=b[0], ref=ref(struct.unpack('<H', b[7:9])[0]), cx=I(b, 13), cy=I(b, 17), r=I(b, 21),
                              a0=struct.unpack('<d', b[25:33])[0], a1=struct.unpack('<d', b[33:41])[0], w=I(b, 41)))
for t, (b,) in recs('Fills6/Data', 1):
    if b[0] in (33, 34):
        G['fills'].append(dict(layer=b[0], ref=ref(struct.unpack('<H', b[7:9])[0]), x1=I(b, 13), y1=I(b, 17), x2=I(b, 21), y2=I(b, 25),
                               rot=struct.unpack('<d', b[29:37])[0]))
M, D = json.load(open(model)), json.load(open(comps_p))
EXP = {'U1': 0.0, 'U2': 0.035, 'X3': 0.04}
G['pads'] = []
for p in M['pads']:
    L = p['layers'] or ['Top Layer', 'Bottom Layer']
    for side, lay in (('Top', 'Top Layer'), ('Bottom', 'Bottom Layer')):
        if lay in L:
            e = EXP.get(p.get('ref'), 0.05)
            G['pads'].append(dict(side=side, ref=p.get('ref'), pad=p['pad'], net=p['net'], shape=p['shape'], x=p['x'], y=p['y'], w=p['w'], h=p['h'],
                                  drill=p.get('drill', 0), mask=[p['x'] - p['w'] / 2 - e, p['y'] - p['h'] / 2 - e, p['x'] + p['w'] / 2 + e, p['y'] + p['h'] / 2 + e]))
G['vias'] = [v for v in M['vias'] if 'Top Layer' in v['span'] or 'Bottom Layer' in v['span'] or v['span'] == ['Top Layer', 'Bottom Layer']]
P = body_check.build(M, D)
G['bodies'] = {s: {r: [list(b) for b in v['body']] for r, v in P[s].items() if v['body']} for s in P}
G['comps'] = D['comps']
G['board'] = M.get('board')
json.dump(G, open(out, 'w'), indent=0)
print(out, {k: len(v) for k, v in G.items() if isinstance(v, (list, dict))})
