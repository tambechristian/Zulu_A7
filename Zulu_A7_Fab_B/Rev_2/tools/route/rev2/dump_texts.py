"""List silkscreen texts and graphics near the X2 landings (KiCad python): python dump_texts.py <PcbDoc>"""
import sys, wx, pcbnew
app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(sys.argv[1], None)
mm = pcbnew.ToMM
c = b.GetBoardEdgesBoundingBox().GetCenter(); cx, cy = mm(c.x), -mm(c.y)
rel = lambda x, y: (round(mm(x) - cx + 34.925, 3), round(-mm(y) - cy + 12.7, 3))
items = []
for d in b.GetDrawings():
    if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        bb = d.GetBoundingBox(); x0, y1 = rel(bb.GetLeft(), bb.GetTop()); x1, y0 = rel(bb.GetRight(), bb.GetBottom())
        items.append((d.GetClass(), b.GetLayerName(d.GetLayer()), getattr(d, 'GetText', lambda: '')(), x0, y0, x1, y1))
for fp in b.GetFootprints():
    for d in list(fp.GraphicalItems()) + [fp.Reference()]:
        if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and fp.GetReference() in ('X1', 'X4', 'X2'):
            bb = d.GetBoundingBox(); x0, y1 = rel(bb.GetLeft(), bb.GetTop()); x1, y0 = rel(bb.GetRight(), bb.GetBottom())
            items.append((fp.GetReference() + ':' + d.GetClass(), b.GetLayerName(d.GetLayer()), getattr(d, 'GetText', lambda: '')(), x0, y0, x1, y1))
for it in items:
    if 20 < (it[3] + it[5]) / 2 < 42 and ((it[4] + it[6]) / 2 > 17 or (it[4] + it[6]) / 2 < 8):
        print('%-22s %-10s %-12r x %.2f..%.2f y %.2f..%.2f' % (it[0], it[1], it[2], it[3], it[5], it[4], it[6]))
