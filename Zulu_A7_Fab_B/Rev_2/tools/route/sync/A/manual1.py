"""manual1.py: exact hand routes on top of the stubs transplant + router pass r2 (stubs variant).

    python manual1.py            -> manual1.json (plan additions) + m3.json (model with them)

  GND  U1-L19: one Top>L2 laser (0.30/0.15) overlapping the L19 land at (50.975, 11.37): JA4's Top track at y 11.65
       keeps a via on the land centre 0.062 mm away; 0.075 E / 0.03 S clears it (exact search, fit.search_via).
  CHAN5: Top (49.95, 17.5) -> stack Top>L2>L3 at (50.85, 17.35) -> L3 down to the D17 stub end (50.85, 16.65).
       TARGET's own path went via (50.6, 18.05), which the moved U4-5 land now covers.
"""
import json

import fit

W = 0.0762


def main():
    F = fit.Fit('m_r2_stubs.json')
    F.add_via('GND', 50.975, 11.37, ['TL2'])
    F.add_via('CHAN5', 50.85, 17.35, ['TL2', 'L23'])
    F.add_track('CHAN5', 'Top Layer', W, 49.95, 17.5, 50.85, 17.35)
    F.add_track('CHAN5', 'L3-SIG', W, 50.85, 16.65, 50.85, 17.35)
    json.dump(F.plan, open('manual1.json', 'w'), indent=1)
    json.dump(F.M, open('m3.json', 'w'))
    print('manual1: %d tracks, %d vias' % (len(F.plan['tracks']), len(F.plan['vias'])))


if __name__ == '__main__':
    main()
