# -*- coding: utf-8 -*-
"""Generate the bill of materials from zulu_a7.sch.

    python tools/bom.py

Writes docs/zulu_a7-bom.csv and prints a summary. Reads the schematic and
nothing else, so it cannot disagree with the board about what is fitted --
though it cannot check the board either. Use check_board.py for that.

WHAT COUNTS AS A LINE. Not the value. A value is a label: this schematic
spells one 10k resistor "10K" on one part and "10k" on another, and one
0.1 uF capacitor "0.1uF" here and "100nF" there. Group by value and each of
those becomes two lines for a part you order once. So the key is the
ORDERABLE IDENTITY -- MANF# where there is one, and the value where the
value IS the part number, which is how most of the ICs and connectors carry
it here (AS4C32M16SB-6TIN, LTC3569EUDC#TRPBF, XC7A35T-1CPG236C). The value
variants are reported separately rather than silently merged, because a
split spelling is worth fixing in the schematic even though it does not
change what you buy.

WHAT IS EXCLUDED, ON TWO DIFFERENT GROUNDS. Parts whose deviceset has no
package at all -- frames and supply symbols -- are drawing furniture. The
four Creative Commons blocks are not: they carry a package each, so a test
on "has a package" lets them through and they read as four line items with
no part number against them. They are silkscreen. The test that catches
both is COPPER: no pad and no smd means nothing to solder and nothing to
buy. Parts marked DNP are listed but separated out, because "do not
populate" is a fitting instruction and not an absence -- the footprint is
still on the board and someone has to know not to buy for it.

MANF# IS ONE PART THAT MEETS THE SPEC, NOT THE ONLY ONE. See
source_passives.py: the SPEC attribute carries the requirement that
actually matters, and the suffix on a Murata or Yageo number encodes
thickness and packaging and is the easiest thing to get wrong. Check stock
and the exact suffix before ordering.
"""

import csv, io, os, re, sys, collections
import xml.etree.ElementTree as ET

_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCH = os.path.join(ROOT, "zulu_a7.sch")
OUT = os.path.join(ROOT, "docs", "zulu_a7-bom.csv")

sch = ET.parse(SCH).getroot().find("drawing/schematic")
LIB = {l.get("name"): l for l in sch.findall("libraries/library")}


def package_of(part):
    """the package this part will actually get, or None if it has none"""
    lib = LIB.get(part.get("library"))
    if lib is None:
        return None
    ds = lib.find("devicesets/deviceset[@name='%s']" % part.get("deviceset"))
    if ds is None:
        return None
    for d in ds.findall("devices/device"):
        if d.get("name") == part.get("device"):
            return d.get("package") or None
    return None


def has_copper(lib_name, pkg_name):
    """a package with no pad and no smd is artwork, and artwork is not bought.

    The four Creative Commons blocks carry a package each and would otherwise
    read as four line items with no part number against them. They are silk.
    """
    lib = LIB.get(lib_name)
    P = lib.find("packages/package[@name='%s']" % pkg_name) if lib is not None else None
    return P is not None and (P.findall("pad") or P.findall("smd"))


def refkey(name):
    """R10 sorts after R9, and C1 before R1"""
    m = re.match(r"^([A-Za-z$]+)(\d+)$", name)
    return (m.group(1), int(m.group(2))) if m else (name, 0)


rows, skipped, artwork, novalue = [], [], [], []
for p in sch.findall("parts/part"):
    a = {x.get("name"): x.get("value") for x in p.findall("attribute")}
    pkg = package_of(p)
    if not pkg:
        skipped.append(p.get("name"))
        continue
    if not has_copper(p.get("library"), pkg):
        artwork.append(p.get("name"))
        continue
    val, mpn, note = (p.get("value") or ""), a.get("MANF#", ""), a.get("NOTE", "")
    dnp = ("dnp" in val.lower() or "no load" in val.lower()
           or "NO HEADER FITTED" in note or "nothing to order" in note)
    # the orderable identity: a part number if there is one, else the value,
    # which for most of the ICs here IS the part number
    key = mpn or val or "(unspecified)"
    rows.append(dict(ref=p.get("name"), val=val, pkg=pkg, manf=a.get("MANF", ""),
                     mpn=mpn, spec=a.get("SPEC", ""), note=note, dnp=dnp, key=key))
    if not val:
        novalue.append(p.get("name"))

