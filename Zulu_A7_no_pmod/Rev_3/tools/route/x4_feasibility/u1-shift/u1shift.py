exec(open('geo.py').read())
P = bc.build(M, D)
U1b = P['Top']['U1']['body'][0]
# U1 group on Bottom = parts whose body centre lies inside U1's body footprint
grpB = [r for r, v in P['Bottom'].items() if v['body'] and U1b[0] <= (v['body'][0][0]+v['body'][0][2])/2 <= U1b[2] and U1b[1] <= (v['body'][0][1]+v['body'][0][3])/2 <= U1b[3]]
print('U1 bottom group:', sorted(grpB))
def shifted(v, dx, dy):
    return {'pads': [((b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy), dict(p, x=p['x']+dx, y=p['y']+dy)) for b,p in v['pads']],
            'body': [(b[0]+dx,b[1]+dy,b[2]+dx,b[3]+dy) for b in v['body']]}
def blockers(dx, dy, group={'Top':['U1'], 'Bottom':grpB}, ignore=set(), pp=0.2, bb=0.1):
    out = {}
    for s in ('Top','Bottom'):
        mov = [shifted(P[s][r], dx, dy) for r in group[s] if r in P[s]]
        # through-hole pads of U1? none. include board edges
        for m in mov:
            for b,p in m['pads']:
                e = min(b[0]-0.3, b[1]-0.3, W-0.3-b[2], H-0.3-b[3])
                if e < 0: out['EDGE'] = min(out.get('EDGE',9), e)
        for r, v in P[s].items():
            if r in group[s] or r.split('[')[0] in ignore: continue
            w = 9
            for m in mov:
                for b,p in m['pads']:
                    for b2,p2 in v['pads']: w = min(w, pgap(p2, b) - pp)
                    for b2 in v['body']: w = min(w, bc.gap(b2, b) - bb)
                for b in m['body']:
                    for b2,p2 in v['pads']: w = min(w, pgap(p2, b) - bb)
                    for b2 in v['body']: w = min(w, bc.gap(b2, b) - bb)
            if w < 0: out[s+':'+r] = round(w, 3)
    return out
if __name__ == '__main__':
    for dx in (0.0, 0.25, 0.5, 0.75, 1.0, 2.0, 5.0, 9.0):
        print(dx, blockers(dx, 0))
