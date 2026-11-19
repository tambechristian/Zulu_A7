"""state.py <model.json> [plan ...]: open connections of a model with router plans (tracks/vias) merged in"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import elib as E
M = E.load(sys.argv[1])
for p in sys.argv[2:]:
    P = E.load(p)
    M = E.apply(M, P.get('remove', []) if False else (), (), P['tracks'], P['vias'])
oc = E.C.open_count(E.C.islands(M))
print('open', sum(oc.values()), dict(sorted(((k, v) for k, v in oc.items() if v), key=lambda kv: -kv[1])))
