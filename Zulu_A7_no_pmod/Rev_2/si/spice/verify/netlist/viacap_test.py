import math, viacap as V
# infinite coax: barrel r=0.1 over the whole z range (air=0, Neumann z ends), eps 1, wall R
for R in (0.5, 1.0, 2.0):
    c = V.via_cap(('Top', 'Bot'), 0.2, 0.2, 0.35, R=R, air=0.0, planes=False, uni=1.0, zneu=True)
    print('coax R=%.1f FD %.5f pF ideal %.5f pF' % (R, c * 1e12, 2 * math.pi * 8.854187817e-12 * 1.65038e-3 / math.log(R / 0.1) * 1e12))
# parallel-plate-ish: uni eps check scaling
c1 = V.via_cap(('Top', 'Bot'), 0.35, 0.2, 0.35, R=1.5, uni=1.0); c4 = V.via_cap(('Top', 'Bot'), 0.35, 0.2, 0.35, R=1.5, uni=4.0)
print('eps scaling 4x -> ratio %.4f' % (c4 / c1))
