"""IBIS -> ngspice behavioural buffer (Zulu_a7_no_pmod Rev 2 SI cross-check).

Standard IBIS behavioural model, at the die node:
    I_into_pin = Ku(t) * Ipu(Vpu - V) + Kd(t) * Ipd(V) + Igc(V) + Ipc(Vpc - V) + C_comp * dV/dt
(IBIS tables: pull-up and POWER-clamp voltages are measured from their reference rail; currents are positive INTO the
pin; pull-up/pull-down tables exclude the clamp currents.)
Ku/Kd are extracted per edge from the two V-T waveforms with different fixtures (two equations, two unknowns at every
time point), with the fixture current corrected for clamps, C_comp and C_fixture. Without two usable waveforms the
[Ramp] (20-80 %) is used to make linear Ku/Kd. The package is R_pkg + L_pkg in series from the die to the pin, C_pkg at
the pin (per-pin values from [Pin] override [Package]).

Corner columns: 'typ', 'min', 'max' (IBIS min = slow/weak, max = fast/strong).
"""
import re
import numpy as np

COL = {'typ': 0, 'min': 1, 'max': 2}
_SCALE = {'T': 1e12, 'G': 1e9, 'M': 1e6, 'k': 1e3, 'K': 1e3, 'm': 1e-3, 'u': 1e-6, 'n': 1e-9, 'p': 1e-12, 'f': 1e-15}


def num(s):
    """IBIS number with optional scale letter and unit text ('4.39pF', '3.3V', '-1.2mA', 'NA')."""
    s = s.strip()
    if s.upper() == 'NA' or s == '':
        return None
    m = re.match(r'^([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)([TGMkKmunpf]?)', s)
    if not m:
        raise ValueError('bad IBIS number %r' % s)
    v = float(m.group(1))
    if m.group(2):
        v *= _SCALE[m.group(2)]
    return v


def _strip_comment(line):
    i = line.find('|')
    return line if i < 0 else line[:i]


class Model:
    def __init__(self, name):
        self.name = name
        self.kw = {}
        self.tables = {}          # key -> np.array (N, 4): x, typ, min, max
        self.waves = {'rise': [], 'fall': []}   # dicts: fixture params + table (N,4)
        self.ramp = {}


