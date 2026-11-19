"""Exact clearance probe for hand-routed copper against a router model.
check(M, objs) -> list of (obj, other, gap) where gap < required.  objs: tracks {'net','layer','w','x1','y1','x2','y2'}
and vias {'net','x','y','size','hole','span'}."""
import math
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
CLR = 0.09


def seg_seg(a, b):
    def pd(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
        return math.hypot(px - x1 - u * dx, py - y1 - u * dy)
    (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2) = a, b
    def ccw(A, B, Cc):
        return (Cc[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (Cc[0] - A[0])
    A, B, Cc, D = (ax1, ay1), (ax2, ay2), (bx1, by1), (bx2, by2)
    if ccw(A, Cc, D) != ccw(B, Cc, D) and ccw(A, B, Cc) != ccw(A, B, D):
        return 0.0
    return min(pd(ax1, ay1, *b), pd(ax2, ay2, *b), pd(bx1, by1, *a), pd(bx2, by2, *a))


def seg_box(s, b):
    x1, y1, x2, y2 = s
    if b[0] <= x1 <= b[2] and b[1] <= y1 <= b[3]:
        return 0.0
    edges = [(b[0], b[1], b[2], b[1]), (b[2], b[1], b[2], b[3]), (b[2], b[3], b[0], b[3]), (b[0], b[3], b[0], b[1])]
    return min(seg_seg(s, e) for e in edges)


def shape(o):
    """('seg', (x1,y1,x2,y2), r) or ('box', box, 0) per layer list"""
    if 'layer' in o:
        return [o['layer']], ('seg', (o['x1'], o['y1'], o['x2'], o['y2']), o['w'] / 2)
    if 'ref' in o:
        L = o['layers'] or STACK
        if o['shape'] == 'circle':
            return L, ('seg', (o['x'], o['y'], o['x'], o['y']), o['w'] / 2)
        return L, ('box', (o['x'] - o['w'] / 2, o['y'] - o['h'] / 2, o['x'] + o['w'] / 2, o['y'] + o['h'] / 2), 0)
    return o['span'], ('seg', (o['x'], o['y'], o['x'], o['y']), o['size'] / 2)


def dist(a, b):
    (ka, ga, ra), (kb, gb, rb) = a, b
    if ka == 'seg' and kb == 'seg':
        d = seg_seg(ga, gb)
    elif ka == 'seg':
        d = seg_box(ga, gb)
    elif kb == 'seg':
        d = seg_box(gb, ga)
    else:
        d = max(0, max(ga[0] - gb[2], gb[0] - ga[2]), max(ga[1] - gb[3], gb[1] - ga[3]))
    return d - ra - rb


def check(M, objs, clr=CLR, plane_nets=('GND', 'VCC3V3')):
    out = []
    others = [o for o in M['pads'] + M['tracks'] + M['vias']]
    for o in objs:
        Lo, so = shape(o)
        for q in others:
            if q.get('net') == o['net'] and q.get('net'):
                continue
            Lq, sq = shape(q)
            com = [l for l in Lo if l in Lq and l not in ('L2-GND', 'L5-VCC3V3')]
            # planes: a via crossing a plane layer gets an antipad, no conflict modelled here
            if not com:
                continue
            g = dist(so, sq)
            if g < clr - 1e-6:
                out.append((round(g, 3), q.get('net'), q.get('ref', ''), q.get('pad', ''), com[0][:6], shape(q)[1]))
        # hole to hole
        if 'hole' in o:
            for q in M['vias'] + [p for p in M['pads'] if p.get('drill')]:
                h = q.get('hole') or q.get('drill')
                sp = q.get('span') or STACK
                if set(sp) & set(o['span']) and not (abs(q['x'] - o['x']) < 1e-6 and abs(q['y'] - o['y']) < 1e-6):
                    g = math.hypot(q['x'] - o['x'], q['y'] - o['y']) - h / 2 - o['hole'] / 2
                    if g < 0.24:
                        out.append((round(g, 3), q.get('net'), 'HOLE', '', '', (q['x'], q['y'])))
        if 'layer' in o:
            for x, y in ((o['x1'], o['y1']), (o['x2'], o['y2'])):
                if min(x, y, 60.96 - x, 25.4 - y) < 0.30 + o['w'] / 2:
                    out.append(('edge', x, y))
    return out
