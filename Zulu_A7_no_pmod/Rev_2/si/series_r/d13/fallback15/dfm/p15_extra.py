"""p15_extra.py -- plan15-specific adversarial checks, called from adv15.py main() with its globals/locals.

12a remnant scan (no D13 / SDRAM-D13 / R132 / gnd47 item anywhere except the 'source' note)
12b plan15 == 13-R plan + (16-R delta restricted to D14/D15 nets), recomputed independently of build15.py
12c D13 untouched: after-board D13 objects byte-equal to the PcbDoc's, no SDRAM-D13 anywhere, ONE island U3-50..U1-H1
12d U2-47 GND tie: the original GND copper at U2-47 alive, nothing new within 1 mm, U2-47 on the main GND island
12e VIPPO list == geometric via-in-pad detection (pads, nets, via spans) -- exactly 6 sites
12f microvia typing list: every entry matches a via of the same size/hole/span/net; every non-thru via in 'vias' typed
12g renamed_existing counts vs the plan's own 'rename' items
12h NetAntennae (tolerance 0) on the WHOLE after-board: every track end / via span end touches same-net copper;
    baseline subtracted
12i U1 designator (stays at its PcbDoc position) vs every Top pad opening of the after-board, nominal + conservative box
12j ComponentClearance calibration on the baseline (pairs of existing parts under 0.254 on a board that is DRC 0)
12k new copper to board edge; designators hidden on every new part
"""
import collections, json, math


