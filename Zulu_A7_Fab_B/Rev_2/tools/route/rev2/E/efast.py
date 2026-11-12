"""efast.py: router_e's via policy (no via land on an SMD pad, plane-tie columns) + finish.py's numpy via_ok.
Import it before anything that uses router.Router.
    python efast.py router <router.py args...>     tools/router.py main (seeded second pass etc.)
    python efast.py finish <finish.py args...>     tools/finish.py main (partial rip-up finisher)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import router_e as RE  # noqa: E402  (patches router: VIAS, PLANE_VIAS, Board.__init__ padban, Router.via_ok)
import finish as FN  # noqa: E402    (replaces Router.via_ok with the numpy version, commit/rip bump vver)

RE._orig_via_ok = FN._via_ok          # router_e's pad ban first, then the numpy land / hole test
FN.R.Router.via_ok = RE._via_ok
R = FN.R

if __name__ == '__main__':
    mode = sys.argv.pop(1)
    print('efast %s: pad ban (%s) + plane-tie columns + numpy via_ok' % (mode, 'through only' if RE.INPAD else 'all vias'), flush=True)
    if mode == 'router':
        R.main()
    else:
        FN.main()
