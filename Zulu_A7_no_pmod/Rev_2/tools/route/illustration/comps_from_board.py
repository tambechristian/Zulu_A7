"""comps.json for body_check / board_illustration, read from the saved PcbDoc (KiCad python).

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route/illustration/comps_from_board.py OUT.json [MECH_FROM.json]

ref, layer (TOP/BOTTOM), rot (degrees), pattern, height 0. 'mech' (connector body offsets from their pad extent)
is copied from MECH_FROM (default tools/route/x4_feasibility/qfn/comps_final.json, which holds the S2B-PH-SM4-TB X4).
"""
import json
import os
import sys

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
BOARD = os.environ.get('FABB_PCB', os.path.join(os.path.dirname(TOOLS), 'Imported zulu_a7.PrjPcb', 'Zulu_a7_no_pmod.PcbDoc'))
app = wx.App(False)  # noqa: F841
wx.Log.SetActiveTarget(wx.LogStderr())
b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
comps = []
for fp in b.GetFootprints():
    comps.append({'ref': fp.GetReference(), 'layer': 'BOTTOM' if fp.GetLayer() == pcbnew.B_Cu else 'TOP',
                  'rot': round(fp.GetOrientationDegrees() % 360, 3), 'pattern': str(fp.GetFPID().GetLibItemName()),
                  'height': 0.0})
src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TOOLS, 'route', 'x4_feasibility', 'qfn', 'comps_final.json')
json.dump({'comps': comps, 'mech': json.load(open(src))['mech']}, open(sys.argv[1], 'w'), indent=0)
print(len(comps), 'parts from', BOARD)
