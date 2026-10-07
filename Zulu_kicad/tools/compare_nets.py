"""Compare a KiCad schematic netlist against the pad nets of a .kicad_pcb.

Usage: python compare_nets.py NETLIST.net BOARD.kicad_pcb
Run with KiCad's bundled python (needs pcbnew). Compares net *partitions*
(which pads share a net) and net names.
"""
import re, sys
from collections import defaultdict
import pcbnew

net_txt = open(sys.argv[1], encoding="utf8").read()
net_txt = net_txt[net_txt.index("(nets"):]
sch = {}  # (ref, pad) -> net
for block in net_txt.split("(net\n")[1:]:
    name = re.search(r'\(name "([^"]*)"\)', block).group(1)
    for ref, pin in re.findall(r'\(ref "([^"]+)"\)\s+\(pin "([^"]*)"\)', block):
        sch[(ref, pin)] = name

b = pcbnew.LoadBoard(sys.argv[2])
pcb = {}
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() > 0:
            pcb[(fp.GetReference(), p.GetNumber())] = p.GetNetname()


def groups(d):
    g = defaultdict(set)
    for k, v in d.items():
        g[v].add(k)
    return {frozenset(s) for s in g.values() if len(s) > 1}


print(f"schematic nodes {len(sch)}, board net pads {len(pcb)}")
only_s = sorted(set(sch) - set(pcb))
only_p = sorted(set(pcb) - set(sch))
print("in schematic only:", len(only_s), only_s[:40])
print("on board only:", len(only_p), only_p[:40])
common = set(sch) & set(pcb)
gs = groups({k: sch[k] for k in common})
gp = groups({k: pcb[k] for k in common})
print("net groups: sch", len(gs), "pcb", len(gp), "identical", len(gs & gp))
for s in sorted(gs - gp, key=sorted)[:25]:
    k = next(iter(s)); print("  SCH group", sch[k], sorted(s)[:8])
for s in sorted(gp - gs, key=sorted)[:25]:
    k = next(iter(s)); print("  PCB group", pcb[k], sorted(s)[:8])
ren = sorted({(sch[k], pcb[k]) for k in common if sch[k].lstrip("/") != pcb[k].lstrip("/")})
print("name differences:", len(ren), ren[:60])
