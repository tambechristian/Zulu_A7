"""Give the converted schematic real project libraries.

  - Footprint field of every placed symbol <- zulu_a7:<board footprint>
    (from footprint_map.tsv written by link_board.py)
  - Embedded lib_symbols -> one .kicad_sym per library nickname
    (ctambe, rcl, zulu_a7-altium-import, ...) plus sym-lib-table
  - fp-lib-table -> the native zulu_a7.pretty instead of the Altium PcbLib
"""
import glob, os, re, sys

d = sys.argv[1]
root = os.path.dirname(os.path.abspath(d))
fmap = dict(l.split("\t") for l in open(os.path.join(root, "footprint_map.tsv")).read().split("\n") if l)

libs = {}  # nick -> {name: text}
conflicts = []
for path in sorted(glob.glob(os.path.join(d, "*.kicad_sch"))):
    text = open(path, encoding="utf8").read()

    # --- footprint fields on placed symbols (top-level "\t(symbol\n" blocks)
    def fix_symbol(m):
        blk = m.group(0)
        ref = re.search(r'\(reference "([^"]+)"\)', blk)
        if not ref or ref.group(1) not in fmap:
            return blk
        return re.sub(r'\(property "Footprint" "[^"]*"', f'(property "Footprint" "{fmap[ref.group(1)]}"', blk, count=1)

    text, n = re.subn(r"\n\t\(symbol\n.*?\n\t\)(?=\n)", fix_symbol, text, flags=re.S)
    open(path, "w", encoding="utf8", newline="\n").write(text)

    # --- embedded library symbols
    ls = re.search(r"\n\t\(lib_symbols\n(.*?)\n\t\)\n", text, re.S)
    if not ls:
        continue
    for blk in re.findall(r"^\t\t\(symbol \".*?\n\t\t\)$", ls.group(1), re.S | re.M):
        full = re.match(r'\t\t\(symbol "([^"]+)"', blk).group(1)
        if ":" not in full:  # per-instance variant referenced via lib_name; stays embedded
            continue
        nick, name = full.split(":", 1)
        body = blk.replace(f'(symbol "{full}"', f'(symbol "{name}"', 1)
        body = "\n".join(l[1:] if l.startswith("\t") else l for l in body.split("\n"))
        old = libs.setdefault(nick, {}).get(name)
        if old is not None and old != body:
            conflicts.append((nick, name, os.path.basename(path)))
            continue
        libs[nick][name] = body

rows = []
for nick, syms in sorted(libs.items()):
    fn = f"{nick}.kicad_sym"
    out = ["(kicad_symbol_lib", "\t(version 20251024)", '\t(generator "zulu_a7_convert")']
    out += [syms[k] for k in sorted(syms)]
    out.append(")\n")
    open(os.path.join(d, fn), "w", encoding="utf8", newline="\n").write("\n".join(out))
    rows.append(f'\t(lib (name "{nick}") (type "KiCad") (uri "${{KIPRJMOD}}/{fn}") (options "") (descr "from Altium import"))')
    print(f"{fn}: {len(syms)} symbols")
open(os.path.join(d, "sym-lib-table"), "w", newline="\n").write("(sym_lib_table\n\t(version 7)\n" + "\n".join(rows) + "\n)\n")
open(os.path.join(d, "fp-lib-table"), "w", newline="\n").write(
    '(fp_lib_table\n\t(version 7)\n\t(lib (name "zulu_a7") (type "KiCad") (uri "${KIPRJMOD}/zulu_a7.pretty") (options "") (descr "footprints as placed on the Altium board"))\n)\n')
print("conflicting duplicate symbols (kept first):", conflicts)
