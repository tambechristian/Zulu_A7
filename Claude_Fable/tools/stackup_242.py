# -*- coding: utf-8 -*-
"""Turn the 1+6+1 build into 2+4+2: two build-up layers on each side, so a
BGA ring can escape on L3 as well as L2.

    python tools/stackup_242.py in.brd out.brd

WHY. With one microvia layer a 0.5 mm BGA at 3 mil rules escapes ring 1 on
L1 and ring 2 on L2, and ring 3 still needs a through via, which lands in the
corridor west of U1 where there is no room (board/STACKUP.md, 2026-09-06).
A second build-up layer gives ring 3 its own escape layer: a 1-2 microvia in
the ball, a 2-3 microvia beside it (staggered, 0.25 mm on the diagonal
towards the empty annulus), and an L3 trace outward with nothing of rings 1
and 2 in its way, because their copper stops at L2.

WHAT IT DOES
  1. moves the GND <polygonpour> from layer 3 to layer 4 (L4 and L5 are then
     the GND / VCC3V3 plane pair, which is a better pair than L3 / L5 was);
  2. renumbers every layer-4 signal wire to layer 3 -- through vias reach
     both, so nothing disconnects, and L3 carried no wires while it was the
     plane;
  3. sets layerSetup to [3:1+2+((3*4)+(5*6))+7+16:7]: microvias 1-2 and 2-3
     from the top, 16-7 and 7-6 from the bottom, cores 3*4 and 5*6, through
     vias 1-16.
The old L4 vertical traffic is now on L3, in the way of the ring-3 escapes
under U1 -- close_airwires evicts it with CLOSE_EVICT=3:U1:7.9. Run the
router with CLOSE_LAYERS=1,2,3,6,7,16 CLOSE_PLANES=GND:4,VCC3V3:5
CLOSE_MICROVIA=1-2,2-3,7-16,6-7 from here on.
"""

import io
import re
import sys


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = io.open(src, encoding="utf-8", errors="replace").read()
    n_pour = text.count('<polygonpour layer="3"')
    assert n_pour == 1, "expected exactly one layer-3 pour (GND), found %d" % n_pour
    assert '<polygonpour layer="4"' not in text, "layer 4 already carries a pour"
    text = text.replace('<polygonpour layer="3"', '<polygonpour layer="4"', 1)
    sm = re.search(r"<signals>.*</signals>", text, re.S)
    body = sm.group(0)
    n_l3 = len(re.findall(r'<wire\b[^>]*\blayer="3"', body))
    assert n_l3 == 0, "layer 3 already has %d signal wire(s)" % n_l3
    body, n_moved = re.subn(r'(<wire\b[^>]*\blayer=")4(")', r"\g<1>3\2", body)
    odd = [m for m in re.findall(r'<via [^>]*extent="([^"]+)"', body) if "4" in m.split("-")]
    text = text[:sm.start()] + body + text[sm.end():]
    text, n_rule = re.subn(r'(<param name="layerSetup" value=")[^"]*(")', r"\g<1>[3:1+2+((3*4)+(5*6))+7+16:7]\2", text)
    print("GND pour L3 -> L4; %d wire(s) L4 -> L3; layerSetup set (%d); blind vias ending on L4: %s" % (n_moved, n_rule, odd or "none"))
    import xml.etree.ElementTree as ET
    ET.fromstring(text)
    io.open(dst, "w", encoding="utf-8", newline="").write(text)
    print("wrote", dst)


if __name__ == "__main__":
    main()
