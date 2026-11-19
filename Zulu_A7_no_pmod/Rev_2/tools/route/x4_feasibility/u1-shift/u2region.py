exec(open('geo.py').read())
top = bc.build(M, D)['Top']
U2p = [p for p in M['pads'] if p['ref']=='U2']
U2b = top['U2']['body'][0]
fixed = ['X1','X2','X3','BTN','C158','LD0','LD1','LD2','LD3','LD4','C159','C155']
def clear(dx, dy, cx):
    pads, body = s2b(cx)
    ub = (U2b[0]+dx, U2b[1]+dy, U2b[2]+dx, U2b[3]+dy)
    up = [dict(p, x=p['x']+dx, y=p['y']+dy) for p in U2p]
    w = 9
    # board edges
    for p in up:
        b = box(p); w = min(w, b[0]-0.3, b[1]-0.3, W-0.3-b[2], H-0.3-b[3])
    for q in pads:
        for p in up: w = min(w, bc.gap(box(p), box(q)) - 0.2)
        w = min(w, bc.gap(ub, box(q)) - 0.1)
    for p in up: w = min(w, bc.gap(box(p), body) - 0.1)
    w = min(w, bc.gap(ub, body) - 0.1)
    for ref in fixed:
        v = top[ref]
        for pb, p in v['pads']:
            for u in up: w = min(w, pgap(p, box(u)) - 0.2)
            w = min(w, pgap(p, ub) - 0.1)
        for b in v['body']:
            w = min(w, bc.gap(b, ub) - 0.1)
            for u in up: w = min(w, bc.gap(b, box(u)) - 0.1)
        if w < 0: return w
    return w
if __name__ == '__main__':
    print('as placed, cx 30.48:', round(clear(0,0,30.48),3))
    res = {}
    for j in range(-60, 121, 5):
        dy = j/100*1.0*1
        dy = j*0.05
        best = None
        for cx in (29.20, 30.48, 31.76):
            for i in range(0, 400):
                dx = i*0.05
                if clear(dx, dy, cx) >= 0:
                    if best is None or dx < best[0]: best = (dx, cx)
                    break
            # also west
        bw = None
        for cx in (29.20, 30.48, 31.76):
            for i in range(0, 400):
                dx = -i*0.05
                if clear(dx, dy, cx) >= 0:
                    if bw is None or -dx < -bw[0]: bw = (dx, cx)
                    break
        print('dy %+5.2f  min east dx %s   min west dx %s' % (dy, best, bw))
