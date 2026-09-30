# -*- coding: utf-8 -*-
"""The via SPAN model (2026-09-29, HDI microvias): one reader for tools/hdi.json, shared by every gate.

A via occupies the layers in its span, outer to inner order on the Board6 stack
Top / L2-GND / L3-SIG / L4-SIG / L5-VCC3V3 / Bottom.  It blocks routing only on the SIGNAL layers
of its span, joins copper only on those layers, makes a plane anti-pad only on a plane layer that
is in its span and whose net is not its own, and may sit at the centre of a same-net SMD pad on its
outer layer when hdi.json allows via-in-pad for the span.  Two vias conflict only if their spans
share a layer; the pitch is the max of their spans' pitches (laser vs mechanical: the
laser_to_mechanical_pitch).  A via record without a 'span' key -- every plan written before
2026-09-29, every route_inputs.json before the span field -- is a through via.

    H = hdi.load(inp)            tools/hdi.json (an inputs dict carrying its own 'hdi' key -- a test
                                 model -- overrides it, with a note on stderr; route_inputs.py writes none)
    hdi.span_of(v)               tuple of layer names in STACK order, THROUGH when the record has none
    H.land(span) / H.hole(span) / H.pitch_between(a, b) / H.via_in_pad(span) / H.field_ban(span)
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'hdi.json')
STACK = ('Top', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom')
SIGNAL = ('Top', 'L3-SIG', 'L4-SIG', 'Bottom')
THROUGH = STACK
CLEARANCE = 0.09          # via land to via land, the clearance the through pitch derives from (0.44 = 0.35 + 0.09)
# the through via as every gate modelled it before hdi.json existed (JLC: hole 0.20, land 0.35, pitch 0.44)
THROUGH_PARAMS = dict(span=list(THROUGH), kind='mechanical', hole=0.20, land=0.35, pitch=0.44, via_in_pad=False, antipad=None)
BUILTIN = dict(stack=list(STACK), signal_layers=list(SIGNAL), plane_nets={'L2-GND': 'GND', 'L5-VCC3V3': 'VCC3V3'},
               spans=[THROUGH_PARAMS], laser_to_mechanical_pitch=0.44, disjoint_span_pitch=0.0, stacked_same_xy=False)


def span_of(v):
    """the via's span as a tuple in STACK order; a record without one is a through via"""
    s = v.get('span')
    return canonical(s) if s else THROUGH


def canonical(span):
    """the span as a tuple in STACK (Top-first) order: a list written inner-first, the natural
    'outer to inner' order of a Bottom-side via (Bottom, L5-VCC3V3), is turned round so plan files
    and hdi.json match in either order.  Anything else is returned as given, for is_allowed to refuse"""
    s = tuple(span)
    if len(s) > 1 and s[0] in STACK and s[-1] in STACK and STACK.index(s[0]) > STACK.index(s[-1]):
        s = s[::-1]
    return s


def is_through(span):
    return tuple(span) == THROUGH


def signal_layers(span):
    return tuple(L for L in SIGNAL if L in span)


def shares_layer(a, b):
    return bool(set(a) & set(b))


def adjacent(a, b):
    """two spans that meet end to end (a stack): the outer end of one is the inner end of the other"""
    return a[-1] == b[0] or b[-1] == a[0]


def span_between(lo, hi):
    """the span from layer name lo to layer name hi (either order), on the stack"""
    i, j = sorted((STACK.index(lo), STACK.index(hi)))
    return STACK[i:j + 1]


def _refuse(msg):
    raise SystemExit('tools/hdi.json: ' + msg)


def _check_span(s):
    """schema and physical floors for one hdi.json span entry; returns its canonical key.  A span
    must be contiguous on the stack (either order); its land must exceed its hole, its pitch must
    reach land + CLEARANCE (below that two lands overlap and no gate would see it), and an antipad,
    when given, must exceed the hole"""
    given = tuple(s['span'])
    if not given or any(L not in STACK for L in given):
        _refuse('span %s names a layer that is not on the stack %s' % ('/'.join(map(str, given)), '/'.join(STACK)))
    key = span_between(given[0], given[-1])
    if given not in (key, key[::-1]):
        _refuse('span %s is not contiguous on the stack (expected %s)' % ('/'.join(given), '/'.join(key)))
    name = '/'.join(key)
    hole, land, pitch = float(s['hole']), float(s['land']), float(s['pitch'])
    if land <= hole:
        _refuse('span %s: land %.3f must exceed the hole %.3f' % (name, land, hole))
    if pitch < land + CLEARANCE - 1e-9:
        _refuse('span %s: pitch %.3f is below land + %.2f = %.3f (two lands would overlap)' % (name, pitch, CLEARANCE, land + CLEARANCE))
    ap = s.get('antipad')
    if ap is not None and float(ap) <= hole:
        _refuse('span %s: antipad %.3f must exceed the hole %.3f' % (name, float(ap), hole))
    return key


