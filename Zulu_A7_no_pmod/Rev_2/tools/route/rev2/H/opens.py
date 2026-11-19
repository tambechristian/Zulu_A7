"""opens.py <model.json> <plan.json> [...]: open connections per net of model + plan (plan copper added, plan removes applied)"""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/tools')
import route_conn as C
import compose_plan as CP
M = json.load(open(sys.argv[1]))
for f in sys.argv[2:]:
    P = json.load(open(f))
    P.setdefault('remove', []); P.setdefault('remove_vias', [])
    Mx = CP.apply(M, P)
    oc = C.open_count(C.islands(Mx))
    print(f, sum(oc.values()), dict(sorted(oc.items())))
