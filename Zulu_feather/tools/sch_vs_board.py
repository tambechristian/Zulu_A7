"""Schematic vs board report for the Feather project.

Schematic side: sch_netlist.py reading the SchDocs (pins, nets) plus each part's footprint ModelName.
Board side: tools/board_dump.json (run board_dump.py first), i.e. the saved PcbDoc read through KiCad's importer.
Reported:
  1. parts only on one side, and footprint mismatches;
  2. schematic pins with no pad of that number, and pads (with a name) with no schematic pin;
  3. per pin: the schematic net vs the net of every pad carrying that number (multi-pad pins, e.g. USB-C VBUS,
     must agree on all pads). Unnamed schematic nets are matched by membership, not by name;
  4. board-only nets (a net name on pads that the schematic does not have).
Exit code 0 only when everything agrees.
    python tools/sch_vs_board.py
"""
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sch_netlist import build  # noqa: E402
from schdoc import field, owner, read_stream, split  # noqa: E402

ROOT = os.path.join(os.path.dirname(HERE), 'Zulu_feather.PrjPcb')


def sch_parts():
    """{ref: footprint ModelName} for every placed part (multi-part parts give one entry)."""
    out = {}
    for path in glob.glob(os.path.join(ROOT, '*.SchDoc')):
        recs = split(read_stream(path))
        refs = {owner(b): field(b, 'Text') for h, b in recs if field(b, 'RECORD') == '34'}
        for i, (h, b) in enumerate(recs):
            if field(b, 'RECORD') == '45' and field(b, 'IsCurrent') == 'T':
                il = owner(b)
                ref = refs.get(owner(recs[il][1]))
                if ref and field(b, 'ModelName'):          # title-block FRAME symbols carry no footprint
                    out[ref] = field(b, 'ModelName')
    return out


def main():
    nets = build(ROOT)
    pin_net = {}
    for name, pins in nets.items():
        for p in pins:
            pin_net[p] = name
    parts = sch_parts()
    dump = json.load(open(os.path.join(HERE, 'board_dump.json')))
    dump.pop('_board', None)
    problems = []

    # 1. parts and footprints
    for ref in sorted(set(parts) - set(dump)):
        problems.append('PART only in schematic: %s (%s)' % (ref, parts[ref]))
    for ref in sorted(set(dump) - set(parts)):
        problems.append('PART only on board: %s (%s)' % (ref, dump[ref]['footprint']))
    for ref in sorted(set(parts) & set(dump)):
        if parts[ref] != dump[ref]['footprint']:
            problems.append('FOOTPRINT %s: schematic %s, board %s' % (ref, parts[ref], dump[ref]['footprint']))

    # 2./3. pins vs pads
    pads = defaultdict(list)                       # (ref, number) -> [board net, ...]
    for ref, c in dump.items():
        for p in c['pads']:
            if p['name']:
                pads[(ref, p['name'])].append(p['net'])
    sch_pins = {p for p in pin_net if p[0] in dump}
    for p in sorted(sch_pins - set(pads)):
        problems.append('PIN without pad: %s-%s (net %s)' % (p[0], p[1], pin_net[p]))
    for p in sorted(set(pads) - set(pin_net)):
        if p[0] in parts and any(pads[p]):
            problems.append('PAD without pin but with a net: %s-%s (%s)' % (p[0], p[1], ','.join(pads[p])))

    # nets: map each schematic net to the board net names its pads carry
    sch_to_board = defaultdict(set)
    for p in sch_pins & set(pads):
        for bn in pads[p]:
            sch_to_board[pin_net[p]].add(bn)
    single_pin = {k for k, v in nets.items() if len(v) == 1}
    for sn, bns in sorted(sch_to_board.items()):
        named = not sn.startswith('N$')
        if len(bns) != 1:
            problems.append('NET %s: its pads carry %d board nets %s' % (sn, len(bns), sorted(bns)))
        elif named and next(iter(bns)) != sn and not (sn in single_pin and next(iter(bns)) == ''):
            problems.append('NET %s: board calls it %r' % (sn, next(iter(bns))))
        elif not named and sn not in single_pin and next(iter(bns)) == '':
            problems.append('NET %s (%d pins): no net on the board' % (sn, len(nets[sn])))
        elif not named and sn in single_pin and next(iter(bns)) != '':
            problems.append('STALE NET NAME %s on the board for unconnected pin %s' % (next(iter(bns)), sn[2:]))
    # a board net must not span two schematic nets
    board_to_sch = defaultdict(set)
    for p in sch_pins & set(pads):
        for bn in pads[p]:
            if bn:
                board_to_sch[bn].add(pin_net[p])
    for bn, sns in sorted(board_to_sch.items()):
        if len(sns) > 1:
            problems.append('BOARD NET %s joins schematic nets %s' % (bn, sorted(sns)))
    # 4. board-only net names
    sch_names = set(nets)
    board_names = {bn for v in pads.values() for bn in v if bn}
    for bn in sorted(board_names - sch_names - {next(iter(v)) for v in sch_to_board.values() if len(v) == 1}):
        problems.append('BOARD-ONLY NET %s' % bn)

    n_pins = len(sch_pins)
    n_multi = sum(1 for v in nets.values() if len(v) > 1)
    print('schematic: %d parts, %d pins, %d multi-pin nets | board: %d parts, %d named pads, %d net names' % (
        len(parts), n_pins, n_multi, len(dump), len(pads), len(board_names)))
    for line in problems:
        print('  ' + line)
    print('MATCH' if not problems else '%d DIFFERENCES' % len(problems))
    return 0 if not problems else 1


if __name__ == '__main__':
    sys.exit(main())
