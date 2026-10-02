# -*- coding: utf-8 -*-
"""Sheet 0, 2026-09-09: five things the block diagram says that are not true.

The block diagram is the index a newcomer and the layout engineer both start from, so a false
statement on it is worth more than a crooked one. These are the five the review found that are
factual rather than stylistic; the naming choices it also flagged are left alone and listed at the
bottom of this docstring.

1. "CHAN-I/O (28)" -> "CHAN-I/O (29)". The netlist holds CHAN0 through CHAN28, which is 29 nets.
   The sheet has already taught the reader that a number in brackets is a bus width, via CTRL (7),
   ADDRESS (15) and DATA (16), all three of which are right. 28 is a trap because it is also the
   highest channel number, so it survives a spot-check.

2. SDRAM-CLK is drawn leaving the FPGA at (460,612), running down to y 542, jogging right to x 480
   and coming back UP into an arrowhead at (480,612) pointing into the FPGA -- while the main line
   continues down to an arrowhead at (460,502) entering the SDRAM. It reads as a clock the FPGA
   sends out and receives back. There is no such path: the net is exactly two pads, U1-M1 and U3-38.
   The return branch and its arrowhead go, leaving one line with one arrowhead, which is how CTRL
   and ADDRESS beside it are drawn.

3. The note claims microSD sits "on six bank-34 balls of its own". It spans three banks. Confirmed
   from the package file and from the pin designators on sheet 5: CLK U8 and CMD U7 are bank 34,
   DAT0 C15, DAT1 B15 and DAT3 A16 are bank 16, DAT2 L3 is bank 35. The claim that matters -- that a
   card cannot reach the config bus -- is true and is kept.

4. The XADC link is drawn as a thin line with an arrowhead at BOTH ends, i.e. bidirectional. It is
   not: X2-39 and X2-40 carry ANALOG-IO0/ANALOG-IO1 through dividers into the XADC pins AIN15_P (G3)
   and AIN16_P (H2). Two analogue inputs, header to FPGA, one way. The arrowhead at the header end
   goes and the line is extended to the header edge, giving the flat-ended shape the sheet already
   uses for one-way links.

5. The LED/Button link is drawn with a single arrowhead pointing INTO the FPGA, which on this
   sheet's own convention means the FPGA only receives. Five of the six signals go the other way:
   LED0_R (P19), LED0_G (R18), LED0_B (N19), LED1 (N18) and LED2 (M19) are FPGA outputs, and only
   BTN (N17) is an input. An arrowhead into the LED/Button block is added, in the same 8-unit style
   as the Pmod link's, making it bidirectional and honest.

CHECKED AND NOT CHANGED: the review also said the Pmod link was drawn with a single arrowhead into
the FPGA. It is not -- it already has one at each end, into the FPGA at (615,722) and up into the
block at (720,787) -- so it is correct as drawn and is left alone.

DELIBERATELY NOT CHANGED, because they are naming style rather than error: the rail nicknames +5V,
+3.3V, +1.8V and +1.0V, which are not the net names (USB5V0, VCC3V3, VCC1V8, VCC1V0); the flash link
labels FCS_B, CCLK and DQ[3:0], which are pin names where the neighbouring SD-CLK/SD-CMD/SD-DAT are
net names; the 12 MHz oscillator drawn as a two-terminal passive when Q1 is an active four-pad part;
and the absence of designators on the blocks.

Ten line records are deleted and two added, so every later OwnerIndex is renumbered and the header
count rewritten -- this is the sheet that was left unopenable once by skipping exactly that. Refuses
to run twice.

    python tools/sheet0_fixes.py tools "Imported zulu_a7.PrjPcb/zulu_a7_0.SchDoc"
"""
import sys, re, random, string
sys.path.insert(0, sys.argv[1])
from fix_text_orientation import read_stream, write_stream, split, join, field, set_field