class Ibis:
    def __init__(self, path):
        self.path = path
        self.models = {}
        self.selectors = {}
        self.pins = {}            # pin -> (signal, model, R, L, C) per component (first component only)
        self.pkg = {}             # R_pkg/L_pkg/C_pkg -> (typ, min, max)
        self.pkg_model = {}       # pin -> (R, L, C): diagonals of [Define Package Model] matrices
        text = open(path, encoding='latin1').read()
        self._parse(text)
        self._parse_pkg_model(text)

    def _parse_pkg_model(self, text):
        """Diagonal R/L/C per pin from the first [Define Package Model] (banded/sparse/full: the diagonal is the
        first entry of each [Row], or the entry whose column pin equals the row pin)."""
        i0 = text.find('[Define Package Model]')
        if i0 < 0:
            return
        mat = row = None
        diag = {'r': {}, 'l': {}, 'c': {}}
        for l in text[i0:].splitlines():
            l = _strip_comment(l).strip()
            if not l:
                continue
            lo = l.lower()
            if lo.startswith('[resistance matrix]'):
                mat = 'r'; row = None; continue
            if lo.startswith('[inductance matrix]'):
                mat = 'l'; row = None; continue
            if lo.startswith('[capacitance matrix]'):
                mat = 'c'; row = None; continue
            if lo.startswith('[end model data]') or lo.startswith('[end package model]'):
                break
            if lo.startswith('[row]'):
                row = l.split()[1]; first = True; continue
            if l.startswith('[') or mat is None or row is None:
                continue
            t = l.split()
            if len(t) == 2 and t[0] == row:
                diag[mat][row] = num(t[1])
            elif row not in diag[mat] and len(t) >= 1 and (len(t) != 2 or not re.match(r'^[A-Z]+\d+$', t[0])):
                diag[mat][row] = num(t[0])
        for p in set(diag['r']) | set(diag['l']) | set(diag['c']):
            if p in diag['l'] and p in diag['c']:
                self.pkg_model[p] = (diag['r'].get(p, 0.0), diag['l'][p], diag['c'][p])

    def _parse(self, text):
        lines = [_strip_comment(l).rstrip() for l in text.splitlines()]
        kw = None
        model = None
        comp_done = False
        cur = None   # current table / waveform
        selector = None
        for raw in lines:
            if not raw.strip():
                continue
            m = re.match(r'^\[([^\]]+)\]\s*(.*)$', raw.strip())
            if m:
                kw = re.sub(r'[_\s]+', ' ', m.group(1).strip().lower())   # IBIS: '_' and ' ' are equivalent
                arg = m.group(2).strip()
                cur = None
                selector = None
                if kw == 'component':
                    if self.pins:
                        comp_done = True
                elif kw == 'model':
                    model = Model(arg.split()[0])
                    self.models[model.name] = model
                elif kw == 'model selector':
                    selector = arg.split()[0]
                    self.selectors[selector] = []
                elif kw in ('pulldown', 'pullup', 'gnd clamp', 'power clamp') and model is not None:
                    cur = model.tables.setdefault(kw, [])
                elif kw in ('rising waveform', 'falling waveform') and model is not None:
                    cur = {'rows': []}
                    model.waves['rise' if kw.startswith('rising') else 'fall'].append(cur)
                elif kw == 'ramp' and model is not None:
                    cur = model.ramp
                elif kw in ('voltage range', 'pullup reference', 'pulldown reference', 'power clamp reference',
                            'gnd clamp reference', 'temperature range') and model is not None and arg:
                    model.kw[kw] = [num(x) for x in arg.split()[:3]]
                continue
            toks = raw.split()
            if kw == 'package' and toks[0].lower() in ('r_pkg', 'l_pkg', 'c_pkg') and not comp_done:
                self.pkg[toks[0].lower()] = tuple(num(x) for x in toks[1:4])
            elif kw == 'pin' and not comp_done:
                if toks[0].lower() == 'signal_name' or len(toks) < 3:
                    continue
                rlc = [num(x) for x in toks[3:6]] if len(toks) >= 6 else [None, None, None]
                self.pins[toks[0]] = (toks[1], toks[2], *rlc)
            elif kw == 'model selector' and selector is not None:
                self.selectors[selector].append(toks[0])
            elif kw == 'model' and model is not None:
                k = toks[0].lower()
                if k == 'model_type':
                    model.kw['model_type'] = toks[1].lower()
                elif k == 'c_comp':
                    model.kw['c_comp'] = [num(x) for x in toks[1:4]]
                elif k in ('vinl', 'vinh', 'vmeas', 'vref', 'rref', 'cref'):
                    model.kw[k] = num(raw.split('=', 1)[1].split()[0]) if '=' in raw else num(toks[1])
                elif '=' in raw:
                    for a, b in re.findall(r'(\w+)\s*=\s*(\S+)', raw):
                        model.kw[a.lower()] = num(b)
            elif kw in ('pulldown', 'pullup', 'gnd clamp', 'power clamp') and cur is not None:
                vals = [num(x) for x in toks[:4]]
                cur.append(vals)
            elif kw in ('rising waveform', 'falling waveform') and cur is not None:
                if '=' in raw:
                    for a, b in re.findall(r'(\w+)\s*=\s*(\S+)', raw):
                        cur[a.lower()] = num(b)
                else:
                    cur['rows'].append([num(x) for x in toks[:4]])
            elif kw == 'ramp' and cur is not None:
                if toks[0].lower() in ('dv/dt_r', 'dv/dt_f'):
                    vals = []
                    for x in toks[1:4]:
                        if x.upper() == 'NA':
                            vals.append(None)
                        else:
                            a, b = x.split('/')
                            vals.append((num(a), num(b)))
                    cur[toks[0].lower()] = vals
                elif '=' in raw:
                    for a, b in re.findall(r'(\w+)\s*=\s*(\S+)', raw):
                        cur[a.lower()] = num(b)
        for mdl in self.models.values():
            for k, rows in list(mdl.tables.items()):
                a = np.array([[np.nan if v is None else v for v in r] for r in rows], float)
                # NA min/max -> typ
                for c in (2, 3):
                    bad = np.isnan(a[:, c])
                    a[bad, c] = a[bad, 1]
                mdl.tables[k] = a[np.argsort(a[:, 0])]
            for edge in ('rise', 'fall'):
                for w in mdl.waves[edge]:
                    a = np.array([[np.nan if v is None else v for v in r] for r in w['rows']], float)
                    for c in (2, 3):
                        bad = np.isnan(a[:, c])
                        a[bad, c] = a[bad, 1]
                    w['t'] = a

    def model(self, name):
        """Resolve a [Model Selector] to its first (default) model."""
        if name in self.models:
            return self.models[name]
        if name in self.selectors:
            return self.models[self.selectors[name][0]]
        for k in self.models:
            if k.lower() == name.lower():
                return self.models[k]
        raise KeyError(name)


