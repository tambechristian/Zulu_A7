"""Minimal S-expression reader for KiCad netlists (used to read the proven Zulu A7 netlist)."""
import re

_TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


class Str(str):
    """A quoted string, kept apart from bare atoms."""


def parse(text):
    stack, cur = [], []
    pos, n = 0, len(text)
    while pos < n:
        m = _TOK.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(Str(re.sub(r'\\(.)', r'\1', m.group(3))))
        else:
            cur.append(m.group(4))
    return cur[0] if len(cur) == 1 else cur


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    r = find(node, key)
    return r[0] if r else None


def netlist(path):
    """Return {net name: [(ref, pin), ...]} from a kicad-cli netlist."""
    root = parse(open(path, encoding='utf-8').read())
    out = {}
    for net in find(first(root, 'nets'), 'net'):
        out[first(net, 'name')[1]] = [(first(nd, 'ref')[1], first(nd, 'pin')[1]) for nd in find(net, 'node')]
    return out


def components(path):
    """Return {ref: {'value', 'footprint'}} from a kicad-cli netlist."""
    root = parse(open(path, encoding='utf-8').read())
    out = {}
    for c in find(first(root, 'components'), 'comp'):
        fp = first(c, 'footprint')
        out[first(c, 'ref')[1]] = {'value': first(c, 'value')[1], 'footprint': fp[1] if fp else ''}
    return out
