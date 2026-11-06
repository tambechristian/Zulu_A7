# -*- coding: utf-8 -*-
"""Split the last two EAGLE multi-pad pins into one pin per pad, 2026-09-10.

EAGLE lets one symbol pin own several package pads; the Altium importer collapses that into a
single pin whose Designator is a comma list. Altium has no such concept, so those pins match no
footprint pad and the parts arrive on the board unconnected. X3 was fixed this way on 2026-09-06
(tools/x3_dm3d_sf.py); these are the two that were left.

  BTN  PTS810 tact switch, sheet 2.  Pins "1,2" and "3,4" -> 1, 2, 3, 4.
       Pads 1-2 are one terminal and 3-4 the other, so each new pad is tied to its partner with a
       stub back to the existing node. A short symbol line carries the eye from the switch
       terminal down to the added pad, and the Comment moves left out of the way.

  X1   Molex 105017-0001 micro-USB-B, sheet 1.  Pin "5,MH1,MH2,MP1,MP2,MP3,MP4,MS1,MS2" -> pin 5
       plus eight more, all GND: two mounting holes, four shell posts, two shield tabs. They go on
       the right edge of the symbol, bussed at x=240 and carried under the body to the GND port
       that already serves pin 5 at (180,1067) -- the corridor between X1 and U8 is free from
       x 235 to 295, and the USB5V0 wire at y=1040 is well clear below.

Mechanics follow x3_dm3d_sf.py: new child records go in right after the component's whole record
tree (its children plus the nested 44->45->46/48 implementation records), every OwnerIndex at or
past the insert point is shifted, loose wires and junctions are appended at the end, and the header
Weight is corrected. Run with the project closed in Altium:

    python tools/split_multipad_pins.py tools "Imported zulu_a7.PrjPcb/zulu_a7_1.SchDoc"
    python tools/split_multipad_pins.py tools "Imported zulu_a7.PrjPcb/zulu_a7_2.SchDoc"
"""
import sys
import random
import string

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else 'tools')
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def rec(body):
    body = body if isinstance(body, bytes) else body.encode()
    return [bytes(4), body + bytes(1)]          # every record ends with a NUL


# orientation lives in the low two bits of PinConglomerate: 0 right, 1 up, 2 left, 3 down
def reorient(cong, orient):
    return (int(cong) & ~3) | orient


# ---------------------------------------------------------------- what each part needs
# new_pins: (designator, name, x, y, orientation, pin_length)
JOBS = {
    'BTN': dict(
        rename={'1,2': '1', '3,4': '3'},
        template='1,2',
        new_pins=[('2', '1', 780, 994, 2, 10),
                  ('4', '2', 800, 994, 0, 10)],
        lines=[(780, 1014, 780, 994), (800, 1014, 800, 994)],
        wires=[(770, 994, 770, 1014), (810, 994, 810, 1014)],
        junctions=[(770, 1014), (810, 1014)],
        move_comment=(735, None),
        note=('2026-09-10: BTN pads 1-2 are one switch terminal and 3-4 the other. They were one '
              'pin each ("1,2" and "3,4"), an EAGLE multi-pad import artefact that matches no '
              'Altium footprint pad; now four pins, each pad on its partner\'s net.'),
        note_at=(620, 966),
    ),
    'X1': dict(
        rename={'5,MH1,MH2,MP1,MP2,MP3,MP4,MS1,MS2': '5'},
        template='5,MH1,MH2,MP1,MP2,MP3,MP4,MS1,MS2',
        new_pins=[('MH1', 'GND', 230, 1142, 0, 10),
                  ('MH2', 'GND', 230, 1132, 0, 10),
                  ('MP1', 'GND', 230, 1122, 0, 10),
                  ('MP2', 'GND', 230, 1112, 0, 10),
                  ('MP3', 'GND', 230, 1102, 0, 10),
                  ('MP4', 'GND', 230, 1092, 0, 10),
                  ('MS1', 'GND', 230, 1082, 0, 10),
                  ('MS2', 'GND', 230, 1072, 0, 10)],
        # the right edge already runs 1082..1142; carry it down to the last added pin
        extend_line=dict(uid='SFGWTWYY', key='Y2', value='1072'),
        wires=[(240, 1142, 240, 1067), (240, 1067, 180, 1067)],
        junctions=[(240, 1132), (240, 1122), (240, 1112), (240, 1102),
                   (240, 1092), (240, 1082), (240, 1072), (180, 1067)],
        note=('2026-09-10: X1 pin 5 owned nine pads ("5,MH1,MH2,MP1,MP2,MP3,MP4,MS1,MS2"), an '
              'EAGLE multi-pad import artefact that matches no Altium footprint pad. Now one pin '
              'per pad: 5 is USB GND, MH1/MH2 the mounting holes, MP1-MP4 the shell posts and '
              'MS1/MS2 the shield tabs, all on the same GND port.'),
        note_at=(330, 1160),
    ),
}


