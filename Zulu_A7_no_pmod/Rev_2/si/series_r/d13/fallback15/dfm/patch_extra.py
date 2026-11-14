"""one-off patch of p15_extra.py (refines three over-broad checks of the first run)"""
s = open('p15_extra.py', encoding='utf-8').read()


def rep(a, b):
    global s
    assert s.count(a) == 1, a
    s = s.replace(a, b)


rep("""            if any(math.hypot(x - u247['x'], y - u247['y']) < 1.5 for x in xs for y in ys) or it.get('net') == 'GND' and \\
                    any(abs(x - 38.2) < 0.3 for x in xs):""",
    """            if it.get('net') == 'GND' and any(math.hypot(x - u247['x'], y - u247['y']) < 1.5 for x in xs for y in ys):""")
rep("plan items within 1.5 mm of U2-47", "GND plan items within 1.5 mm of U2-47")
rep("""        a13 = collections.Counter(k(x) for x in p13.get(key, []))""",
    """        a13 = collections.Counter(k(x) for x in p13.get(key, []))
        if key == 'vippo':     # the 13-R plan has no vippo key; its R128/R131 entries first appear in the 16-R plan
            a13 = collections.Counter(k(x) for x in p16.get(key, []) if x['pad'].split('-')[0] in ('R128', 'R131'))""")
rep("""        spans = sorted('%s>%s %.2f/%.2f' % (v.span[0] if v.span[0] not in ('Top', 'Bottom') else v.span[0],
                                            v.span[-1], v.size, v.hole) for v in vs)""",
    """        stack = [v for v in after if v.kind == 'via' and any(math.hypot(v.x - w.x, v.y - w.y) < 1e-4 for w in vs)]
        spans = sorted('%s>%s %.2f/%.2f' % (v.span[0], v.span[-1], v.size, v.hole) for v in stack)
        vs = stack""")
rep("""                        res.append((o.ident, '%s end (%.4f,%.4f)' % (o.d(), x, y)))""",
    """                        res.append((('trk', o.layer, round(x, 4), round(y, 4)), '%s end (%.4f,%.4f)' % (o.d(), x, y)))""")
rep("""                        res.append((o.ident + (L,), '%s nothing on %s' % (o.d(), L)))""",
    """                        res.append((('via', round(o.x, 4), round(o.y, 4), o.span[0], o.span[-1], L), '%s nothing on %s' % (o.d(), L)))""")
rep("""    say('   12h NetAntennae (tol 0) whole board: baseline %d, after %d, NEW %d' % (len(an_b), len(an_a), len(an_new)))""",
    """    say('   12h NetAntennae (tol 0) whole board, keyed by geometry (net renames ignored): baseline %d (track ends %d, via '
        'span ends %d), after %d (track ends %d), NEW %d' % (len(an_b), sum(r[0][0] == 'trk' for r in an_b),
                                                           sum(r[0][0] == 'via' for r in an_b), len(an_a),
                                                           sum(r[0][0] == 'trk' for r in an_a), len(an_new)))
    for r in [r for r in an_b if r[0][0] == 'trk'][:6]:
        say('       baseline track end:', r[1])""")
rep("""    for r in an_new:
        hard('net-antenna', r[1])""",
    """    for r in an_new:
        (hard if r[0][0] == 'trk' else adv)('net-antenna', r[1])""")
open('p15_extra.py', 'w', encoding='utf-8', newline='\n').write(s)
print('patched')