groups = collections.defaultdict(list)
for r in rows:
    groups[(r["key"], r["pkg"], r["dnp"])].append(r)

fitted = sorted([g for g in groups if not g[2]], key=lambda g: (g[1], str(g[0])))
donot = sorted([g for g in groups if g[2]], key=lambda g: (g[1], str(g[0])))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
try:
    fh = open(OUT, "w", encoding="utf-8", newline="")
except PermissionError:
    # Excel takes an exclusive lock on an open .csv. Without this the traceback
    # says "Permission denied" and looks like a filesystem problem, while the
    # stale file sits there reading like a fresh one.
    sys.exit("cannot write %s -- it is open in another program (Excel locks a csv "
             "it has open). Close it and run again." % OUT)
with fh:
    w = csv.writer(fh)
    w.writerow(["Item", "Qty", "Refdes", "Value", "Package", "Manufacturer",
                "MANF#", "Spec", "Fitted", "Note"])
    item = 0
    for g in fitted + donot:
        item += 1
        rs = sorted(groups[g], key=lambda r: refkey(r["ref"]))
        vals = sorted({r["val"] for r in rs if r["val"]})
        w.writerow([item, len(rs), " ".join(r["ref"] for r in rs),
                    " / ".join(vals), g[1], rs[0]["manf"], rs[0]["mpn"], rs[0]["spec"],
                    "DNP" if g[2] else "yes", rs[0]["note"][:400]])

# ---------------------------------------------------------------- report ----
print("BOM from zulu_a7.sch")
print("  %d lines fitted, %d DNP, %d parts in all" % (len(fitted), len(donot), len(rows)))
print("  %d schematic-only parts excluded (no package): frames and supply symbols" % len(skipped))
print("  %d padless artwork excluded (a package but no copper): %s"
      % (len(artwork), " ".join(sorted(artwork, key=refkey))))
print()
byp = collections.Counter(g[1] for g in fitted)
print("  chip packages in use:")
for pk in sorted(byp, key=lambda k: (k[0], k)):
    if re.match(r"^[RC]0\d{3}$", pk):
        print("     %-8s %2d line(s), %3d part(s)"
              % (pk, byp[pk], sum(len(groups[g]) for g in fitted if g[1] == pk)))
print()

nompn = [g for g in fitted if not groups[g][0]["mpn"]]
if nompn:
    print("  NO MANF# -- the value is carrying the part number, or there is none:")
    for g in sorted(nompn, key=lambda g: g[1]):
        rs = sorted(groups[g], key=lambda r: refkey(r["ref"]))
        print("     %-30s %-18s %s" % ((rs[0]["val"] or "(no value)")[:30], g[1],
                                       " ".join(r["ref"] for r in rs)))
    print()

var = collections.defaultdict(set)
for r in rows:
    if r["mpn"]:
        var[r["mpn"]].add(r["val"])
split = {m: v for m, v in var.items() if len(v) > 1}
if split:
    print("  ONE PART, TWO VALUE SPELLINGS. Grouped by part number here, so the BOM")
    print("  is right, but worth making consistent in the schematic:")
    for m, v in sorted(split.items()):
        print("     %-22s %s" % (m, " / ".join(sorted(v))))
    print()
if novalue:
    print("  no value at all: %s" % " ".join(sorted(novalue, key=refkey)))
    print()
if donot:
    print("  DNP (footprint on the board, nothing to buy):")
    for g in donot:
        rs = sorted(groups[g], key=lambda r: refkey(r["ref"]))
        print("     %-30s %-16s %s" % ((rs[0]["val"] or "-")[:30], g[1],
                                       " ".join(r["ref"] for r in rs)))
    print()
print("wrote %s" % OUT)