def run(G, Lc, hard, adv, say, OUT):
    BX, PL, A = G['BX'], G['PL'], G['A']
    base, after = Lc['base'], Lc['after']
    sgap, circ, near, lname = G['sgap'], G['circ'], G['near'], G['lname']
    ufa, ia, pia = Lc['ufa'], Lc['ia'], Lc['pia']
    ufb = Lc['ufb']
    pours_a = Lc['pours_a']
    POLYS = G['POLYS']
    SR = G['SR']
    k = lambda x: json.dumps(x, sort_keys=True)
    X = {}

    say('\n== 12. plan15-specific checks')
    # ------------------------------------------------------------------ 12a remnants
    body = {kk: v for kk, v in PL.items() if kk != 'source'}
    sb = json.dumps(body)
    rem = {t: sb.count(t) for t in ('D13', 'R132', 'gnd47', 'GND47', '"U2"')}
    # GND items near U2-47 (the 16-R re-tie) in any list
    u247 = next(p for p in BX['pads'] if p['ref'] == 'U2' and p['pad'] == '47')
    near47 = []
    for key in ('tracks', 'vias', 'remove', 'remove_vias', 'microvias'):
        for it in PL.get(key, []):
            xs = [it[a] for a in ('x', 'x1', 'x2') if a in it]
            ys = [it[a] for a in ('y', 'y1', 'y2') if a in it]
            if it.get('net') == 'GND' and any(math.hypot(x - u247['x'], y - u247['y']) < 1.5 for x in xs for y in ys):
                near47.append((key, it))
    say('   12a remnant token counts outside "source": %s; GND plan items within 1.5 mm of U2-47 (%.4f,%.4f): %d' % (
        rem, u247['x'], u247['y'], len(near47)))
    for kk, it in near47:
        say('      ', kk, k(it))
    if any(rem.values()):
        hard('remnant', 'plan15 carries D13/R132/gnd47 tokens outside source: %s' % rem)
    if near47:
        hard('remnant', '%d plan items near U2-47' % len(near47))
    X['remnants'] = rem

    # ------------------------------------------------------------------ 12b plan15 == 13-R + D14/D15 delta
    p13 = json.load(open(SR + '/dq_series_r_plan_13.json'))
    p16 = json.load(open(SR + '/dq_series_r_plan.json'))
    keep = {'D14', 'D15', 'SDRAM-D14', 'SDRAM-D15'}
    bad = []
    for key in ('tracks', 'vias', 'remove', 'remove_vias', 'microvias', 'renet_pads', 'parts', 'vippo'):
        a15 = collections.Counter(k(x) for x in PL.get(key, []))
        a13 = collections.Counter(k(x) for x in p13.get(key, []))
        if key == 'vippo':     # the 13-R plan has no vippo key; its R128/R131 entries first appear in the 16-R plan
            a13 = collections.Counter(k(x) for x in p16.get(key, []) if x['pad'].split('-')[0] in ('R128', 'R131'))
        a16 = collections.Counter(k(x) for x in p16.get(key, []))
        extra = a15 - a13
        missing13 = a13 - a15
        not16 = a15 - a16
        # what the 16-R plan has beyond the 13-R plan, restricted to D14/D15
        d16 = a16 - a13
        want = collections.Counter()
        for s_, n in d16.items():
            o = json.loads(s_)
            nets = {o.get('net')} if 'net' in o else {o['pad1']['net'], o['pad2']['net']} if 'pad1' in o else set()
            if nets & keep:
                want[s_] = n
        dif1 = extra - want
        dif2 = want - extra
        say('   12b %-12s 13-R %3d  plan15 %3d  16-R %3d | extra over 13-R %d, 16-R D14/D15 delta %d, extra-not-delta %d, '
            'delta-not-in-plan15 %d, 13-R items missing %d, plan15 items not in 16-R %d' % (
                key, sum(a13.values()), sum(a15.values()), sum(a16.values()), sum(extra.values()), sum(want.values()),
                sum(dif1.values()), sum(dif2.values()), sum(missing13.values()), sum(not16.values())))
        for s_ in list(dif1) + list(dif2) + list(missing13) + list(not16):
            say('        diff item:', s_[:200])
        if dif1 or dif2 or missing13 or not16:
            bad.append(key)
    nca = PL.get('net_class_add', {}).get('SDRAM_DATA', [])
    nc13 = p13.get('net_class_add', {}).get('SDRAM_DATA', [])
    say('   12b net_class_add SDRAM_DATA: plan15 %s; 13-R + D14/D15 = %s' % (
        sorted(nca) == sorted(nc13 + ['SDRAM-D14', 'SDRAM-D15']), 'SDRAM-D13' in nca))
    if sorted(nca) != sorted(nc13 + ['SDRAM-D14', 'SDRAM-D15']):
        bad.append('net_class_add')
    for key in bad:
        hard('plan-delta', 'plan15 %s is not 13-R + D14/D15 delta' % key)
    X['delta_bad'] = bad

    # ------------------------------------------------------------------ 12c D13 untouched
    bD13 = sorted(k(o.src) for o in base if o.net == 'D13' and o.kind != 'pad')
    aD13 = sorted(k(o.src) for o in after if o.net == 'D13' and o.kind != 'pad')
    bpads = sorted('%s-%s' % (o.comp, o.pad) for o in base if o.net == 'D13' and o.kind == 'pad')
    apads = sorted('%s-%s' % (o.comp, o.pad) for o in after if o.net == 'D13' and o.kind == 'pad')
    sd13 = [o.d() for o in after if o.net == 'SDRAM-D13']
    newd13 = [o.d() for o in after if o.net == 'D13' and o.new]
    isl = len(ia.get('D13', ()))
    pisl = len(pia.get('D13', ()))
    ok = bD13 == aD13 and bpads == apads == ['U1-H1', 'U3-50'] and not sd13 and not newd13 and isl == 1 and pisl == 1
    say('   12c D13: base objects %d, after %d, byte-equal %s; pads base %s after %s; SDRAM-D13 objects %d; new D13 '
        'objects %d; copper islands %d pad islands %d -> %s' % (
            len(bD13), len(aD13), bD13 == aD13, bpads, apads, len(sd13), len(newd13), isl, pisl, 'OK' if ok else 'FAIL'))
    tl = sum(math.hypot(o.src['x2'] - o.src['x1'], o.src['y2'] - o.src['y1']) for o in after if o.net == 'D13' and o.kind == 'track')
    say('       D13 copper: %d tracks %.3f mm, %d vias (%s)' % (
        sum(o.kind == 'track' for o in after if o.net == 'D13'), tl, sum(o.kind == 'via' for o in after if o.net == 'D13'),
        ', '.join(o.d() for o in after if o.net == 'D13' and o.kind == 'via')))
    if not ok:
        hard('d13', 'D13 not untouched / not one island: base %d after %d eq %s sdram %d new %d isl %d' % (
            len(bD13), len(aD13), bD13 == aD13, len(sd13), len(newd13), isl))
    u350 = next(o for o in after if o.kind == 'pad' and o.comp == 'U3' and o.pad == '50')
    if u350.net != 'D13' or u350.new:
        hard('d13', 'U3-50 net %s new=%s' % (u350.net, u350.new))
    X['d13'] = dict(ok=ok, objects=len(aD13), islands=isl)

    # ------------------------------------------------------------------ 12d U2-47 GND tie
    p47 = next(o for o in after if o.kind == 'pad' and o.comp == 'U2' and o.pad == '47')
    side = p47.layer
    b47 = [o for o in base if o.net == 'GND' and o.kind != 'pad' and side in o.shp and sgap(o.shp[side], next(
        q for q in base if q.kind == 'pad' and q.comp == 'U2' and q.pad == '47').shp[side]) <= 1e-6]
    aid = {o.ident for o in after}
    alive47 = [o.d() for o in b47 if o.ident in aid]
    gone47 = [o.d() for o in b47 if o.ident not in aid]
    new_near = [o.d() for o in after if o.new and any(
        L in o.shp and sgap(o.shp[L], circ(p47.x, p47.y, 0.0)) < 1.0 for L in o.shp)]
    # island of U2-47 is the island of the L2 GND pour
    r47 = ufa.f(p47.id)
    pourroots = {ufa.f(('pour', 'L2-GND', int(i))) for i in pours_a['L2-GND']['live']}
    gnd_main = r47 in pourroots
    say('   12d U2-47 (%s, net %s, %.4f,%.4f): base GND copper touching it %d, alive %d, removed %d; new objects within '
        '1.0 mm: %d; on the L2-GND pour island: %s' % (side, p47.net, p47.x, p47.y, len(b47), len(alive47), len(gone47),
                                                       len(new_near), gnd_main))
    for d in alive47:
        say('       tie:', d)
    for d in new_near:
        say('       new near U2-47:', d)
    if p47.net != 'GND' or gone47 or not gnd_main or not b47:
        hard('u2-47', 'U2-47 tie changed: net %s removed %s main %s' % (p47.net, gone47, gnd_main))
    # whole-board GND: no base GND object removed by plan15 that the 13-R plan did not remove
    gnd_gone = [o.d() for o in base if o.net == 'GND' and o.kind != 'pad' and o.ident not in aid]
    gnd_new = [o.d() for o in after if o.net == 'GND' and o.new]
    say('       GND objects removed by plan15: %d %s; new GND objects: %d %s' % (len(gnd_gone), gnd_gone, len(gnd_new), gnd_new))
    X['u2_47'] = dict(tie=alive47, removed=gone47, main=gnd_main, gnd_removed=gnd_gone, gnd_new=gnd_new)

    # ------------------------------------------------------------------ 12e VIPPO list vs geometry
    smd = [o for o in after if o.kind == 'pad' and not o.multi]
    geo = collections.defaultdict(list)
    for v in after:
        if v.kind != 'via':
            continue
        for s in ('Top', 'Bottom'):
            if s not in v.shp:
                continue
            for p in smd:
                if p.layer != s or abs(p.x - v.x) > 1 or abs(p.y - v.y) > 1:
                    continue
                if sgap(circ(v.x, v.y, v.size / 2), p.shp[s]) < -1e-9:   # via LAND overlaps the pad
                    geo['%s-%s' % (p.comp, p.pad)].append(v)
    newgeo = {pp: vs for pp, vs in geo.items() if any(v.new for v in vs) or any(
        o.new for o in after if o.kind == 'pad' and '%s-%s' % (o.comp, o.pad) == pp)}
    basegeo = collections.defaultdict(list)
    bsmd = [o for o in base if o.kind == 'pad' and not o.multi]
    for v in base:
        if v.kind != 'via':
            continue
        for s in ('Top', 'Bottom'):
            if s not in v.shp:
                continue
            for p in bsmd:
                if p.layer == s and abs(p.x - v.x) < 1 and abs(p.y - v.y) < 1 and sgap(circ(v.x, v.y, v.size / 2), p.shp[s]) < -1e-9:
                    basegeo['%s-%s' % (p.comp, p.pad)].append(v)
    newgeo = {pp: vs for pp, vs in geo.items() if pp not in basegeo}
    listed = {e['pad']: e for e in PL.get('vippo', [])}
    say('   12e via-in-pad (land overlaps pad) sites new vs PcbDoc: %d %s; VIPPO list %d %s' % (
        len(newgeo), sorted(newgeo), len(listed), sorted(listed)))
    want6 = {'R128-1', 'R128-2', 'R131-1', 'R131-2', 'R133-1', 'R134-1'}
    if set(newgeo) != set(listed) or set(listed) != want6:
        hard('vippo-list', 'geometric sites %s vs list %s vs expected %s' % (sorted(newgeo), sorted(listed), sorted(want6)))
    # a via land that merely touches a pad (not centred) is a different DFM case
    for pp, vs in sorted(newgeo.items()):
        e = listed.get(pp)
        p = next(o for o in after if o.kind == 'pad' and '%s-%s' % (o.comp, o.pad) == pp)
        stack = [v for v in after if v.kind == 'via' and any(math.hypot(v.x - w.x, v.y - w.y) < 1e-4 for w in vs)]
        spans = sorted('%s>%s %.2f/%.2f' % (v.span[0], v.span[-1], v.size, v.hole) for v in stack)
        vs = stack
        lspans = sorted((e or {}).get('vias', []))
        # allow either span order naming in the list
        norm = lambda s: s.replace('Top Layer', 'Top').replace('Bottom Layer', 'Bottom')
        same = sorted(map(norm, lspans)) == sorted(map(norm, spans))
        cen = all(math.hypot(v.x - p.x, v.y - p.y) < 1e-3 for v in vs)
        nets = {v.net for v in vs} | {p.net}
        say('       %s pad net %s: vias %s | list %s | spans match %s, centred %s, nets %s, list xy (%.4f,%.4f) vs pad (%.4f,%.4f)' % (
            pp, p.net, spans, lspans, same, cen, sorted(nets), (e or {}).get('x', 0), (e or {}).get('y', 0), p.x, p.y))
        if not same or len(nets) != 1 or (e and e.get('net') != p.net):
            hard('vippo-list', '%s list entry does not match the vias (%s vs %s) or net mismatch %s' % (pp, lspans, spans, nets))
        if not cen:
            adv('vippo-offcentre', '%s via land not centred on the pad: %s' % (pp, [(v.x, v.y) for v in vs]))
        if e and (not near(e['x'], p.x, 2e-3) or not near(e['y'], p.y, 2e-3)):
            adv('vippo-xy', '%s list xy (%.4f,%.4f) is not the pad centre (%.4f,%.4f)' % (pp, e['x'], e['y'], p.x, p.y))
    X['vippo'] = sorted(newgeo)

    # ------------------------------------------------------------------ 12f microvia typing
    vias_nonthru = [v for v in PL.get('vias', []) if not (lname(v['from']) == 'Top' and lname(v['to']) == 'Bottom')]
    mv = PL.get('microvias', [])
    unmatched_v = [v for v in vias_nonthru if sum(
        1 for m in mv if near(m['x'], v['x'], 1e-6) and near(m['y'], v['y'], 1e-6) and m['net'] == v['net'] and
        {lname(m['from']), lname(m['to'])} == {lname(v['from']), lname(v['to'])} and near(m['size'], v['size'], 1e-6) and
        near(m['hole'], v['hole'], 1e-6)) != 1]
    unmatched_m = [m for m in mv if sum(
        1 for v in vias_nonthru if near(m['x'], v['x'], 1e-6) and near(m['y'], v['y'], 1e-6) and m['net'] == v['net'] and
        {lname(m['from']), lname(m['to'])} == {lname(v['from']), lname(v['to'])}) != 1]
    rename_nonthru = [v for v in PL.get('vias', []) if v.get('why') == 'rename' and v in vias_nonthru]
    types = collections.Counter(m['type'] for m in mv)
    wrongtype = []
    for m in mv:
        sp = (lname(m['from']), lname(m['to']))
        exp = 'buried' if set(sp) == {'L3-SIG', 'L4-SIG'} else 'microvia'
        if not m['type'].startswith(exp) or ('%.2f/%.2f' % (m['size'], m['hole'])) not in m['type']:
            wrongtype.append(m)
    say('   12f non-thru vias in plan %d, typing entries %d %s; unmatched vias %d, orphan entries %d, wrong type %d, '
        'renamed non-thru vias %d' % (len(vias_nonthru), len(mv), dict(types), len(unmatched_v), len(unmatched_m),
                                      len(wrongtype), len(rename_nonthru)))
    for v in unmatched_v:
        hard('via-typing', 'non-thru via not typed: %s' % k(v))
    for m in unmatched_m:
        hard('via-typing', 'orphan typing entry: %s' % k(m))
    for m in wrongtype:
        hard('via-typing', 'typing entry type/size mismatch: %s' % k(m))
    for v in rename_nonthru:
        adv('via-typing', 'renamed non-thru via relies on its existing PcbDoc type: %s' % k(v))

    # ------------------------------------------------------------------ 12g renamed counts
    rt = sum(1 for t in PL.get('tracks', []) if t.get('why') == 'rename')
    rr = sum(1 for t in PL.get('remove', []) if t.get('why') == 'rename')
    rv = sum(1 for t in PL.get('vias', []) if t.get('why') == 'rename')
    rrv = sum(1 for t in PL.get('remove_vias', []) if t.get('why') == 'rename')
    say('   12g renamed_existing %s; rename items: tracks %d (removes %d), vias %d (removes %d)' % (
        PL.get('renamed_existing'), rt, rr, rv, rrv))
    if PL.get('renamed_existing') != {'tracks': rt, 'vias': rv} or rt != rr or rv != rrv:
        adv('rename-count', 'renamed_existing %s vs items tracks %d/%d vias %d/%d' % (PL.get('renamed_existing'), rt, rr, rv, rrv))
    # every rename must keep geometry identical (only the net changes) and move Dn -> SDRAM-Dn
    rbad = []
    for key, rkey in (('tracks', 'remove'), ('vias', 'remove_vias')):
        rems = [r for r in PL.get(rkey, []) if r.get('why') == 'rename']
        for t in [t for t in PL.get(key, []) if t.get('why') == 'rename']:
            if key == 'tracks':
                m = [r for r in rems if lname(r['layer']) == lname(t['layer']) and near(r['w'], t['w'], 1e-6) and (
                    (near(r['x1'], t['x1']) and near(r['y1'], t['y1']) and near(r['x2'], t['x2']) and near(r['y2'], t['y2'])) or
                    (near(r['x1'], t['x2']) and near(r['y1'], t['y2']) and near(r['x2'], t['x1']) and near(r['y2'], t['y1'])))]
            else:
                m = [r for r in rems if near(r['x'], t['x']) and near(r['y'], t['y']) and near(r['hole'], t['hole'], 1e-6) and
                     lname(r['span'][0]) == lname(t['from']) and lname(r['span'][-1]) == lname(t['to'])]
            if len(m) != 1 or t['net'] != 'SDRAM-' + m[0]['net']:
                rbad.append((key, t, m))
    say('       rename items not geometry-identical Dn -> SDRAM-Dn: %d' % len(rbad))
    for r in rbad:
        hard('rename', '%s %s matches %s' % (r[0], k(r[1]), r[2]))
    # the renamed via sizes: the board's vias at those spots
    for t in [t for t in PL.get('vias', []) if t.get('why') == 'rename']:
        b = [o for o in base if o.kind == 'via' and near(o.x, t['x']) and near(o.y, t['y'])]
        if not b or any(not near(o.size, t['size'], 1e-6) for o in b):
            hard('rename', 'renamed via size differs from the PcbDoc: %s vs %s' % (k(t), [o.d() for o in b]))

    # ------------------------------------------------------------------ 12h NetAntennae, whole board
    def antennae(objs, pours):
        res = []
        byL = collections.defaultdict(list)
        for o in objs:
            for L, s in o.shp.items():
                byL[L].append(o)
        cell = 0.5
        grid = collections.defaultdict(list)
        for L, lst in byL.items():
            for o in lst:
                b = G['sbox'](o.shp[L])
                for i in range(int(b[0] / cell) - 1, int(b[2] / cell) + 2):
                    for j in range(int(b[1] / cell) - 1, int(b[3] / cell) + 2):
                        grid[(L, i, j)].append(o)

        def touched(x, y, L, o, net):
            for p in grid.get((L, int(x / cell), int(y / cell)), []):
                if p.id == o.id or p.net != net:
                    continue
                if G['point_in_shape'](x, y, p.shp[L], tol=1e-4):
                    return True
            if L in pours and POLYS[L]['net'] == net:
                pr = pours[L]
                i, j = int((x - pr['win'][0]) / pr['res']), int((y - pr['win'][1]) / pr['res'])
                if 0 <= j < pr['kept'].shape[0] and 0 <= i < pr['kept'].shape[1]:
                    return bool(pr['kept'][j, i] or pr['same'][j, i])
            return False

        for o in objs:
            if not o.net:
                continue
            if o.kind == 'track':
                t = o.src
                for (x, y) in ((t['x1'], t['y1']), (t['x2'], t['y2'])):
                    if not touched(x, y, o.layer, o, o.net):
                        res.append((('trk', o.layer, round(x, 4), round(y, 4)), '%s end (%.4f,%.4f)' % (o.d(), x, y)))
            elif o.kind == 'via':
                for L in (o.span[0], o.span[-1]):
                    if L in pours and POLYS[L]['net'] == o.net:
                        continue
                    hit = any(p.id != o.id and p.net == o.net and L in p.shp and sgap(p.shp[L], o.shp[L]) <= 1e-6
                              for p in grid.get((L, int(o.x / cell), int(o.y / cell)), []))
                    if not hit:
                        res.append((('via', round(o.x, 4), round(o.y, 4), o.span[0], o.span[-1], L), '%s nothing on %s' % (o.d(), L)))
        return res
    an_b = antennae(base, Lc['pours_b'])
    an_a = antennae(after, pours_a)
    kb = {r[0] for r in an_b}
    an_new = [r for r in an_a if r[0] not in kb]
    say('   12h NetAntennae (tol 0) whole board, keyed by geometry (net renames ignored): baseline %d (track ends %d, via '
        'span ends %d), after %d (track ends %d), NEW %d' % (len(an_b), sum(r[0][0] == 'trk' for r in an_b),
                                                           sum(r[0][0] == 'via' for r in an_b), len(an_a),
                                                           sum(r[0][0] == 'trk' for r in an_a), len(an_new)))
    for r in [r for r in an_b if r[0][0] == 'trk'][:6]:
        say('       baseline track end:', r[1])
    for r in an_b[:6]:
        say('       baseline:', r[1])
    for r in an_new:
        (hard if r[0][0] == 'trk' else adv)('net-antenna', r[1])
    X['antennae'] = dict(base=len(an_b), after=len(an_a), new=[r[1] for r in an_new])

    # ------------------------------------------------------------------ 12i U1 designator
    u1 = next(t for t in BX['texts'] if t['comp'] == 'U1' and t['designator'])
    say('   12i U1 designator "%s" at (%.4f,%.4f) h %.4f stroke %.4f hidden %s layer %s' % (
        u1['text'], u1['x'], u1['y'], u1['height'], u1['stroke'], u1['hidden'], u1['layer']))
    ops = Lc['ops_a']
    tb = [x for x in G['text_boxes']() if x[0] is u1]
    for (t, side, label, s) in tb:
        gaps = []
        for (o, s2, sh, e) in ops:
            if s2 != side or o.kind != 'pad':
                continue
            gaps.append((sgap(s, sh), o.d(), o.new))
        gaps.sort()
        newmin = min((g for g in gaps if g[2]), default=None)
        say('       %-12s box: min gap to any Top pad opening %.4f (%s); min to a NEW plan pad %.4f (%s); rule %.4f' % (
            label, gaps[0][0], gaps[0][1], newmin[0], newmin[1], G['SILK_MASK']))
        if gaps[0][0] < G['SILK_MASK'] - 1e-7:
            (hard if label == 'nominal' else adv)('silk-to-mask', 'U1 designator (%s) %.4f to %s' % (label, gaps[0][0], gaps[0][1]))
    # designator moves must be empty
    if PL.get('designator_moves'):
        hard('designator', 'designator_moves not empty: %s' % PL['designator_moves'])
    # every visible overlay text vs every NEW pad, nominal and conservative
    allnew = []
    for (t, side, label, s) in G['text_boxes']():
        for (o, s2, sh, e) in ops:
            if s2 == side and o.kind == 'pad' and o.new and G['box_gap'](G['sbox'](s), G['sbox'](sh)) < 1.0:
                allnew.append((round(sgap(s, sh), 4), label, t['text'], t['comp'], o.d()))
    allnew.sort()
    say('       visible overlay text vs NEW pad openings within 1 mm: %d; tightest %s' % (len(allnew), allnew[:4]))
    for g in allnew:
        if g[0] < G['SILK_MASK'] - 1e-7:
            (hard if g[1] == 'nominal' else adv)('silk-to-mask', 'text "%s" (%s, %s) %.4f to %s' % (g[2], g[3], g[1], g[0], g[4]))

    # ------------------------------------------------------------------ 12j ComponentClearance calibration
    CC = G['CCGAP']
    boxes = {}
    for c in BX['components']:
        ps = [p for p in BX['pads'] if p['ref'] == c['ref']]
        if not ps:
            continue
        sides = {c['side']} if all(p['layer'] != 'Multi' for p in ps) else {'Top', 'Bottom'}
        boxes[c['ref']] = (min(p['x'] - p['w'] / 2 for p in ps), min(p['y'] - p['h'] / 2 for p in ps),
                           max(p['x'] + p['w'] / 2 for p in ps), max(p['y'] + p['h'] / 2 for p in ps), sides,
                           c['footprint'])
    small = {r for r, b in boxes.items() if b[5] in ('R0201', 'C0201', 'R0402', 'C0402')}
    bp = []
    refs = sorted(small)
    for i, a in enumerate(refs):
        for b in refs[i + 1:]:
            A_, B_ = boxes[a], boxes[b]
            if not (A_[4] & B_[4]):
                continue
            g = G['box_gap'](A_[:4], B_[:4])
            if g < CC - 1e-6:
                bp.append((round(g, 4), a, b))
    bp.sort()
    say('   12j ComponentClearance calibration: existing 0201/0402 pairs with pad-box gap < %.3f on the DRC-0 board: %d; '
        'tightest %s' % (CC, len(bp), bp[:6]))
    X['cc_baseline'] = dict(n=len(bp), tightest=bp[:10])

    # ------------------------------------------------------------------ 12k board edge / hidden designators
    ol = BX['source']['board_outline']
    x0, y0 = min(p[0] for p in ol), min(p[1] for p in ol)
    x1, y1 = max(p[0] for p in ol), max(p[1] for p in ol)
    worst = 9
    for o in after:
        if not o.new:
            continue
        for L, s in o.shp.items():
            b = G['sbox'](s)
            worst = min(worst, b[0] - x0, b[1] - y0, x1 - b[2], y1 - b[3])
    say('   12k new copper min distance to the board edge %.3f mm; parts with designator not hidden: %s' % (
        worst, [p['ref'] for p in PL.get('parts', []) if not p.get('designator_hidden')]))
    if worst < 0.25:
        hard('edge', 'new copper %.3f mm from the board edge' % worst)
    if any(not p.get('designator_hidden') for p in PL.get('parts', [])):
        adv('designator', 'a new part has a visible designator not checked for silk placement')
    OUT['p15_extra'] = X
