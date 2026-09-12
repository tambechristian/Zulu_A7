#!/usr/bin/env python
"""
verify_stack.py -- read the SAVED PcbDoc and check the layer stack against the
JLCPCB catalogue template JLC06161H-3313E.  Reads the file; changes nothing.

Altium stores every stack length in Board6/Data as a mil STRING with trailing
zeros stripped ("0.4mil", "3.9134mil", "44.126mil") and every dielectric
constant as a 3-decimal string ("4.100").  So we PARSE and compare numerically
with a tolerance rather than matching strings.

Three independent copies of the stack live in Board6/Data and all three are
checked, because Altium writes all three on save:
  V9_STACK_LAYERn_*   the authoritative Layer Stack Manager rows (one row per
                      copper layer AND one row per dielectric sheet)
  LAYER_V8_n*         a flat V8 cache, same shape
  LAYERn*             the legacy 82-slot table, which carries the dielectric
                      BELOW each copper layer -- it has exactly ONE dielectric
                      slot per copper layer and therefore cannot represent a
                      gap built from more than one sheet.

Usage:  python tools/verify_stack.py [path\\to\\zulu_a7.PcbDoc]
"""
import sys, re, olefile

MIL = 0.0254                      # mm per mil
TOL_MM = 0.0005                   # generous: the 4-dp mil quantum is 2.5e-6 mm
TOL_DK = 0.002                    # DIELCONST is stored to 3 decimals

DEFAULT = (r"C:\Users\tambe\Documents\Electronics\Zulu_A7\Zulu_Altrium"
           r"\Imported zulu_a7.PrjPcb\zulu_a7.PcbDoc")

# DIELTYPE codes, now PROVEN rather than inferred (2026-09-12).  Dielectrics 4
# and 5 were set to "Core" in the Layer Stack Manager and the saved file was
# read back: both came out as 1, not 0.
#   0 -> "Dielectric"       generic / unspecified   (FR-4, Dielectric 1)
#   1 -> "Core"             (Dielectrics 4 and 5)
#   2 -> "Prepreg"          (PP-006, Dielectrics 2 and 3)
#   3 -> "Surface Material" (Solder Resist)
# The 2026-09-11 reading that 0 meant Core was WRONG.  The old custom stack's
# FR-4 row merely DISPLAYED as "Dielectric" and was called a core in prose;
# no row in this file had ever actually been labelled Core until now.
GENERIC, CORE, PREPREG, SURFACE = 0, 1, 2, 3

# Outer copper: JLCPCB publish 0.035 mm FINISHED.  Altium's stock 1.4 mil is
# 0.03556 mm.  Set OUTER_CU_MM = 0.03556 if you chose to leave 1.4 mil alone.
OUTER_CU_MM = 0.035               # 1.378 mil
INNER_CU_MM = 0.0152              # 0.5984 mil

# (row name, kind, thickness mm, Dk, dieltype)   kind: 'cu' | 'diel' | 'none'
EXPECT = [
    ("Top Paste",      "none", None,        None,  None),
    ("Top Overlay",    "none", None,        None,  None),
    ("Top Solder",     "diel", 0.4 * MIL,   3.500, SURFACE),
    ("Top Layer",      "cu",   OUTER_CU_MM, None,  None),
    ("Dielectric 2",   "diel", 0.0994,      4.100, PREPREG),  # 3313 x1 UNCHANGED
    ("L2-GND",         "cu",   INNER_CU_MM, None,  None),
    ("Dielectric 4",   "diel", 0.1000,      4.600, CORE),     # 0.1 mm core
    ("L3-SIG",         "cu",   INNER_CU_MM, None,  None),
    ("Dielectric 1",   "diel", 1.1208,      4.523, GENERIC),  # 7628+0.7core+7628 -> mixed
    ("L4-SIG",         "cu",   INNER_CU_MM, None,  None),
    ("Dielectric 5",   "diel", 0.1000,      4.600, CORE),     # 0.1 mm core
    ("L5-GND",         "cu",   INNER_CU_MM, None,  None),
    ("Dielectric 3",   "diel", 0.0994,      4.100, PREPREG),  # 3313 x1 UNCHANGED
    ("Bottom Layer",   "cu",   OUTER_CU_MM, None,  None),
    ("Bottom Solder",  "diel", 0.4 * MIL,   3.500, SURFACE),
    ("Bottom Overlay", "none", None,        None,  None),
    ("Bottom Paste",   "none", None,        None,  None),
]


