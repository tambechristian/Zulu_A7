"""Copy every schematic symbol field onto its footprint as a hidden field
(what Update PCB from Schematic would do), so parity has no field mismatches.
Usage (KiCad python): python copy_fields.py kicad.net kicad_project/zulu_a7.kicad_pcb"""
import re, sys
import pcbnew

net = open(sys.argv[1], encoding="utf8").read()
std = {"Reference", "Footprint"}
comps = {}
for blk in net[net.index("(components"):net.index("(libparts")].split("(comp\n")[1:]:
    ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
    fields = re.search(r"\(fields\n(.*?)\n\t\t\t\)\n", blk, re.S)
    found = re.findall(r'\(field\s+\(name "([^"]+)"\)(?: "((?:[^"\\]|\\.)*)")?', fields.group(1)) if fields else []
    comps[ref] = {k: re.sub(r'\\(.)', r'\1', v) for k, v in found if k not in std}
b = pcbnew.LoadBoard(sys.argv[2])
n = 0
for fp in b.GetFootprints():
    for k, v in comps.get(fp.GetReference(), {}).items():
        if k == "Value":
            if fp.GetValue() != v:
                print(f"value {fp.GetReference()}: {fp.GetValue()!r} -> {v!r}")
                fp.SetValue(v)
                n += 1
        elif not fp.HasField(k):
            fp.SetField(k, v)
            fp.GetField(k).SetVisible(False)
            n += 1
        elif fp.GetFieldText(k) != v:
            fp.GetField(k).SetText(v)
            n += 1
b.Save(sys.argv[2])
print("fields added", n)