CHAN_OLD, CHAN_NEW = 'CHAN-I/O (28)', 'CHAN-I/O (29)'
NOTE_OLD = ('CLK, CMD and DAT[3:0] on six bank-34 balls of ~1its own, so a card cannot touch the '
            'config bus.')
NOTE_NEW = ('CLK and CMD in bank 34, DAT0/DAT1/DAT3 in 16 ~1and DAT2 in 35 -- none of them on the '
            'config bus.')
# 2. the SDRAM-CLK return branch: the jog right, the run back up, and the arrowhead into the FPGA
SDRAM_KILL = {((460, 542), (480, 542)), ((480, 542), (480, 602)),
              ((475, 602), (480, 612)), ((480, 602), (475, 602)),
              ((485, 602), (480, 602)), ((480, 612), (485, 602))}
# 4. the XADC arrowhead at the header end, and the line that must reach the edge without it
XADC_KILL = {((725, 702), (735, 697)), ((735, 697), (725, 692)),
             ((725, 697), (725, 702)), ((725, 692), (725, 697))}
XADC_LINE_OLD, XADC_LINE_NEW = ((725, 697), (625, 697)), ((735, 697), (625, 697))
# 5. the LED/Button bus, shortened to leave room for an arrowhead into the block
LED_SHORTEN = {((720, 639), (720, 552)): ((720, 639), (720, 560)),
               ((700, 619), (700, 552)): ((700, 619), (700, 560))}
LED_ARROW = [((700, 560), (710, 552)), ((710, 552), (720, 560))]


def uid():
    return ''.join(random.choice(string.ascii_uppercase) for _ in range(8))


def new_uid(b):
    """Every cloned record needs its own identity; two arrowhead halves off one template would
    otherwise share a UniqueID, which is the trap tools/sc189_pin_ids.py had to clean up after."""
    return re.sub(rb'\|UniqueID=[A-Z]{8}', lambda m: b'|UniqueID=' + uid().encode(), b)


def num(b, k):
    v = field(b, k)
    return int(v) if v is not None else None


def owner_list_index(b):
    o = field(b, 'OwnerIndex')
    return int(o) + 1 if o is not None else None


def pts_of(b):
    if not b.startswith(b'|RECORD=6|'):
        return None
    n = num(b, 'LocationCount') or 0
    return tuple((num(b, f'X{k}'), num(b, f'Y{k}')) for k in range(1, n + 1))


def set_pts(b, pts):
    for k, (x, y) in enumerate(pts, 1):
        b = set_field(set_field(b, f'X{k}', str(x)), f'Y{k}', str(y))
    return set_field(b, 'LocationCount', str(len(pts)))


