"""Repair the clearance misses route_check.py finds in a plan (2026-11-05): each violating plan track or via is cut
and re-joined by finish.py --kick (wider raster allowance first), until the plan PASSes or nothing changes.

    python tools/fix_clear.py <plan.json> <model.json> <out.json> [--judge 0.0762] [--clear 0.080]
                              [--laser-small 0.25/0.10] [--rounds 4]"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def opt(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def check(plan, model, judge):
    r = subprocess.run([PY, os.path.join(HERE, 'route_check.py'), plan, model, '--clear', judge],
                       capture_output=True, text=True)
    kicks = []
    for l in r.stdout.splitlines():
        m = re.match(r'\s*track (\S+) .+? \(([-\d.]+),([-\d.]+)\)-\(([-\d.]+),([-\d.]+)\) [-\d.]+ from', l)
        if m:
            x1, y1, x2, y2 = [float(v) for v in m.groups()[1:]]
            kicks.append((m.group(1), (x1 + x2) / 2, (y1 + y2) / 2, 0.30))
            continue
        m = re.match(r'\s*(?:hole-hole )?via (\S+) at ([-\d.]+),([-\d.]+)', l)
        if m:
            kicks.append((m.group(1), float(m.group(2)), float(m.group(3)), 0.20))
    lines = r.stdout.strip().splitlines()
    return kicks, lines


def main():
    plan, model, out = sys.argv[1:4]
    judge, clear = opt('--judge', '0.0762'), opt('--clear', '0.080')
    laser, rounds = opt('--laser-small', '0.25/0.10'), int(opt('--rounds', '4'))
    cur = plan
    for i in range(rounds):
        kicks, lines = check(cur, model, judge)
        print('round %d: %s | %s | %d kicks' % (i, lines[-2], lines[-1], len(kicks)), flush=True)
        if not kicks:
            break
        seen, uniq = [], []
        for k in kicks:                                # one kick per net and neighbourhood
            if not any(k[0] == s[0] and abs(k[1] - s[1]) < 0.25 and abs(k[2] - s[2]) < 0.25 for s in seen):
                uniq.append(k)
            seen.append(k)
        nxt = '%s.fix%d.json' % (os.path.splitext(out)[0], i + 1)
        arg = ';'.join('%s@%.3f,%.3f,%.2f' % k for k in uniq)
        r = subprocess.run([PY, os.path.join(HERE, 'finish.py'), '--model', model, '--seed', cur, '--out', nxt,
                            '--clear', clear, '--slack', '0.005', '--laser-small', laser, '--kick', arg, '--no-open',
                            '--lpops', '300000', '--pops', '600000', '--soft', '0.2', '--hw', '1.5'],
                           capture_output=True, text=True)
        print('\n'.join(l for l in r.stdout.splitlines() if 'kick' in l or l.startswith('finish')), flush=True)
        if r.returncode:
            print(r.stderr[-1500:])
            break
        cur = nxt
    if cur != out:
        shutil.copy(cur, out)
    kicks, lines = check(out, model, judge)
    print('final: %s | %s | %s' % (lines[-3], lines[-2], lines[-1]))


if __name__ == '__main__':
    main()
