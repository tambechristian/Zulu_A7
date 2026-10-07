"""Link the imported board to the schematic and give it a native footprint lib.

Run with KiCad's bundled python:  python link_board.py kicad_project
  - saves every board footprint into kicad_project/zulu_a7.pretty
    (as placed; one file per distinct footprint name)
  - sets each footprint's FPID to zulu_a7:<name> and its schematic path
    (/<sheet uuid>/<symbol uuid>) from the netlist kicad.net
  - writes footprint_map.tsv (ref -> zulu_a7:<name>) for the schematic side
"""
import os, re, sys
import pcbnew

d = sys.argv[1]
net = open(os.path.join(os.path.dirname(os.path.abspath(d)), "kicad.net"), encoding="utf8").read()
comps = {}
for block in net[net.index("(components"):net.index("(libparts")].split("(comp\n")[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', block).group(1)
    names = re.search(r'\(sheetpath\s+\(names "([^"]*)"\)\s+\(tstamps "([^"]*)"\)', block)
    tst = re.search(r'\(tstamps "([0-9a-f-]{36})"', block)
    comps[ref] = (names.group(1), names.group(2), tst.group(1).split()[0])

pcb_path = os.path.join(d, "zulu_a7.kicad_pcb")
b = pcbnew.LoadBoard(pcb_path)
lib = os.path.join(d, "zulu_a7.pretty")
io = pcbnew.PCB_IO_MGR.FindPlugin(pcbnew.PCB_IO_MGR.KICAD_SEXP)

if not os.path.isdir(lib):
    os.makedirs(lib)

saved, unlinked, rows = {}, [], []
sheetfile = {}
for line in open(os.path.join(d, "zulu_a7.kicad_sch"), encoding="utf8").read().split("\t(sheet\n")[1:]:
    su = re.search(r'\(uuid "([^"]+)"\)', line).group(1)
    sheetfile[su] = re.search(r'\(property "Sheetfile" "([^"]+)"', line).group(1)

for fp in b.GetFootprints():
    ref = fp.GetReference()
    name = fp.GetFPID().GetLibItemName().wx_str()
    if name not in saved:
        copy = pcbnew.FOOTPRINT(fp)
        copy.SetReference("REF**")
        copy.SetPosition(pcbnew.VECTOR2I(0, 0))
        if copy.IsFlipped():
            copy.Flip(copy.GetPosition(), pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
        copy.SetOrientationDegrees(0)
        copy.SetPath(pcbnew.KIID_PATH())
        io.FootprintSave(lib, copy)
        saved[name] = ref
    fp.SetFPID(pcbnew.LIB_ID("zulu_a7", name))
    rows.append(f"{ref}\tzulu_a7:{name}")
    if ref not in comps:
        unlinked.append(ref)
        continue
    sheetname, stamps, sym = comps[ref]
    sheet_uuid = stamps.strip("/")
    fp.SetPath(pcbnew.KIID_PATH(f"/{sheet_uuid}/{sym}"))
    fp.SetSheetname(sheetname.strip("/"))
    fp.SetSheetfile(sheetfile.get(sheet_uuid, ""))

b.Save(pcb_path)
open(os.path.join(os.path.dirname(os.path.abspath(d)), "footprint_map.tsv"), "w").write("\n".join(rows) + "\n")
print(f"footprints {len(rows)}, library entries {len(saved)}, unlinked {unlinked}")
print("schematic symbols without footprint:", sorted(set(comps) - {r.split()[0] for r in rows}))
