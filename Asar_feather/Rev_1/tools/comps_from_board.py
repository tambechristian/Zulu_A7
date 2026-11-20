"""comps.json for body_check / release_body_gate, read from the saved PcbDoc (KiCad python). READ-ONLY on the board.

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/comps_from_board.py OUT.json [MECH_FROM.json]

ref, layer (TOP/BOTTOM), rot (degrees), pattern. 'mech' (connector body offsets from their pad extent) is copied from
MECH_FROM (default tools/body_mech.json). ASAR_PCB overrides the board path. Ported from no_pmod's
tools/route/illustration/comps_from_board.py.
"""
import json
import os
import sys

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.environ.get('ASAR_PCB', os.path.join(os.path.dirname(HERE), 'Asar_feather.PrjPcb', 'asar_feather.PcbDoc'))
app = wx.App(False)  # noqa: F841
wx.Log.SetActiveTarget(wx.LogStderr())
wx.Log.SetLogLevel(0)
b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
comps = []
for fp in b.GetFootprints():
    comps.append({'ref': fp.GetReference(), 'layer': 'BOTTOM' if fp.GetLayer() == pcbnew.B_Cu else 'TOP',
                  'rot': round(fp.GetOrientationDegrees() % 360, 3), 'pattern': str(fp.GetFPID().GetLibItemName())})
src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, 'body_mech.json')
mech = json.load(open(src))
mech = mech.get('mech', mech)
mech.pop('_note', None)
json.dump({'comps': comps, 'mech': mech}, open(sys.argv[1], 'w'), indent=0)
print(len(comps), 'parts from', BOARD)