def mm(s):
    """'44.126mil' -> 1.1208 (mm).  Altium also writes a bare 'mm' suffix."""
    if s is None:
        return None
    m = re.match(r"\s*(-?[\d.]+)\s*(mil|mm)?\s*$", s)
    if not m:
        raise ValueError("unparsable length %r" % s)
    v = float(m.group(1))
    return v * MIL if (m.group(2) or "mil") == "mil" else v


def load(path):
    o = olefile.OleFileIO(path)
    txt = o.openstream("Board6/Data").read().decode("latin-1")
    d = {}
    for kv in txt.split("|"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            d[k] = v
    return d


def rows(d, prefix, sep):
    """Collect prefix<N>sep<FIELD> into {index: {field: value}}."""
    out = {}
    pat = re.compile(re.escape(prefix) + r"(\d+)" + re.escape(sep) + r"(.*)$")
    for k, v in d.items():
        m = pat.match(k)
        if m and not m.group(2).startswith("{"):
            out.setdefault(int(m.group(1)), {})[m.group(2)] = v
    return out


def check(label, got, want, tol, fails):
    if want is None:
        return
    if got is None:
        fails.append("%s MISSING (want %s)" % (label, want))
        print("   %-42s %-12s BAD (missing)" % (label, "-"))
        return
    ok = abs(got - want) <= tol
    print("   %-42s %-12s %s" % (
        label, ("%.5f" % got).rstrip("0").rstrip("."),
        "OK" if ok else "BAD (want %.5f)" % want))
    if not ok:
        fails.append("%s got %.5f want %.5f" % (label, got, want))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    d = load(path)
    fails = []
    print("FILE:", path)

    # ---- 1. the authoritative V9 stack -------------------------------------
    v9 = rows(d, "V9_STACK_LAYER", "_")
    order = [v9[i] for i in sorted(v9)]
    names = [r.get("NAME") for r in order]
    print("\n[1] V9_STACK_LAYERn -- %d rows" % len(order))
    print("    order: " + " / ".join(n or "?" for n in names))
    if names != [e[0] for e in EXPECT]:
        fails.append("V9 row order/count differs from expected\n"
                     "      got  %s\n      want %s"
                     % (names, [e[0] for e in EXPECT]))
        print("    !! row list differs; field checks below match by NAME")

    by_name = {}
    for r in order:
        by_name.setdefault(r.get("NAME"), r)

    total_mm = 0.0
    for name, kind, t_mm, dk, dt in EXPECT:
        r = by_name.get(name)
        if r is None:
            fails.append("V9 row %r MISSING" % name)
            continue
        if kind == "cu":
            g = mm(r.get("COPTHICK"))
            check("V9 %s COPTHICK" % name, g, t_mm, TOL_MM, fails)
            if g:
                total_mm += g
        elif kind == "diel":
            g = mm(r.get("DIELHEIGHT"))
            check("V9 %s DIELHEIGHT" % name, g, t_mm, TOL_MM, fails)
            if g:
                total_mm += g
            gk = float(r["DIELCONST"]) if "DIELCONST" in r else None
            check("V9 %s DIELCONST" % name, gk, dk, TOL_DK, fails)
            gt = int(r["DIELTYPE"]) if "DIELTYPE" in r else None
            print("   %-42s %-12s %s" % ("V9 %s DIELTYPE" % name, gt,
                                         "OK" if gt == dt else "BAD (want %d)" % dt))
            if gt != dt:
                fails.append("V9 %s DIELTYPE got %r want %d "
                             "(0=Dielectric 1=Core 2=Prepreg 3=Surface)" % (name, gt, dt))
            print("   %-42s %s" % ("V9 %s MATERIAL" % name,
                                   r.get("DIELMATERIAL", "-")))

    lam = total_mm - 2 * 0.4 * MIL
    print("\n    total incl. solder mask : %.5f mm  (%.4f mil)"
          % (total_mm, total_mm / MIL))
    print("    laminate  excl. mask    : %.5f mm   <- JLC quote 1.65040 mm" % lam)

    # ---- 2. the V8 cache must agree ----------------------------------------
    v8 = rows(d, "LAYER_V8_", "")
    print("\n[2] LAYER_V8_n cache")
    for name, kind, t_mm, dk, dt in EXPECT:
        if kind == "none":
            continue
        r = next((x for x in v8.values() if x.get("NAME") == name), None)
        if r is None:
            fails.append("V8 cache row %r MISSING" % name)
            continue
        key = "COPTHICK" if kind == "cu" else "DIELHEIGHT"
        check("V8 %s %s" % (name, key), mm(r.get(key)), t_mm, TOL_MM, fails)

    # ---- 3. the legacy table: ONE dielectric slot per copper layer ----------
    leg = rows(d, "LAYER", "")
    legname = {}
    for i in sorted(leg):
        r = leg[i]
        if "NAME" in r:
            legname.setdefault(r["NAME"], r)
    print("\n[3] legacy LAYERn table (dielectric BELOW each copper layer)")
    legacy_expect = [("Top Layer",    OUTER_CU_MM, 0.0994, 4.100),
                     ("L2-GND",       INNER_CU_MM, 0.1000, 4.600),
                     ("L3-SIG",       INNER_CU_MM, 1.1208, 4.523),
                     ("L4-SIG",       INNER_CU_MM, 0.1000, 4.600),
                     ("L5-GND",       INNER_CU_MM, 0.0994, 4.100),
                     ("Bottom Layer", OUTER_CU_MM, None,   None)]
    for name, cu, h, dk in legacy_expect:
        r = legname.get(name)
        if r is None:
            fails.append("legacy row %r MISSING" % name)
            continue
        check("legacy %s COPTHICK" % name, mm(r.get("COPTHICK")), cu, TOL_MM, fails)
        if h is not None:
            check("legacy %s DIELHEIGHT" % name,
                  mm(r.get("DIELHEIGHT")), h, TOL_MM, fails)
            check("legacy %s DIELCONST" % name,
                  float(r["DIELCONST"]) if "DIELCONST" in r else None,
                  dk, TOL_DK, fails)

    # ---- 4. things the stack edit must NOT have broken ----------------------
    print("\n[4] must be untouched")
    for k, want in (("PLANE1NETNAME", "GND"), ("PLANE2NETNAME", "GND"),
                    ("PLANE1PULLBACK", "20mil"), ("PLANE2PULLBACK", "20mil")):
        got = d.get(k)
        ok = got == want
        print("   %-42s %-12s %s" % (k, got, "OK" if ok else "BAD (want %s)" % want))
        if not ok:
            fails.append("%s got %r want %r" % (k, got, want))
    for nm, lid in (("Top Layer", "16777217"), ("L2-GND", "16842753"),
                    ("L3-SIG", "16777218"), ("L4-SIG", "16777219"),
                    ("L5-GND", "16842754"), ("Bottom Layer", "16842751")):
        got = by_name.get(nm, {}).get("LAYERID")
        ok = got == lid
        print("   %-42s %-12s %s" % ("LAYERID %s" % nm, got,
                                     "OK" if ok else "BAD (want %s)" % lid))
        if not ok:
            fails.append("LAYERID %s got %r want %r -- layer identity changed, "
                         "primitives may have moved" % (nm, got, lid))

    print("\n" + "=" * 72)
    if fails:
        print("FAIL -- %d problem(s):" % len(fails))
        for f in fails:
            print("  *", f)
        return 1
    print("PASS -- stack matches JLC06161H-3313E")
    return 0


if __name__ == "__main__":
    sys.exit(main())
