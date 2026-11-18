"""check_w.py <widths.json> <plan> <model>: route_check.py with router.py's --widths override applied
(route_check alone uses the old Zulu table: VU/USB5V0/VBATT 1.1 mm on inner layers)."""
import json, sys
sys.path.insert(0, 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/tools')
import router as R
import route_check
R.WIDTH_OVERRIDE.update(json.load(open(sys.argv[1])))
print('width rules overridden:', json.load(open(sys.argv[1])))
sys.argv = [sys.argv[0]] + sys.argv[2:]
route_check.main()
