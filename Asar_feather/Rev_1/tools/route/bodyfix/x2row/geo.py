"""Shared geometry helpers for the x2row fix (scratch only)."""
import json
import math
import os
import sys

REV = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Asar_feather/Rev_1'
sys.path.insert(0, REV + '/tools')
import route_conn as C  # noqa: E402

MODEL = REV + '/tools/route/body_gate/model.json'
ROW = ['C40', 'C41', 'C152', 'C153', 'C154', 'R19', 'C155', 'C156', 'C157', 'C158', 'C159', 'C38']
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
AB = {'Top Layer': 'T', 'L2-GND': '2', 'L3-SIG': '3', 'L4-SIG': '4', 'L5-VCC3V3': '5', 'Bottom Layer': 'B'}


def load():
    return json.load(open(MODEL))


def players(p):
    return p['layers'] or (STACK if p['drill'] > 0 else [])


def items_on(M, layer):
    for p in M['pads']:
        if layer in players(p):
            yield 'p', p
    for t in M['tracks']:
        if t['layer'] == layer:
            yield 't', t
    for v in M['vias']:
        if layer in v['span']:
            yield 'v', v


def pad_gap(p, k, o):
    """copper gap between pad p (rect) and an item"""
    if k == 'p':
        if C.pad_round(o):
            return C.pad_point(p, o['x'], o['y']) - min(o['w'], o['h']) / 2
        dx = max(abs(p['x'] - o['x']) - (p['w'] + o['w']) / 2, 0)
        dy = max(abs(p['y'] - o['y']) - (p['h'] + o['h']) / 2, 0)
        g = math.hypot(dx, dy)
        if g == 0:
            g = -min((p['w'] + o['w']) / 2 - abs(p['x'] - o['x']), (p['h'] + o['h']) / 2 - abs(p['y'] - o['y']))
        return g
    if k == 't':
        return C.pad_seg(p, (o['x1'], o['y1'], o['x2'], o['y2'])) - o['w'] / 2
    return C.pad_point(p, o['x'], o['y']) - o['size'] / 2


def desc(k, o):
    if k == 'p':
        return 'pad %s-%s %s' % (o['ref'], o['pad'], o['net'])
    if k == 't':
        return 'trk %s %s w%.3f (%.3f,%.3f)-(%.3f,%.3f)' % (o['net'], AB[o['layer']], o['w'], o['x1'], o['y1'], o['x2'], o['y2'])
    return 'via %s %s %.2f/%.2f @(%.3f,%.3f)' % (o['net'], ''.join(AB[l] for l in o['span']), o['size'], o['hole'], o['x'], o['y'])
