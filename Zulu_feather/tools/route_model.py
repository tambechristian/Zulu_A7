"""Router stage 3 (2026-10-24): the board as the router sees it, read from the saved zulu_feather.PcbDoc.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route_model.py        -> tools/route/model.json

Coordinates are board-relative mm (origin at the board's lower-left corner, from the board-edge box centre; the
board is 50.8 x 22.86 mm), y up. Layer names are the Altium ones (Top Layer, L2-GND, L3-SIG, L4-SIG, L5-VCC3V3,
Bottom Layer).

  pads    ref, pad, net, x, y, shape (circle | rect), w, h (axis-aligned extent after rotation; a rotated or
          rounded pad is modelled by its bounding box, which is conservative), layers, drill (0 for SMD),
          plated
  tracks  net, layer, w, x1, y1, x2, y2
  vias    net, x, y, size, hole, span (layer list, top to bottom)
  planes  {layer: net} for the two pours (they cover the board inside a 0.25 mm pullback)
  board   w, h
"""
import json
import os

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'Zulu_feather.PrjPcb', 'zulu_feather.PcbDoc')
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']


def main():
    app = wx.App(False)  # noqa: F841
    wx.Log.SetActiveTarget(wx.LogStderr())
    b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
    mm = pcbnew.ToMM
    c = b.GetBoardEdgesBoundingBox().GetCenter()
    cx, cy = mm(c.x), -mm(c.y)
    def rel(x, y):
        return round(mm(x) - cx + 25.4, 4), round(-mm(y) - cy + 11.43, 4)
    lid = {b.GetLayerName(l): l for l in b.GetEnabledLayers().CuStack()}
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            layers = [n for n in STACK if p.IsOnLayer(lid[n])]
            if not layers and p.GetDrillSizeX() == 0:
                continue
            bb = p.GetBoundingBox()
            x0, y1 = rel(bb.GetLeft(), bb.GetTop())
            x1, y0 = rel(bb.GetRight(), bb.GetBottom())
            px, py = rel(p.GetPosition().x, p.GetPosition().y)
            shape = 'circle' if p.GetShape(lid[layers[0]] if layers else pcbnew.F_Cu) == pcbnew.PAD_SHAPE_CIRCLE else 'rect'
            pads.append({'ref': fp.GetReference(), 'pad': p.GetNumber(), 'net': p.GetNetname(), 'x': px, 'y': py,
                         'shape': shape, 'w': round(x1 - x0, 4), 'h': round(y1 - y0, 4), 'layers': layers,
                         'drill': round(mm(max(p.GetDrillSizeX(), p.GetDrillSizeY())), 4),
                         'plated': p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH})
    tracks, vias = [], []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            x, y = rel(t.GetPosition().x, t.GetPosition().y)
            a, z = STACK.index(b.GetLayerName(t.TopLayer())), STACK.index(b.GetLayerName(t.BottomLayer()))
            vias.append({'net': t.GetNetname(), 'x': x, 'y': y, 'size': round(mm(t.GetWidth(pcbnew.F_Cu)), 4),
                         'hole': round(mm(t.GetDrillValue()), 4), 'span': STACK[min(a, z):max(a, z) + 1]})
        else:
            (x1, y1), (x2, y2) = rel(t.GetStart().x, t.GetStart().y), rel(t.GetEnd().x, t.GetEnd().y)
            tracks.append({'net': t.GetNetname(), 'layer': b.GetLayerName(t.GetLayer()), 'w': round(mm(t.GetWidth()), 4),
                           'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
    planes = {b.GetLayerName(z.GetLayer()): z.GetNetname() for z in b.Zones() if z.IsOnCopperLayer()}
    out = {'board': {'w': 50.8, 'h': 22.86}, 'planes': planes, 'pads': pads, 'tracks': tracks, 'vias': vias}
    os.makedirs(os.path.join(HERE, 'route'), exist_ok=True)
    json.dump(out, open(os.path.join(HERE, 'route', 'model.json'), 'w'))
    print('pads %d, tracks %d, vias %d, planes %s' % (len(pads), len(tracks), len(vias), planes))


if __name__ == '__main__':
    main()
