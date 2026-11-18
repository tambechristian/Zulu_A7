"""chk.py <widths.json> <plan> <model>: route_check.py with the router's --widths override applied
(route_check.py itself has no --widths flag, so it judges inner VU/USB5V0/VBATT against the 1.1 mm legacy table)."""
import json, os, sys
T = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, T)
import router as R
import route_check
R.WIDTH_OVERRIDE.update(json.load(open(sys.argv[1])))
sys.argv = [sys.argv[0]] + sys.argv[2:]
sys.exit(route_check.main())