def main(path):
    data = read_stream(path, 'FileHeader')
    recs = split(data)
    done = []

    todo = []
    for want, job in JOBS.items():
        hits = [int(field(b, 'OwnerIndex')) + 1 for h, b in recs
                if b.startswith(b'|RECORD=34|') and field(b, 'Text') == want]
        if len(hits) == 1:
            todo.append((want, job, hits[0]))
        elif len(hits) > 1:
            raise SystemExit('%s appears %d times in %s' % (want, len(hits), path))
    if not todo:
        print('%s: neither BTN nor X1 on this sheet, nothing done' % path)
        return
    if len(todo) > 1:
        raise SystemExit('both parts on one sheet; this script edits one at a time')

    want, job, ci = todo[0]
    own = str(ci - 1)

    # the component's whole record tree, so inserts land after it
    kids = [i for i, (h, b) in enumerate(recs) if field(b, 'OwnerIndex') == own]
    tree, lvl = set(kids), kids
    while lvl:
        nxt = [i for i, (h, b) in enumerate(recs)
               if field(b, 'OwnerIndex') in {str(j - 1) for j in lvl} and i not in tree]
        tree |= set(nxt)
        lvl = nxt
    last = max(tree)

    # ---- rename the multi-pad pins, and keep one as the template for the new ones
    tpl = None
    for i in sorted(tree):
        b = recs[i][1]
        if not b.startswith(b'|RECORD=2|'):
            continue
        d = field(b, 'Designator')
        if d in job['rename']:
            recs[i][1] = set_field(b, 'Designator', job['rename'][d])
            done.append('pin "%s" -> %s' % (d, job['rename'][d]))
        if d == job['template']:
            tpl = recs[i][1]
    if tpl is None:
        print('%s: %s has no pin "%s" left - already split, nothing done'
              % (path, want, job['template']))
        return

    # ---- one small in-place geometry fix per part
    if job.get('extend_line'):
        e = job['extend_line']
        for i in sorted(tree):
            if field(recs[i][1], 'UniqueID') == e['uid']:
                recs[i][1] = set_field(recs[i][1], e['key'], e['value'])
                done.append('body edge %s -> %s' % (e['key'], e['value']))
                break
    if job.get('move_comment'):
        nx, ny = job['move_comment']
        for i in sorted(tree):
            b = recs[i][1]
            if b.startswith(b'|RECORD=41|') and field(b, 'Name') == 'Comment':
                if nx is not None:
                    b = set_field(b, 'Location.X', str(nx))
                if ny is not None:
                    b = set_field(b, 'Location.Y', str(ny))
                recs[i][1] = b
                done.append('Comment moved clear of the new pins')
                break

    # ---- the new pins, cloned from the pin they were split out of
    def pin(des, name, x, y, orient, length):
        b = tpl
        b = set_field(b, 'Designator', des)
        b = set_field(b, 'Name', name)
        b = set_field(b, 'Location.X', str(x))
        b = set_field(b, 'Location.Y', str(y))
        b = set_field(b, 'PinLength', str(length))
        b = set_field(b, 'PinConglomerate',
                      str(reorient(field(b, 'PinConglomerate'), orient)))
        b = set_field(b, 'UniqueID', uid())
        return rec(b)

    new_kids = [pin(*p) for p in job['new_pins']]
    for x1, y1, x2, y2 in job.get('lines', []):
        new_kids.append(rec('|RECORD=6|OwnerIndex=%s|IsNotAccesible=T|OwnerPartId=1|LineWidth=1'
                            '|Color=128|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d|UniqueID=%s'
                            % (own, x1, y1, x2, y2, uid())))

    n = len(new_kids)
    p = last + 1
    for i, (h, b) in enumerate(recs):
        o = field(b, 'OwnerIndex')
        if o is not None and int(o) + 1 >= p:
            recs[i][1] = set_field(b, 'OwnerIndex', str(int(o) + n))
    recs[p:p] = new_kids
    done.append('%d records inserted at %d' % (n, p))

    # AllPinCount, if the component carries one
    ci2 = ci if ci < p else ci + n
    comp = recs[ci2][1]
    if field(comp, 'AllPinCount'):
        recs[ci2][1] = set_field(comp, 'AllPinCount',
                                 str(int(field(comp, 'AllPinCount')) + len(job['new_pins'])))
        done.append('AllPinCount +%d' % len(job['new_pins']))

    # ---- loose wires, junctions and the note
    loose = []
    for x1, y1, x2, y2 in job.get('wires', []):
        loose.append(rec('|RECORD=27|OwnerPartId=-1|LineWidth=1|Color=32768|UniqueID=%s'
                         '|LocationCount=2|X1=%d|Y1=%d|X2=%d|Y2=%d' % (uid(), x1, y1, x2, y2)))
    for x, y in job.get('junctions', []):
        loose.append(rec('|RECORD=29|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Color=128'
                         '|Locked=T|UniqueID=%s' % (x, y, uid())))
    if job.get('note'):
        nx, ny = job['note_at']
        loose.append(rec('|RECORD=4|OwnerPartId=-1|Location.X=%d|Location.Y=%d|Orientation=0'
                         '|Color=8421504|FontID=3|Text=%s|UniqueID=%s'
                         % (nx, ny, job['note'], uid())))
    recs.extend(loose)
    done.append('%d loose records appended' % len(loose))

    hdr = recs[0][1]
    recs[0][1] = set_field(hdr, 'Weight', str(int(field(hdr, 'Weight')) + n + len(loose)))

    out = join(recs)
    write_stream(path, 'FileHeader', out)
    assert read_stream(path, 'FileHeader') == out
    print('%s  %s: %d records; %s' % (path, want, len(recs), '; '.join(done)))


if __name__ == '__main__':
    main(sys.argv[2])
