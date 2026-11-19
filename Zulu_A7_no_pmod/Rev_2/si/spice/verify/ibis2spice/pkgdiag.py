"""Diagonal R/L/C of the U1 [Define Package Model] for the SDRAM pins, vs the [Package] defaults ibis2spice uses."""
import sys, os, json, re
sys.path.insert(0, os.path.abspath('../..'))
import bus_sim as B, ibis2spice as I
txt = open(B.U1_IBS, encoding='latin1').read().splitlines()
i0 = next(i for i, l in enumerate(txt) if l.startswith('[Define Package Model]'))
mat = None; row = None; diag = {'r': {}, 'l': {}, 'c': {}}
for l in txt[i0:]:
    l = l.split('|')[0].strip()
    if not l: continue
    if l.startswith('[Resistance Matrix]'): mat = 'r'; continue
    if l.startswith('[Inductance Matrix]'): mat = 'l'; continue
    if l.startswith('[Capacitance Matrix]'): mat = 'c'; continue
    if l.startswith('[End Model Data]'): break
    if l.startswith('[Row]'): row = l.split()[1]; first = True; continue
    if l.startswith('['): continue
    if mat and row:
        t = l.split()
        if mat == 'r':      # banded, bandwidth 0: one value
            if row not in diag['r']: diag['r'][row] = float(t[0])
        elif len(t) == 2 and t[0] == row:
            diag[mat][row] = float(t[1])
M = json.load(open(B.MODEL))
U1 = I.Ibis(B.U1_IBS)
out = []
for net in B.NETS:
    p = [q for q in M['pads'] if q['net'] == net and q['ref'] == 'U1'][0]['pad']
    out.append((net, p, diag['r'].get(p), diag['l'].get(p), diag['c'].get(p), U1.pins[p]))
print('[Package] typ/min/max', U1.pkg)
for o in out:
    print('%-10s %-4s R=%.3f L=%.2f nH C=%.3f pF   pins-entry=%s' % (o[0], o[1], o[2], o[3]*1e9, o[4]*1e12, o[5]))
import numpy as np
L = np.array([o[3] for o in out]); C = np.array([o[4] for o in out]); R = np.array([o[2] for o in out])
print('per-pin L nH: min %.2f mean %.2f max %.2f ; C pF min %.3f mean %.3f max %.3f; R min %.3f max %.3f' % (L.min()*1e9, L.mean()*1e9, L.max()*1e9, C.min()*1e12, C.mean()*1e12, C.max()*1e12, R.min(), R.max()))
json.dump({o[0]: [o[1], o[2], o[3], o[4]] for o in out}, open('u1_pkg_diag.json', 'w'), indent=1)
