"""comps.json for body_check / the release body gate, read from the saved PcbDoc (KiCad python).

    "C:/Program Files/KiCad/10.0/bin/python.exe" tools/route/illustration/comps_from_board.py OUT.json [MECH_FROM.json]

ref, layer (TOP/BOTTOM), rot (degrees), pattern, height 0. 'mech' (connector body offsets from their pad extent, each
with the footprint it belongs to) is copied from MECH_FROM (default tools/body_mech.json).

Fab B Rev 2 copy (2026-11-20) of Zulu_A7_no_pmod/Rev_2/tools/route/illustration/comps_from_board.py (427960e): the
default board is this folder's zulu_a7_fab_b.PcbDoc; FABB_PCB overrides it as before. Nothing else changed.
"""
import json
import os
import sys

import pcbnew
import wx

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(os.path.dirname(HERE))
BOARD = os.environ.get('FABB_PCB', os.path.join(os.path.dirname(TOOLS), 'Imported zulu_a7.PrjPcb', 'zulu_a7_fab_b.PcbDoc'))
app = wx.App(False)  # noqa: F841
wx.Log.SetActiveTarget(wx.LogStderr())
b = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER).LoadBoard(BOARD, None)
comps = []
for fp in b.GetFootprints():
    comps.append({'ref': fp.GetReference(), 'layer': 'BOTTOM' if fp.GetLayer() == pcbnew.B_Cu else 'TOP',
                  'rot': round(fp.GetOrientationDegrees() % 360, 3), 'pattern': str(fp.GetFPID().GetLibItemName()),
                  'height': 0.0})
src = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TOOLS, 'body_mech.json')
mech = json.load(open(src))
mech = mech.get('mech', mech)
mech.pop('_note', None)
json.dump({'comps': comps, 'mech': mech}, open(sys.argv[1], 'w'), indent=0)
print(len(comps), 'parts from', BOARD)