def main(path):
    recs = split(read_stream(path, 'FileHeader'))
    N = len(recs)
    assert int(field(recs[0][1], 'Weight')) == N - 1, 'header count is already wrong'
    if not any(field(b, 'Text') == CHAN_OLD for h, b in recs):
        raise SystemExit('sheet 0 has already been corrected; nothing done')

    template = None
    for h, b in recs:
        if pts_of(b) in SDRAM_KILL:
            template = b                                   # style for the arrowhead we add
    assert template is not None, 'no line to copy the arrowhead style from'

    out, done = [], set()
    for i, (h, b) in enumerate(recs):
        p = pts_of(b)
        if p is not None and len(p) == 2:
            if p in SDRAM_KILL:
                done.add('sdram'); continue
            if p in XADC_KILL:
                done.add('xadc arrow'); continue
            if p == XADC_LINE_OLD:
                b = set_pts(b, XADC_LINE_NEW); done.add('xadc line')
            elif p in LED_SHORTEN:
                b = set_pts(b, LED_SHORTEN[p]); done.add('led bus')
        elif b.startswith(b'|RECORD=4|') and field(b, 'Text') == CHAN_OLD:
            b = set_field(b, 'Text', CHAN_NEW); done.add('chan count')
        elif b.startswith(b'|RECORD=28|') and NOTE_OLD in (field(b, 'Text') or ''):
            b = set_field(b, 'Text', field(b, 'Text').replace(NOTE_OLD, NOTE_NEW))
            done.add('note')
        out.append([h, b])

    want = {'sdram', 'xadc arrow', 'xadc line', 'led bus', 'chan count', 'note'}
    assert done == want, sorted(want ^ done)

    keep = [i for i, (h, b) in enumerate(recs)
            if not (pts_of(b) is not None and len(pts_of(b)) == 2
                    and (pts_of(b) in SDRAM_KILL or pts_of(b) in XADC_KILL))]
    assert len(keep) == len(out), (len(keep), len(out))
    newpos = {old: new for new, old in enumerate(keep)}
    fixed = []
    for old, (h, b) in zip(keep, out):
        oi = owner_list_index(b)
        if oi is not None:
            assert oi in newpos, f'record {old} is owned by a deleted record'
            b = set_field(b, 'OwnerIndex', str(newpos[oi] - 1))
        fixed.append([h, b])
    for pts in LED_ARROW:                                  # appended, so no index moves
        fixed.append([bytes(4), set_pts(new_uid(template), pts)])
    fixed[0][1] = set_field(fixed[0][1], 'Weight', str(len(fixed) - 1))
    blob = join(fixed)
    write_stream(path, 'FileHeader', blob)
    assert read_stream(path, 'FileHeader') == blob
    print(f'sheet 0: {N} -> {len(fixed)} records ({N - len(keep)} lines deleted, {len(LED_ARROW)} added)')
    verify(path)


def verify(path):
    recs = split(read_stream(path, 'FileHeader'))
    assert int(field(recs[0][1], 'Weight')) == len(recs) - 1, 'header count'
    assert all(b.endswith(b'\x00') for h, b in recs), 'a record lost its terminator'
    uids = [field(b, 'UniqueID') for h, b in recs if field(b, 'UniqueID')]
    assert len(uids) == len(set(uids)), 'duplicate UniqueID'
    for i, (h, b) in enumerate(recs):
        oi = owner_list_index(b)
        if oi is not None:
            assert 0 <= oi < len(recs) and recs[oi][1].startswith(
                (b'|RECORD=1|', b'|RECORD=2|', b'|RECORD=44|', b'|RECORD=45|')), (i, oi)
    lines = {pts_of(b) for h, b in recs if b.startswith(b'|RECORD=6|')}
    texts = {field(b, 'Text') for h, b in recs if b.startswith((b'|RECORD=4|', b'|RECORD=28|'))}
    assert CHAN_NEW in texts and CHAN_OLD not in texts, 'the channel count is not corrected'
    assert any(NOTE_NEW in (t or '') for t in texts), 'the microSD note is not corrected'
    assert not (SDRAM_KILL & lines), 'part of the SDRAM-CLK return path survived'
    assert ((460, 612), (460, 542)) in lines and ((460, 542), (460, 512)) in lines, 'SDRAM-CLK is broken'
    assert ((460, 502), (455, 512)) in lines, 'the SDRAM arrowhead went missing'
    assert not (XADC_KILL & lines), 'the XADC header-end arrowhead survived'
    assert XADC_LINE_NEW in lines, 'the XADC line does not reach the header'
    assert ((625, 702), (615, 697)) in lines, 'the XADC arrowhead into the FPGA went missing'
    for pts in LED_ARROW:
        assert pts in lines, f'the LED/Button arrowhead is missing {pts}'
    for old, new in LED_SHORTEN.items():
        assert old not in lines and new in lines, f'the LED/Button bus was not shortened: {old}'
    assert ((615, 722), (622, 714)) in lines and ((727, 779), (720, 787)) in lines, \
        'the Pmod link lost an arrowhead -- it was correct and should not have been touched'
    print(f'verify: {len(recs)} records; 29 channels, one-way SDRAM-CLK and XADC, '
          'a two-ended LED/Button link, and the Pmod link untouched')


if __name__ == '__main__':
    main(sys.argv[2])
