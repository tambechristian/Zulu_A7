"""Dump asar_feather.PcbDoc for the board pictures (tools/board_pictures.py), 2026-11-18. READ-ONLY on the board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" -u tools/picture_dump.py      -> tools/picture_dump.json

Read through KiCad's Altium importer. Coordinates are board mm, origin at the board's lower-left corner (the edge
lines' centres), y up, seen from the top (the bottom picture mirrors them itself). The silk TEXTS are not dumped:
KiCad redraws Altium's stroke font in its own font, so board_pictures.py reads them from the PcbDoc's Texts6.

  board     w, h, outline (polygon), md5 of the PcbDoc read
  parts     ref, value, footprint, side (top | bottom), x, y, rot, body (Mechanical 3 extent: this board's body layer,
            see docs/x1_microb.md; for Q1 it holds copies of the lands, not a body), body_poly (the Mechanical 3 lines
            as one closed outline, or None), court (Mechanical 7 extent), flange (extent of the Mechanical 7 lines
            that have a width: on X1 that is its front flange, its courtyard lines have none; on other parts it is
            just their courtyard, so the renderer reads it for X1 only)
  pads      ref, pad, net, side (top | bottom | both), x, y, poly (copper outline on its own side), drill (0 = SMD),
            slot (w, h) for oblong holes, plated
  tracks    layer (top | bottom), w, x1, y1, x2, y2 (arcs become chords)
  vias      x, y, size, hole, top / bottom (true when the via reaches that outer layer)
  silk      side (top | bottom), w, x1, y1, x2, y2, owner: every overlay line (footprint graphics and free lines)
"""
import hashlib
import json
import os

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')
OUT = os.path.join(HERE, 'picture_dump.json')
OVERLAY = {'Top Overlay': 'top', 'Bottom Overlay': 'bottom'}


