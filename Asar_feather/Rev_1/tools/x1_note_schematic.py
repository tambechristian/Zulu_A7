"""Sheet 1: rewrite the stale 2026-09-10 X1 note (four RECORD=4 texts east of X1) for the micro-B (review E3).
Text only, same records and UniqueIDs; the netlist is rebuilt before/after and must be identical.
    python tools/x1_note_schematic.py [--apply]     (close sheet 1 in Altium first)"""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import schdoc, sch_netlist
ROOT = os.path.dirname(HERE)
PROJ = os.path.join(ROOT, 'Asar_feather.PrjPcb')
SHEET = os.path.join(PROJ, 'asar_a7_1.SchDoc')
BACKUP = os.path.join(ROOT, 'backups', 'asar_a7_1_before_x1_note.SchDoc')
NEW = {
    'HMNLFCFQ': ('2026-09-10: X1 pin 5 owned nine pads', '2026-11-17: X1 is an Amphenol 10118193-0001LF micro-USB B (LCSC C132562), one pin'),
    'YQXATGGI': ('EAGLE multi-pad import artefact', 'per pad: 1 VBUS, 2 D-, 3 D+, 4 ID left open (No-ERC), 5 GND; MP1-MP4 are the SMT'),
    'DUEIHHEF': ('pin per pad: 5 is USB GND', 'shell pads, MH1/MH2 the shell legs in 0.50 x 1.20 mm plated slots, all on GND.'),
    'KACRHXAH': ('and MS1/MS2 the shield tabs', 'R27/R28 (the USB-C CC pull-downs) went with the USB-C. See docs/x1_microb.md.'),
}
apply = '--apply' in sys.argv
before = sch_netlist.build(PROJ)
recs = schdoc.split(schdoc.read_stream(SHEET))
for uid, (old, new) in NEW.items():
    hit = [i for i, (h, b) in enumerate(recs) if schdoc.field(b, 'UniqueID') == uid]
    assert len(hit) == 1 and schdoc.field(recs[hit[0]][1], 'RECORD') == '4', uid
    cur = schdoc.field(recs[hit[0]][1], 'Text')
    assert cur.startswith(old), (uid, cur)
    recs[hit[0]][1] = schdoc.set_field(recs[hit[0]][1], 'Text', new)
    print('record %d: %r -> %r' % (hit[0], cur, new))
data = schdoc.join(recs)
if not apply:
    print('dry run'); sys.exit(0)
if not os.path.exists(BACKUP):
    shutil.copy2(SHEET, BACKUP)
schdoc.write_stream(SHEET, data)
assert schdoc.split(schdoc.read_stream(SHEET))[0][1] == recs[0][1]
assert sch_netlist.build(PROJ) == before, 'netlist changed'
print('written, netlist identical; backup', BACKUP)