class Hdi(object):
    def __init__(self, d):
        self.d = d
        self.spans = {}
        for s in d.get('spans', []):
            self.spans[_check_span(s)] = s
        self.plane_nets = dict(d.get('plane_nets', {}))          # plane layer -> net
        self.plane_of = {n: L for L, n in self.plane_nets.items()}   # net -> plane layer
        self.l2m = float(d.get('laser_to_mechanical_pitch', 0.44))
        self.disjoint = float(d.get('disjoint_span_pitch', 0.0))
        self.stacking = bool(d.get('stacked_same_xy', False))
        # the cross-kind pitch must keep two lands apart on every layer a laser span shares with a
        # mechanical one (same-kind pairs use the larger pitch, which its own floor already covers;
        # disjoint spans share no layer, so their lands never meet and disjoint_span_pitch has no floor)
        keys = list(self.spans)
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if shares_layer(a, b) and self.kind(a) != self.kind(b):
                    need = (self.land(a) + self.land(b)) / 2.0 + CLEARANCE
                    if self.l2m < need - 1e-9:
                        _refuse('laser_to_mechanical_pitch %.3f is below (%.3f + %.3f) / 2 + %.2f = %.3f for %s vs %s'
                                % (self.l2m, self.land(a), self.land(b), CLEARANCE, need, '/'.join(a), '/'.join(b)))

    def allowed(self):
        """the spans a plan may use, as tuples, in hdi.json order"""
        return list(self.spans)

    def is_allowed(self, span):
        return canonical(span) in self.spans

    def params(self, span):
        p = self.spans.get(canonical(span))
        if p is None:
            if is_through(span):
                return THROUGH_PARAMS
            raise SystemExit('tools/hdi.json does not list the via span %s' % '/'.join(span))
        return p

    def land(self, span):
        return float(self.params(span)['land'])

    def hole(self, span):
        return float(self.params(span)['hole'])

    def pitch(self, span):
        return float(self.params(span)['pitch'])

    def kind(self, span):
        return self.params(span).get('kind', 'mechanical')

    def via_in_pad(self, span):
        return bool(self.params(span).get('via_in_pad', False))

    def outer(self, span):
        """the outer (SMD pad) layers the span touches"""
        return tuple(L for L in (span[0], span[-1]) if L in ('Top', 'Bottom'))

    def field_ban(self, span):
        """is a via of this span banned inside U1's land field?  hdi.json's per-span 'land_field_ban'
        when it gives one; else yes unless the span is a via-in-pad span that stops above Bottom (the
        ban existed for through vias).  A buried span keeps the ban until hdi.json says otherwise:
        lifting it is a capacity decision, not a physics rule"""
        p = self.params(span)
        if p.get('land_field_ban') is not None:
            return bool(p['land_field_ban'])
        return 'Bottom' in span or not self.via_in_pad(span)

    def pitch_between(self, a, b):
        """required centre pitch between a via of span a and one of span b, or None when the spans
        share no layer and hdi.json puts no pitch on that case"""
        a, b = tuple(a), tuple(b)
        if not shares_layer(a, b):
            return self.disjoint if self.disjoint > 0 else None
        if self.kind(a) != self.kind(b):
            return self.l2m
        return max(self.pitch(a), self.pitch(b))

    def stacked(self, va, sa, vb, sb, eps=1e-6):
        """the two vias are one allowed stack: same net, one x,y, adjacent spans"""
        return (self.stacking and va.get('net') == vb.get('net') and adjacent(tuple(sa), tuple(sb)) and
                abs(va['x'] - vb['x']) < eps and abs(va['y'] - vb['y']) < eps)

    def antipad_r(self, span, hole, plane_clr):
        """radius of the plane void: hole/2 + PlaneClearance (the PcbDoc's one PlaneClearance rule
        voids every via that way), ENLARGED to hdi's 'antipad' diameter for the span when that is
        bigger.  'antipad' can only enlarge the void: a smaller value would model a void the PcbDoc
        does not cut, until a PlaneClearance rule scoped to that span exists on the board"""
        ap = self.params(span).get('antipad')
        r = hole / 2.0 + plane_clr
        return max(r, float(ap) / 2.0) if ap else r

    def punches(self, span, net, plane_layer, plane_net):
        """does a via of this span and net void the plane?  Only if it touches the plane layer at
        all (inside or at an end) and is not the plane's own net (its own net connects Direct)"""
        return plane_layer in span and net != plane_net

    def usable(self, layer, net):
        """the allowed spans a via on `layer` of `net` can use: it must touch the layer and either
        reach a second signal layer or land on that net's own plane"""
        out = []
        for S in self.allowed():
            if layer not in S:
                continue
            if len(signal_layers(S)) >= 2 or any(self.plane_nets.get(P) == net for P in S):
                out.append(S)
        return out


_FILE = {}


def _model(d):
    return {k: v for k, v in d.items() if k != '_comment'}


def load(inp=None):
    """the Hdi in force: tools/hdi.json, else the built-in through-only model.  An inputs dict that
    carries its own 'hdi' key (a test model -- route_inputs.py writes none, so a stale copy cannot
    shadow an edited hdi.json) overrides the file, and one line on stderr says so when they differ"""
    if 'H' not in _FILE:
        _FILE['H'] = Hdi(json.load(io.open(PATH, encoding='utf-8'))) if os.path.exists(PATH) else Hdi(BUILTIN)
    if inp is not None and inp.get('hdi'):
        if 'noted' not in _FILE and _model(inp['hdi']) != _model(_FILE['H'].d):
            _FILE['noted'] = True
            sys.stderr.write("hdi: the inputs file carries its own via-span model, which differs from tools/hdi.json"
                             " -- the inputs file's model is in force\n")
        return Hdi(inp['hdi'])
    return _FILE['H']


def default():
    return Hdi(BUILTIN)
