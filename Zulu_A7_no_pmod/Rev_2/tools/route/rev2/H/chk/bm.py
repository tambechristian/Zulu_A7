"""build_model.py: H inputs from prep/ + the B USB hand plan (usb_hand_plan.json, regenerated with bump 28.75 h 0.195).
Writes rip_H.json (prep rip + the USB plan's CHAN10 removals), usb_fixed.json (USB + CHAN10 copper as a plan) and
model_H.json (prep/model.json - CHAN10 removals + USB/CHAN10 copper as FIXED model copper: the router cannot rip it)."""
import json
STACK = ['Top Layer', 'L2-GND', 'L3-SIG', 'L4-SIG', 'L5-VCC3V3', 'Bottom Layer']
P = '../../prep/'
rip = json.load(open(P + 'rip.json'))
M = json.load(open(P + 'model.json'))
U = json.load(open('usb_hand_plan.json'))
def tk(t): return (t['net'], t['layer'], round(t['x1'], 4), round(t['y1'], 4), round(t['x2'], 4), round(t['y2'], 4))
def vk(v):
    sp = v['span'] if 'span' in v else STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]
    return (v['net'], round(v['x'], 4), round(v['y'], 4), sp[0], sp[-1])
rt, rv = {tk(t) for t in U['remove']}, {vk(v) for v in U['remove_vias']}
n0t, n0v = len(M['tracks']), len(M['vias'])
M['tracks'] = [t for t in M['tracks'] if tk(t) not in rt] + U['tracks']
M['vias'] = [v for v in M['vias'] if vk(v) not in rv] + [dict(v, span=STACK[STACK.index(v['from']):STACK.index(v['to']) + 1]) for v in U['vias']]
print('model tracks %d -> %d, vias %d -> %d' % (n0t, len(M['tracks']), n0v, len(M['vias'])))
json.dump(M, open('model_H.json', 'w'))
json.dump({'remove': rip['remove'] + U['remove'], 'remove_vias': rip['remove_vias'] + U['remove_vias']}, open('rip_H.json', 'w'), indent=0)
json.dump({'tracks': U['tracks'], 'vias': U['vias'], 'remove': [], 'remove_vias': []}, open('usb_fixed.json', 'w'), indent=1)
