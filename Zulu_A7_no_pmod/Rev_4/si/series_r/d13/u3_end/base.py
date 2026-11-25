"""Shared loader: the 13-R plan applied to board_extract.json using the checker copy's own apply()."""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
SR = os.path.normpath(os.path.join(HERE, '..', '..'))
PLAN13 = os.path.join(SR, 'dq_series_r_plan.json')
_argv = sys.argv
sys.argv = ['check.py', '--plan', PLAN13, '--tag', '_import']
sys.path.insert(0, HERE)
import check as C
sys.argv = _argv

def applied(plan_path=PLAN13):
    C.PLAN = plan_path
    E = C.load_plan()
    pads, tracks, vias, newflags, errors = C.apply(E)
    assert not errors, errors
    return E, pads, tracks, vias, newflags
