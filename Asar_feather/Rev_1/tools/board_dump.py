"""Dump asar_feather.PcbDoc through KiCad's Altium importer: every part's side, position, rotation, pad
extent (footprint-local, Altium axes) and pad nets, plus the board-edge box under '_board', to
tools/board_dump.json. Placement planning reads it.

KiCad's Y points down: Altium Y = -KiCad Y (the importer keeps Altium's origin). Run with KiCad's python:
    "C:/Program Files/KiCad/10.0/bin/python.exe" -u tools/board_dump.py
"""
import json
import os

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc')


def main():
    app = wx.App(False)  # noqa: F841 -- the importer needs one, or it blocks on a hidden dialog
    wx.Log.SetActiveTarget(wx.LogStderr())
    io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER)
    brd = io.LoadBoard(BOARD, None)
    out = {}
    for fp in brd.GetFootprints():
        ref = fp.GetReference()
        pos = fp.GetPosition()
        pads = []
        for p in fp.Pads():
            # footprint-local, unrotated, Altium axes (as drawn in the library, seen from the top)
            fp_copy_rel = p.GetFPRelativePosition()
            sz = p.GetSize(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            pads.append({'name': p.GetNumber(), 'net': p.GetNetname(),
                         'x': pcbnew.ToMM(fp_copy_rel.x), 'y': -pcbnew.ToMM(fp_copy_rel.y),
                         'dx': pcbnew.ToMM(sz.x), 'dy': pcbnew.ToMM(sz.y),
                         'rot': p.GetFPRelativeOrientation().AsDegrees(),
                         'tht': p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)})
        out[ref] = {'x': pcbnew.ToMM(pos.x), 'y': -pcbnew.ToMM(pos.y), 'rot': fp.GetOrientationDegrees(),
                    'bottom': fp.IsFlipped(), 'footprint': fp.GetFPID().GetLibItemName().wx_str(),
                    'value': fp.GetValue(), 'pads': pads}
    bb = brd.GetBoardEdgesBoundingBox()
    out['_board'] = {'x0': pcbnew.ToMM(bb.GetLeft()), 'y0': -pcbnew.ToMM(bb.GetBottom()),
                     'x1': pcbnew.ToMM(bb.GetRight()), 'y1': -pcbnew.ToMM(bb.GetTop())}
    json.dump(out, open(os.path.join(HERE, 'board_dump.json'), 'w'), indent=0)
    print(len(out), 'components')


if __name__ == '__main__':
    main()
