"""Post-process KiCad 10's Altium import of the Zulu A7 project.

1. Altium project is in Flat mode (HierarchyMode=0): net labels are project
   wide.  KiCad imported them as sheet-local labels, which breaks every
   cross-sheet net.  Convert every local label to a global label.
2. KiCad 10 imported the 7 sheets as 7 top-level sheets, which kicad-cli and
   older KiCad cannot read as one design.  Build a classic hierarchy: a new
   root zulu_a7.kicad_sch holding 7 sheet symbols; the old page-1 file becomes
   zulu_a7_0.kicad_sch.  Symbol instance paths become /<root>/<sheet>.
3. Annotate the unannotated power symbols (#PWR?) with unique numbers.

Run once on the raw import in kicad_project/.
"""
import json, os, re, sys, uuid

d = sys.argv[1] if len(sys.argv) > 1 else "kicad_project"
pro_path = os.path.join(d, "zulu_a7.kicad_pro")
pro = json.load(open(pro_path, encoding="utf8"))
sheets = pro["schematic"]["top_level_sheets"]
assert len(sheets) == 7, "already processed?"

root_uuid = str(uuid.uuid4())
pwr = [0]


def fix_sheet(text, sheet_uuid):
    n_lab = len(re.findall(r"^\t\(label ", text, re.M))
    text = re.sub(r'^\t\(label ("(?:[^"\\]|\\.)*")\n', r"\t(global_label \1\n\t\t(shape passive)\n", text, flags=re.M)
    text = text.replace(f'(path "/{sheet_uuid}"', f'(path "/{root_uuid}/{sheet_uuid}"')

    def ann(m):
        pwr[0] += 1
        return f'(reference "#PWR{pwr[0]:03d}")'

    text = re.sub(r'\(reference "#PWR\?"\)', ann, text)
    # The symbol's Reference property also carries "#PWR?"; keep it in step
    # with the instance (KiCad uses the instance, but keep the file consistent).
    return text, n_lab


new_sheets = []
for i, s in enumerate(sheets):
    src = os.path.join(d, s["filename"])
    dst_name = "zulu_a7_0.kicad_sch" if s["filename"] == "zulu_a7.kicad_sch" else s["filename"]
    text = open(src, encoding="utf8").read()
    text, n = fix_sheet(text, s["uuid"])
    # sub-sheets do not carry sheet_instances
    text = re.sub(r"\n\t\(sheet_instances\n.*?\n\t\)\n", "\n", text, flags=re.S)
    open(os.path.join(d, dst_name), "w", encoding="utf8", newline="\n").write(text)
    print(f"{s['filename']} -> {dst_name}: {n} labels -> global")
    new_sheets.append((s["uuid"], s["name"], dst_name, i + 2))

blocks = []
for k, (su, name, fname, page) in enumerate(new_sheets):
    x, y = 30 + (k % 4) * 60, 40 + (k // 4) * 40
    blocks.append(f"""\t(sheet
\t\t(at {x} {y})
\t\t(size 45 20)
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(stroke
\t\t\t(width 0.1524)
\t\t\t(type solid)
\t\t)
\t\t(fill
\t\t\t(color 0 0 0 0.0000)
\t\t)
\t\t(uuid "{su}")
\t\t(property "Sheetname" "{name}"
\t\t\t(at {x} {y - 0.7} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left bottom)
\t\t\t)
\t\t)
\t\t(property "Sheetfile" "{fname}"
\t\t\t(at {x} {y + 20.6} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(justify left top)
\t\t\t)
\t\t)
\t\t(instances
\t\t\t(project "zulu_a7"
\t\t\t\t(path "/{root_uuid}"
\t\t\t\t\t(page "{page}")
\t\t\t\t)
\t\t\t)
\t\t)
\t)
""")

root = f"""(kicad_sch
\t(version 20260306)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{root_uuid}")
\t(paper "A4")
\t(title_block
\t\t(title "Zulu A7")
\t\t(comment 1 "Converted from Altium (Zulu_Altium_VS_Code); Altium Flat net scope -> global labels")
\t)
\t(lib_symbols)
{''.join(blocks)}\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
"""
open(os.path.join(d, "zulu_a7.kicad_sch"), "w", encoding="utf8", newline="\n").write(root)

pro["schematic"]["top_level_sheets"] = [{"filename": "zulu_a7.kicad_sch", "name": "zulu_a7", "uuid": root_uuid}]
pro["sheets"] = [[root_uuid, "Root"]] + [[su, name] for su, name, _, _ in new_sheets]
json.dump(pro, open(pro_path, "w", encoding="utf8", newline="\n"), indent=2)
print("root", root_uuid, "power symbols annotated:", pwr[0])