def _rails(m, corner):
    c = COL[corner]
    vr = m.kw.get('voltage range')
    pu = m.kw.get('pullup reference', vr)
    pd = m.kw.get('pulldown reference', [0.0, 0.0, 0.0])
    pc = m.kw.get('power clamp reference', vr)
    gc = m.kw.get('gnd clamp reference', [0.0, 0.0, 0.0])
    pick = lambda v: v[c] if v[c] is not None else v[0]
    return pick(pu), pick(pd), pick(pc), pick(gc)


def _table(m, key, corner):
    a = m.tables.get(key)
    if a is None or len(a) == 0:
        return None
    return a[:, 0], a[:, 1 + COL[corner]]


def _interp(tab, x):
    if tab is None:
        return np.zeros_like(np.asarray(x, float))
    return np.interp(x, tab[0], tab[1])


def switching(m, corner, edge, dt=2e-12):
    """(t, Ku, Kd) for one edge of an output/I-O model. Ku: pull-up weight, Kd: pull-down weight."""
    vpu, vpd, vpc, vgc = _rails(m, corner)
    pu, pd = _table(m, 'pullup', corner), _table(m, 'pulldown', corner)
    gcl, pcl = _table(m, 'gnd clamp', corner), _table(m, 'power clamp', corner)
    ccomp = m.kw['c_comp'][COL[corner]] if m.kw.get('c_comp') and m.kw['c_comp'][COL[corner]] is not None else m.kw['c_comp'][0]
    waves = [w for w in m.waves[edge] if 't' in w and len(w['t']) > 3]
    # two fixtures with different V_fixture
    use = []
    for w in waves:
        vf = w.get('v_fixture')
        vfc = w.get('v_fixture_' + corner, vf) if corner != 'typ' else vf
        if vfc is None:
            vfc = vf
        use.append((w, vfc))
    use.sort(key=lambda p: p[1])
    if len(use) >= 2 and abs(use[0][1] - use[-1][1]) > 0.5:
        (w1, vf1), (w2, vf2) = use[0], use[-1]
        T = max(w1['t'][-1, 0], w2['t'][-1, 0])
        t = np.arange(0, T + dt, dt)
        V1 = np.interp(t, w1['t'][:, 0], w1['t'][:, 1 + COL[corner]])
        V2 = np.interp(t, w2['t'][:, 0], w2['t'][:, 1 + COL[corner]])
        rows = []
        for V, w, vf in ((V1, w1, vf1), (V2, w2, vf2)):
            R = w.get('r_fixture', 50.0)
            cf = w.get('c_fixture', 0.0) or 0.0
            dV = np.gradient(V, t)
            # current into the pin from the fixture network, minus clamp and C_comp currents
            I = (vf - V) / R - cf * dV - _interp(gcl, V - vgc) - _interp(pcl, vpc - V) - ccomp * dV
            rows.append((_interp(pu, vpu - V), _interp(pd, V - vpd), I))
        (a1, b1, i1), (a2, b2, i2) = rows
        det = a1 * b2 - a2 * b1
        ok = np.abs(det) > 1e-12 * (np.abs(a1 * b2) + np.abs(a2 * b1) + 1e-30)
        Ku = np.where(ok, (i1 * b2 - i2 * b1) / np.where(ok, det, 1), np.nan)
        Kd = np.where(ok, (a1 * i2 - a2 * i1) / np.where(ok, det, 1), np.nan)
        for K in (Ku, Kd):
            bad = np.isnan(K)
            if bad.any():
                K[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), K[~bad])
        # pin the end states exactly
        if edge == 'rise':
            Ku[0], Kd[0] = 0.0, 1.0
        else:
            Ku[0], Kd[0] = 1.0, 0.0
        src = 'waveforms (V_fixture %.2f / %.2f)' % (vf1, vf2)
    else:
        r = m.ramp.get('dv/dt_r' if edge == 'rise' else 'dv/dt_f')
        dv, tt = r[COL[corner]] if r[COL[corner]] is not None else r[0]
        trise = tt / 0.6
        t = np.arange(0, 2 * trise + dt, dt)
        s = np.clip(t / trise, 0, 1)
        Ku, Kd = (s, 1 - s) if edge == 'rise' else (1 - s, s)
        src = 'ramp'
    if Ku.min() < -0.1 or Ku.max() > 1.1 or Kd.min() < -0.1 or Kd.max() > 1.1:
        src += ' [WARNING Ku %.2f..%.2f Kd %.2f..%.2f outside 0..1: V-T tables inconsistent with C_comp]' % (
            Ku.min(), Ku.max(), Kd.min(), Kd.max())
    return t, Ku, Kd, src


