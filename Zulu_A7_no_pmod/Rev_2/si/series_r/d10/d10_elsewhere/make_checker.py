"""Builds dfm_check_d10.py from dfm_base.py (a byte copy of si/series_r/dfm_check.py with HERE pointed at
si/series_r) by text substitution, so the diff to the proven checker is small and auditable."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(HERE, 'dfm_base.py')).read()
BS = chr(92)


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)


rep('"""Adversarial DFM / DRC review of the CHOSEN series-R plan', '''"""dfm_check_d10.py -- COPY of si/series_r/dfm_check.py adapted (d10_elsewhere) to read an implementation plan in
dq_series_r_plan.json format (emit_copper remove/remove_vias/tracks/vias + parts/renet_pads), so the FILE itself is
what gets proven.  Only load_plan_json(), the argument handling and the output names are new; every check is
dfm_check.py's code unchanged (built by make_checker.py from dfm_base.py).

    python dfm_check_d10.py --plan plan.json --tag d10      -> dfm_check_d10_<tag>.json/.log (this folder)
    python dfm_check_d10.py --plan ../../dq_series_r_plan.json --tag base12   (calibration: must equal FIXED)

ORIGINAL DOCSTRING:
Adversarial DFM / DRC review of the CHOSEN series-R plan''')
rep("VARIANT = 'FINAL'\nif '--variant' in sys.argv:\n    VARIANT = sys.argv[sys.argv.index('--variant') + 1]",
    "VARIANT = 'PLANFILE'\nOUTDIR = os.path.dirname(os.path.abspath(__file__))\n"
    "PLANFILE = sys.argv[sys.argv.index('--plan') + 1] if '--plan' in sys.argv else os.path.join(OUTDIR, 'plan.json')\n"
    "TAG = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'd10'")
loader = '''

EMIT2CU = {'Top Layer': 'Top', 'Bottom Layer': 'Bottom', 'L2-GND': 'L2-GND', 'L3-SIG': 'L3-SIG', 'L4-SIG': 'L4-SIG',
           'L5-VCC3V3': 'L5-VCC3V3', 'Top': 'Top', 'Bottom': 'Bottom'}


def _span(a, b):
    i, j = CU.index(EMIT2CU[a]), CU.index(EMIT2CU[b])
    return CU[min(i, j):max(i, j) + 1]


def load_plan_json(path):
    """dq_series_r_plan.json format -> this checker's edit list.  Renames are remove + re-add in the file; apply()
    reproduces that exactly (removal matched by layer, net and ends; the re-add carries the new net)."""
    P = json.load(open(path))
    E = dict(rm_t=[], add_t=[], rm_v=[], add_v=[], renet=[], add_p=[], parts={}, designer_renames=collections.defaultdict(list))
    for t in P['remove']:
        E['rm_t'].append(dict(layer=EMIT2CU[t['layer']], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['w']))
    for v in P['remove_vias']:
        E['rm_v'].append(dict(net=v['net'], x=v['x'], y=v['y'], span=_span(v['span'][0], v['span'][-1])))
    for t in P['tracks']:
        E['add_t'].append(dict(layer=EMIT2CU[t['layer']], net=t['net'], x1=t['x1'], y1=t['y1'], x2=t['x2'], y2=t['y2'], w=t['w']))
    for v in P['vias']:
        sp = _span(v['from'], v['to'])
        E['add_v'].append(dict(net=v['net'], x=v['x'], y=v['y'], size=v['size'], hole=v['hole'], span=sp,
                               kind='through' if len(sp) == 6 else 'micro'))
    E['renet'] = [dict(r) for r in P['renet_pads']]
    for pr in P['parts']:
        for k in ('1', '2'):
            pd = pr['pad' + k]
            E['add_p'].append(dict(ref=pr['ref'], pad=k, layer=pr['side'], net=pd['net'], x=pd['x'], y=pd['y'], w=0.3, h=0.3,
                                   shape='rect', hole=0.0))
        E['parts'][pr['net_bit']] = dict(ref=pr['ref'], side=pr['side'], x=pr['x'], y=pr['y'], rot=pr['rot'])
    return E, P
'''
rep("\n\nFIXES = {}   # filled by --variant FIXED", loader + "\n\nFIXES = {}   # filled by --variant FIXED")
rep("""    E = load_plan()
    if VARIANT == 'FIXED':
        E = apply_fixes(E)
    out = dict(variant=VARIANT, source=B['source']['pcbdoc_md5'], fixes_applied=FIXES)""",
    """    E, PJ = load_plan_json(PLANFILE)
    out = dict(variant=VARIANT, plan=os.path.abspath(PLANFILE).replace(chr(92), '/'), source=B['source']['pcbdoc_md5'],
               plan_source=PJ.get('source'), fixes_applied=FIXES)""")
rep("""    log('==== dfm_check.py variant %s  (PcbDoc md5 %s) ====' % (VARIANT, B['source']['pcbdoc_md5']))""",
    """    log('==== dfm_check_d10.py plan %s  (PcbDoc md5 %s) ====' % (os.path.abspath(PLANFILE).replace(chr(92), '/'), B['source']['pcbdoc_md5']))""")
rep("""    json.dump(out, open(os.path.join(HERE, 'dfm_check%s.json' % ('' if VARIANT == 'FINAL' else '_' + VARIANT.lower())), 'w'), indent=1, default=str)
    open(os.path.join(HERE, 'dfm_check%s.log' % ('' if VARIANT == 'FINAL' else '_' + VARIANT.lower())), 'w').write('""" + BS + """n'.join(LOG) + '""" + BS + """n')""",
    """    json.dump(out, open(os.path.join(OUTDIR, 'dfm_check_d10_%s.json' % TAG), 'w'), indent=1, default=str)
    open(os.path.join(OUTDIR, 'dfm_check_d10_%s.log' % TAG), 'w').write('""" + BS + """n'.join(LOG) + '""" + BS + """n')""")
open(os.path.join(HERE, 'dfm_check_d10.py'), 'w', newline='\n').write(s)
print('dfm_check_d10.py written')