def main():
    app = wx.App(False)  # noqa: F841 -- the importer needs one
    wx.Log.SetActiveTarget(wx.LogStderr())
    wx.Log.SetLogLevel(0)
    b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
    mm = pcbnew.ToMM
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, True)
    ob = outline.BBox()                                  # edge-line centres (the edge box adds the line width)
    X0, Y1 = mm(ob.GetLeft()), mm(ob.GetBottom())

    def pt(p):
        return (round(mm(p.x) - X0, 4), round(Y1 - mm(p.y), 4))

    def box(e):
        (x0, y0), (x1, y1) = pt(pcbnew.VECTOR2I(e.GetLeft(), e.GetBottom())), pt(pcbnew.VECTOR2I(e.GetRight(), e.GetTop()))
        return [x0, x1, y0, y1]

    def merge(bs):
        if not bs:
            return None
        return [min(q[0] for q in bs), max(q[1] for q in bs), min(q[2] for q in bs), max(q[3] for q in bs)]

    lname = b.GetLayerName
    o = outline.Outline(0)
    out = {'board': {'w': round(mm(ob.GetWidth()), 4), 'h': round(mm(ob.GetHeight()), 4),
                     'outline': [pt(o.CPoint(k)) for k in range(o.PointCount())],
                     'md5': hashlib.md5(open(BOARD, 'rb').read()).hexdigest()},
           'parts': [], 'pads': [], 'tracks': [], 'vias': [], 'silk': []}
    skipped = []

    def silk(g, owner):
        L = lname(g.GetLayer())
        if L not in OVERLAY or g.GetClass() != 'PCB_SHAPE':
            return
        if g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            skipped.append('%s %s %s' % (owner or 'board', L, g.GetShapeStr()))
            return
        (x1, y1), (x2, y2) = pt(g.GetStart()), pt(g.GetEnd())
        out['silk'].append({'side': OVERLAY[L], 'w': round(mm(g.GetWidth()), 4), 'x1': x1, 'y1': y1, 'x2': x2,
                            'y2': y2, 'owner': owner})

    for fp in b.GetFootprints():
        ref = fp.GetReference()
        bodies, courts, flange, segs = [], [], [], []
        for g in fp.GraphicalItems():
            if g.GetClass() != 'PCB_SHAPE':
                continue
            silk(g, ref)
            if lname(g.GetLayer()) == 'Mechanical 3':
                bodies.append(box(g.GetBoundingBox()))
                if g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
                    segs.append((pt(g.GetStart()), pt(g.GetEnd())))
                elif g.GetShape() == pcbnew.SHAPE_T_RECTANGLE:
                    (ax_, ay), (bx, by) = pt(g.GetStart()), pt(g.GetEnd())
                    segs += [((ax_, ay), (bx, ay)), ((bx, ay), (bx, by)), ((bx, by), (ax_, by)), ((ax_, by), (ax_, ay))]
            elif lname(g.GetLayer()) == 'Mechanical 7':
                courts.append(box(g.GetBoundingBox()))
                if g.GetShape() == pcbnew.SHAPE_T_SEGMENT and g.GetWidth() > 0:
                    (x1, y1), (x2, y2) = pt(g.GetStart()), pt(g.GetEnd())
                    flange.append([min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)])
        x, y = pt(fp.GetPosition())
        out['parts'].append({'ref': ref, 'value': fp.GetValue(), 'footprint': fp.GetFPID().GetLibItemName().wx_str(),
                             'side': 'bottom' if fp.IsFlipped() else 'top', 'x': x, 'y': y,
                             'rot': round(fp.GetOrientationDegrees(), 3), 'body': merge(bodies),
                             'body_poly': chain(segs), 'court': merge(courts), 'flange': merge(flange)})
        for p in fp.Pads():
            on_f, on_b = p.IsOnLayer(pcbnew.F_Cu), p.IsOnLayer(pcbnew.B_Cu)
            side = 'both' if on_f and on_b else ('top' if on_f else 'bottom')
            layer = pcbnew.F_Cu if on_f else pcbnew.B_Cu
            ps = pcbnew.SHAPE_POLY_SET()
            p.TransformShapeToPolygon(ps, layer, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
            polys = []
            for i in range(ps.OutlineCount()):
                po = ps.Outline(i)
                polys.append([pt(po.CPoint(k)) for k in range(po.PointCount())])
            ds = p.GetDrillSize()
            drill = round(mm(min(ds.x, ds.y)), 4) if p.HasHole() else 0
            slot = [round(mm(ds.x), 4), round(mm(ds.y), 4)] if p.HasHole() and ds.x != ds.y else None
            if slot and round(p.GetOrientationDegrees()) % 180 == 90:
                slot = slot[::-1]
            px, py = pt(p.GetPosition())
            out['pads'].append({'ref': ref, 'pad': p.GetNumber(), 'net': p.GetNetname(), 'side': side, 'x': px,
                                'y': py, 'poly': polys, 'drill': drill, 'slot': slot,
                                'plated': p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH})

    for t in b.GetTracks():
        c = t.GetClass()
        if c == 'PCB_VIA':
            x, y = pt(t.GetPosition())
            out['vias'].append({'x': x, 'y': y, 'size': round(mm(t.GetWidth(pcbnew.F_Cu)), 4),
                                'hole': round(mm(t.GetDrillValue()), 4), 'top': t.TopLayer() == pcbnew.F_Cu,
                                'bottom': t.BottomLayer() == pcbnew.B_Cu})
            continue
        if t.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        (x1, y1), (x2, y2) = pt(t.GetStart()), pt(t.GetEnd())
        out['tracks'].append({'layer': 'top' if t.GetLayer() == pcbnew.F_Cu else 'bottom', 'w': round(mm(t.GetWidth()), 4),
                              'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})

    for d in b.GetDrawings():
        silk(d, '')

    json.dump(out, open(OUT, 'w'), indent=0)
    nv = len(out['vias'])
    print('%d parts, %d pads, %d tracks, %d vias (%d reach Top, %d reach Bottom), %d silk lines -> %s (board md5 %s)' % (
        len(out['parts']), len(out['pads']), len(out['tracks']), nv, sum(v['top'] for v in out['vias']),
        sum(v['bottom'] for v in out['vias']), len(out['silk']), OUT, out['board']['md5'][:8]))
    if skipped:
        print('WARNING: overlay shapes not drawn (only lines are):', '; '.join(skipped))


def chain(segs):
    """The Mechanical 3 line segments as one closed outline (X4's notched housing, X1's shell), else None. Arcs
    (X1's slot caps) are left out."""
    if len(segs) < 3:
        return None
    key = lambda q: (round(q[0], 3), round(q[1], 3))  # noqa: E731
    left = [(key(a), key(b)) for a, b in segs]
    a, b = left.pop(0)
    poly = [a, b]
    while left:
        nxt = [k for k, (c, d) in enumerate(left) if poly[-1] in (c, d)]
        if not nxt:
            return None
        c, d = left.pop(nxt[0])
        poly.append(d if c == poly[-1] else c)
    return poly[:-1] if poly[-1] == poly[0] else None


if __name__ == '__main__':
    main()