def _pwl_expr(var, tab, scale=1.0):
    """ngspice B-source pwl() of a table, x ascending; thinned to <= 60 points."""
    x, y = tab
    if len(x) > 60:
        keep = np.unique(np.round(np.linspace(0, len(x) - 1, 60)).astype(int))
        x, y = x[keep], y[keep]
    return 'pwl(%s, %s)' % (var, ', '.join('%.6g, %.6g' % (a, b * scale) for a, b in zip(x, y)))


def buffer_netlist(name, m, corner, die, pin, pkg_rlc, ku=None, kd=None, rail=None):
    """SPICE lines for one buffer instance: behavioural die current, C_comp, package to 'pin'. ku/kd: node names
    carrying the switching weights (None = receiver: pull-up/pull-down off)."""
    vpu, vpd, vpc, vgc = _rails(m, corner)
    if rail is not None:          # one board rail for every buffer (both parts sit on VCC3V3)
        vpu, vpc, vpd, vgc = rail, rail, 0.0, 0.0
    c = COL[corner]
    ccomp = m.kw['c_comp'][c] if m.kw['c_comp'][c] is not None else m.kw['c_comp'][0]
    terms = []
    gcl, pcl = _table(m, 'gnd clamp', corner), _table(m, 'power clamp', corner)
    if gcl is not None:
        terms.append(_pwl_expr('V(%s)-%g' % (die, vgc), gcl))
    if pcl is not None:
        terms.append(_pwl_expr('%g-V(%s)' % (vpc, die), pcl))
    if ku is not None:
        terms.append('V(%s)*%s' % (ku, _pwl_expr('%g-V(%s)' % (vpu, die), _table(m, 'pullup', corner))))
        terms.append('V(%s)*%s' % (kd, _pwl_expr('V(%s)-%g' % (die, vpd), _table(m, 'pulldown', corner))))
    expr = ' + '.join(terms) if terms else '0'
    R, L, C = pkg_rlc
    out = ['* buffer %s model %s corner %s' % (name, m.name, corner),
           'B%s %s 0 I = %s' % (name, die, expr),
           'Cc%s %s 0 %g' % (name, die, ccomp),
           'Rp%s %s %s_pk %g' % (name, die, name, max(R, 1e-4)),
           'Lp%s %s_pk %s %g' % (name, name, pin, L),
           'Cp%s %s 0 %g' % (name, pin, C)]
    # wrap long lines for ngspice (continuation '+')
    wrapped = []
    for l in out:
        while len(l) > 900:
            cut = l.rfind(', ', 0, 900) + 1
            wrapped.append(l[:cut])
            l = '+' + l[cut:]
        wrapped.append(l)
    return wrapped, (vpu, ccomp)


def pkg_for(ib, pin, corner):
    """Package R/L/C for one pin: [Pin] R/L/C columns first, then the [Define Package Model] diagonal, then the
    [Package] typical value (its min/max columns are a pin-to-pin spread, not process corners)."""
    p = ib.pins.get(pin)
    if p and p[2] is not None and p[3] is not None and p[4] is not None:
        return p[2], p[3], p[4]
    if pin in ib.pkg_model:
        return ib.pkg_model[pin]
    pk = ib.pkg
    return pk['r_pkg'][0], pk['l_pkg'][0], pk['c_pkg'][0]


def weights_pwl(m, corner, edges, t_end, dt=5e-12):
    """PWL point lists (t, Ku), (t, Kd) for a sequence of edges [(time, 'rise'|'fall'), ...] starting low."""
    tr = switching(m, corner, 'rise')
    tf = switching(m, corner, 'fall')
    t = np.arange(0, t_end + dt, dt)
    ku = np.zeros_like(t)
    kd = np.ones_like(t)
    for te, kind in edges:
        tt, KU, KD, _ = tr if kind == 'rise' else tf
        sel = t >= te
        ku[sel] = np.interp(t[sel] - te, tt, KU)
        kd[sel] = np.interp(t[sel] - te, tt, KD)
    # thin: keep points where either weight changes
    keep = np.ones_like(t, bool)
    keep[1:-1] = (np.abs(np.diff(ku, 2)) > 1e-5) | (np.abs(np.diff(kd, 2)) > 1e-5)
    keep[np.flatnonzero(keep) ] = True
    idx = np.flatnonzero(keep)
    return t[idx], ku[idx], kd[idx]
