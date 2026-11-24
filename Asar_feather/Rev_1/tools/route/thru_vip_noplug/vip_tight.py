"""Tightened through-via acceptance check (phase 3, 2026-11-22): a through via must be a normal tented dog-bone.

Same as vip_check.py (same arguments, same output format) with two limits raised:
  (a) via LAND to any SMD pad's COPPER gap >= 0.0762 mm (3 mil: an etchable gap, so the fab's CAM cannot merge
      the land into the pad and see a via on the pad edge);  vip_check used 1e-4 (touch).
  (b) via HOLE edge to any SMD pad's solder-mask opening >= 0.10 mm (PCBWay's mask dam; covers +/-0.05
      registration with margin);  vip_check used 0.05.
(c) unchanged.  With the board's 0.05 default expansion (a) gives (b) automatically (0.0762+0.075-0.05=0.101).

    python vip_tight.py <model.json> [--plan plan.json] [--truth pad_truth.json] [--json out.json] [--quiet]
Exit code: 0 no violation, 1 violations, 2 bad input.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vip_check as V  # noqa: E402

V.TOUCH = 0.0762
V.MASK_REG = 0.10

if __name__ == '__main__':
    sys.exit(V.main())
