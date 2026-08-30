# -*- coding: utf-8 -*-
"""Restore the <sheet name="..."> attributes that Fusion's .sch export drops.

WHY THIS EXISTS
Fusion keeps two fields per sheet.  Its own document (the .fsch) carries
both and never loses either -- revisions 61 through 64 all hold 7 of 7
names.  But the Eagle-XML *export* writes only <description> and silently
omits the `name` attribute, and `name` is the one the browser panel
labels sheets from.  So every export arrives with the names stripped,
and no edit to the .sch can prevent it -- only put them back.

The names are rebuilt from each sheet's own <description>, which does
survive the export, so this needs no stored state and stays correct if a
sheet is ever retitled.  Fusion drops commas from names, so the same
normalisation is applied.  Two sheets are retitled by hand and those
choices are preserved verbatim -- they live in HAND_SET below, keyed by
the description Fusion writes, because the description itself is
regenerated from Fusion's own document on every export and so cannot
carry a rename made here.

Safe to run repeatedly: it exits without writing if the names are already
present.  Run with no arguments to fix zulu_a7.sch beside this tools/
directory, or pass a path.

    python tools/restore_sheet_names.py [path/to/file.sch]
"""

import re, io, os, sys

# KEEP THE OLD WRAPPER ALIVE. Several of these modules rebind sys.stdout to a
# utf-8 TextIOWrapper over sys.stdout.buffer. Import two of them and the first
# wrapper loses its last reference, gets collected, and CLOSES THE SHARED
# BUFFER on the way out -- every subsequent print dies with 'I/O operation on
# closed file'. It only bit once check_board started importing geom.
_prev_stdout = sys.stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# sheets retitled by hand; keyed by the description Fusion writes, since the
# description is the half of the pair that survives an export
HAND_SET = {
    "FPGA Connections": "FPGA CONNECT",
    "FT2232HQ, JTAG, CLOCK": "FT2232 JTAG CLK",
}


def normalise(description):
    """Fusion drops commas from names; collapse the whitespace that leaves."""
    name = re.sub(r"\s+", " ", description.replace(",", "")).strip()
    return HAND_SET.get(description, name)


def unesc(s):
    """Descriptions are read as raw XML, so entities have to come back first.

    Without this a description holding "WiFi &amp; Bluetooth" was re-escaped
    into name="WiFi &amp;amp; Bluetooth".  The read-back guard below did not
    catch it: it compares the parsed name against the still-escaped string,
    so both sides were wrong in the same way.
    """
    return (s.replace("&lt;", "<").replace("&gt;", ">")
             .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def restore(path):
    text = open(path, encoding="utf-8").read()
    original = text

    already = len(re.findall(r"<sheet name=", text))
    bare = len(re.findall(r"<sheet>\n", text))
    total = already + bare
    if total == 0:
        print("no sheets found in %s -- is this an Eagle schematic?" % path)
        return 1
    if bare == 0:
        print("all %d sheets already named -- nothing to do" % already)
        return 0
    if already:
        print("mixed state: %d named, %d bare -- refusing to guess" % (already, bare))
        return 1

    descriptions = re.findall(r"<sheet>\s*<description[^>]*>(.*?)</description>", text, re.S)
    if len(descriptions) != bare:
        print("only %d of %d sheets carry a <description> to recover from"
              % (len(descriptions), bare))
        return 1

    names = [normalise(unesc(d)) for d in descriptions]
    parts = text.split("<sheet>\n")
    text = parts[0] + "".join('<sheet name="%s">\n' % esc(n) + p
                              for n, p in zip(names, parts[1:]))

    # the only permitted change is the sheet opening tags
    if re.sub(r'<sheet name="[^"]*">', "<sheet>", text) != original:
        print("ABORT: the edit touched something other than the sheet tags")
        return 1

    import xml.etree.ElementTree as ET
    root = ET.fromstring(text)                      # also proves it still parses
    got = [s.get("name") for s in root.iter("sheet")]
    if got != names:
        print("ABORT: parser read back %r" % got)
        return 1

    open(path, "w", encoding="utf-8").write(text)
    for i, (n, d) in enumerate(zip(names, [unesc(x) for x in descriptions]), 1):
        print("  %d/%d  name=%-22r  from description=%r" % (i, len(names), n, d))
    print("restored %d sheet names in %s" % (len(names), path))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "zulu_a7.sch")
        target = os.path.normpath(target)
    sys.exit(restore(target))
