# KiCad copy: X2 pin labels on the top silkscreen (2026-10-07), copied from KiCad's own import of the production
# Altium board after Zulu_Altium_VS_Code/tools/X2PinLabels.pas: 63 board texts on F.SilkS (pin number + short name
# for 33 pins; pins 1 and 4-9 have no room) and the U2 / X3 reference texts moved clear of them.
# Guards: the board must not have the labels yet, and the import must add exactly 63 texts.
#   python -u tools/apply_x2_labels.py kicad_project/zulu_a7.kicad_pcb <production zulu_a7.PcbDoc> <out.kicad_pcb>
import pcbnew, wx, sys
_app = wx.App(False); wx.Log.SetActiveTarget(wx.LogStderr())
BOARD, ALTIUM, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
K = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.KICAD_SEXP, BOARD)
N = pcbnew.PCB_IO_MGR.Load(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER, ALTIUM)


def silk_texts(b):
    return [d for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS]


def key(t):
    p = t.GetPosition()
    return (t.GetText(), round(p.x / 1000), round(p.y / 1000))


have = {key(t) for t in silk_texts(K)}
assert not any(t.GetText() == '1V0' for t in silk_texts(K)), 'labels already present'
new = [t for t in silk_texts(N) if key(t) not in have]
assert len(new) == 63, len(new)
for t in new:
    c = pcbnew.PCB_TEXT(K)
    c.SetText(t.GetText())
    c.SetLayer(pcbnew.F_SilkS)
    c.SetTextSize(t.GetTextSize())
    c.SetTextThickness(t.GetTextThickness())
    c.SetTextAngle(t.GetTextAngle())
    c.SetHorizJustify(t.GetHorizJustify())
    c.SetVertJustify(t.GetVertJustify())
    c.SetKeepUpright(t.IsKeepUpright())
    c.SetMirrored(t.IsMirrored())
    c.SetPosition(t.GetPosition())
    K.Add(c)
moved = 0
for ref in ('U2', 'X3'):
    kr, nr = K.FindFootprintByReference(ref).Reference(), N.FindFootprintByReference(ref).Reference()
    if kr.GetPosition() != nr.GetPosition():
        kr.SetPosition(nr.GetPosition())
        kr.SetTextAngle(nr.GetTextAngle())
        kr.SetHorizJustify(nr.GetHorizJustify())
        kr.SetVertJustify(nr.GetVertJustify())
        moved += 1
print('labels added:', len(new), 'references moved:', moved)
pcbnew.SaveBoard(OUT, K)
print('saved', OUT)
