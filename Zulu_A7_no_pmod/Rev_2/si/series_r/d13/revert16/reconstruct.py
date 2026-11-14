"""Rebuild the 16-R docs/dq_series_resistors.md from the fallback writer's two Read results, then prove it by
replaying every later edit (writer, reviewer) and checking the result against the current doc minus my own edits."""
import json, re, hashlib, sys
W = r'C:/Users/tambe/.claude/projects/C--Users-tambe-Documents-Electronics-Zulu-A7-Zulu-A7-no-pmod/52f614a9-b2f5-42ff-ae9c-6f659acff616/subagents/workflows/wf_1462b8d7-ebc/'
DOC = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/docs/dq_series_resistors.md'
def events(f):
    uses = {}; out = []
    for line in open(W + f, encoding='utf-8'):
        d = json.loads(line); m = d.get('message', {})
        cs = m.get('content') if isinstance(m.get('content'), list) else []
        for c in cs:
            if c.get('type') == 'tool_use':
                uses[c['id']] = c
            elif c.get('type') == 'tool_result' and c.get('tool_use_id') in uses:
                u = uses[c['tool_use_id']]
                if u['input'].get('file_path','').replace(chr(92),'/').endswith('docs/dq_series_resistors.md') and u['name'] in ('Read', 'Edit', 'Write', 'MultiEdit'):
                    txt = c['content'] if isinstance(c['content'], str) else ''.join(x.get('text', '') for x in c['content'])
                    out.append((u['name'], u['input'], txt, c.get('is_error', False)))
    return out
ev = events('agent-a45e555ca5be99c6b.jsonl')
reads = [e for e in ev if e[0] == 'Read'][:2]
lines = {}
for name, inp, txt, err in reads:
    for l in txt.split('\n'):
        mm = re.match(r'^\s*(\d+)\t(.*)$', l)
        if mm:
            lines.setdefault(int(mm.group(1)), mm.group(2))
n = max(lines); missing = [i for i in range(1, n + 1) if i not in lines]
print('lines', n, 'missing', missing[:10])
orig = '\n'.join(lines[i] for i in range(1, n + 1)) + '\n'
open('dq_series_resistors_16r_reconstructed.md', 'w', encoding='utf-8', newline='\n').write(orig)
# replay
s = orig
def replay(s, evs, tag):
    k = 0
    for name, inp, txt, err in evs:
        if err or name == 'Read': continue
        if name == 'Edit':
            a, b = inp['old_string'], inp['new_string']
            if inp.get('replace_all'): s = s.replace(a, b)
            else:
                if s.count(a) != 1: print(tag, 'edit not unique/absent', s.count(a), repr(a[:80])); sys.exit(1)
                s = s.replace(a, b)
        elif name == 'Write':
            s = inp['content']
        k += 1
    print(tag, 'replayed', k)
    return s
s = replay(s, ev, 'writer')
s = replay(s, events('agent-af5441c465c71b043.jsonl'), 'reviewer')
cur = open(DOC, encoding='utf-8').read()
# my three edits after the reviewer
mine = [
("""This plan uses that recipe for
**15 resistors**. Note: `schematic_plan.md` itself still describes the 16-resistor size (R119-R134, 16 SDRAM-Dn nets,
U3-50 -> SDRAM-D13, a 32-member SDRAM_DATA). Use the counts in this section, not those. If the ECO were built from
the 16-resistor text, U3-50 would be re-netted to SDRAM-D13 with no copper behind it, and DRC would show it Un-Routed.""",
"""This plan uses that recipe for
**15 resistors**; `schematic_plan.md` was updated to 15 on 2026-11-13 (its 16-resistor text is archived as
`si/series_r/d13/fallback15/schematic_plan_16r.md`). The same update corrected its pin orientation: it had pin 1 on
Dn, which would have made the ECO net every R's pads opposite to this plan's copper."""),
("Each row is: label Dn — R — label SDRAM-Dn. Pin 1 goes\n  to SDRAM-Dn.", "Each row is: label SDRAM-Dn — pin 1, R, pin 2 — label Dn\n  (pin 1 is the template R24's left pin). Pin 1 must be SDRAM-Dn to match pad 1 in §6.1."),
("and copy `d13/fold/plan_fixed.json` to `dq_series_r_plan_16.json` and over `dq_series_r_plan.json`. Then the fallback: `python build15.py` in `d13/fallback15` (it reads `dq_series_r_plan.json` as the 16-resistor plan and checks its md5 `7c2b8ae6`; update it),",
 "and copy `d13/fold/plan_fixed.json` to `dq_series_r_plan_16.json`. Then the fallback: `python build15.py` in `d13/fallback15` (it reads `dq_series_r_plan_16.json` and checks its md5 `7c2b8ae6`; update it),"),
(" `build15.py` reads `dq_series_r_plan.json` as the 16-resistor base and checks its md5, so point it at `dq_series_r_plan_16.json` before re-running |",
 " `build15.py` reads `dq_series_r_plan_16.json` as the 16-resistor base and checks its md5 (re-run 2026-11-13: reproduces `plan15.json` byte for byte) |")]
for a, b in mine:
    assert s.count(a) == 1, a[:60]; s = s.replace(a, b)
print('replay == current doc:', s == cur, hashlib.md5(orig.encode()).hexdigest())
