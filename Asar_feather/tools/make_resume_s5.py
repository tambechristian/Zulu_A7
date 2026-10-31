"""Write tools/resume_s5.sh from the command lines of the router passes running at a restart (2026-10-29).
    python tools/make_resume_s5.py <running_cmds.txt>
Each pass is relaunched with --seed pointing at its own --checkpoint file (the checkpoint holds the original seed
plus every net routed so far, so the routed nets are skipped) and appends to its original log."""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BS = chr(92)


def main():
    cmds = [l.strip() for l in open(sys.argv[1], encoding='utf-8-sig') if l.strip()]
    out = ['#!/bin/sh',
           '# relaunch the stage-5 passes that were running at the 2026-10-29 restart, each from its per-net checkpoint',
           '# (the checkpoint holds the original seed plus every net routed so far; routed nets are skipped).',
           '# run from the repo root:  sh tools/resume_s5.sh',
           'cd "$(dirname "$0")/.." || exit 1', '']
    for c in cmds:
        m = re.search(r'tools/router' + BS + '.py (.*)$', c)
        if not m:
            out.append('# NOT A ROUTER PASS: ' + c)
            continue
        args = m.group(1).replace(BS, '/')
        ck = re.search(r'--checkpoint (' + BS + 'S+)', args)
        o = re.search(r'--out (' + BS + 'S+)', args)
        if not ck or not o:
            out.append('# NOT RESUMABLE (no checkpoint): ' + c)
            continue
        args2 = re.sub(r'--seed ' + BS + 'S+', '--seed ' + ck.group(1), args)
        log = o.group(1).replace('.json', '.log')
        out.append('nohup python tools/router.py %s >> %s 2>&1 &' % (args2, log))
    out.append('wait')
    p = os.path.join(HERE, 'resume_s5.sh')
    open(p, 'w', newline=chr(10)).write(chr(10).join(out) + chr(10))
    print('%s: %d passes' % (p, sum(1 for l in out if l.startswith('nohup'))))
    for l in out:
        if l.startswith('nohup'):
            print('  ' + l[:150])


if __name__ == '__main__':
    main()
