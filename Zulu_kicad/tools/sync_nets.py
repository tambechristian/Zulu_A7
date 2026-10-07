"""Bring board net names in line with the schematic (KiCad python).

Only renames: the net partition was already proven identical by
compare_nets.py.  Also gives no-connect pads their schematic
unconnected-(...) nets so schematic parity is clean.
Usage: python sync_nets.py kicad.net kicad_project/zulu_a7.kicad_pcb
"""
import re, sys
import pcbnew

net_txt = open(sys.argv[1], encoding="utf8").read()
net_txt = net_txt[net_txt.index("(nets"):]
sch = {}
for block in net_txt.split("(net\n")[1:]:
    name = re.search(r'\(name "([^"]*)"\)', block).group(1)
    for ref, pin in re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]*)"\)', block):
        sch[(ref, pin)] = name

b = pcbnew.LoadBoard(sys.argv[2])
renames, added = {}, 0
for fp in b.GetFootprints():
    for p in fp.Pads():
        key = (fp.GetReference(), p.GetNumber())
        want = sch.get(key)
        if want is None:
            continue
        if p.GetNetCode() > 0:
            have = p.GetNetname()
            if have.lstrip("/") != want.lstrip("/") and not want.startswith("/"):
                renames.setdefault(have, set()).add(want)
        elif want.startswith("unconnected-"):
            ni = b.FindNet(want)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(b, want)
                b.Add(ni)
            p.SetNet(ni)
            added += 1

for old, new in sorted(renames.items()):
    assert len(new) == 1, (old, new)
    ni = b.FindNet(old)
    ni.SetNetname(next(iter(new)))
    print(f"renamed {old} -> {next(iter(new))}")
b.BuildConnectivity()
b.Save(sys.argv[2])
print(f"{len(renames)} nets renamed, {added} no-connect pads given unconnected nets")
