import json, sys
from collections import Counter
sys.path.insert(0, '.')
import judge as J
T = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/'
B0 = json.load(open(T + 'model_base.json'))
for v in B0['vias']:
    v['span'] = J.span(v)
v0 = J.drc(B0)
print(Counter(k[0] for k in v0))
for s in sorted(v0.values())[:60]:
    print(' ', s)
MOVED = ('X1-', 'X4-', 'X2-10(', 'X2-30(', 'U10-', 'R96-', 'R84-', 'R86-')
for key in 'EFGH':
    R = json.load(open(key + '/result.json'))
    vr = J.drc(R)
    hits = [s for s in vr.values() if any(m in s for m in MOVED)]
    print(key, 'result violations', len(vr), 'involving moved parts', len(hits))
    for s in hits:
        print('   ', s)
