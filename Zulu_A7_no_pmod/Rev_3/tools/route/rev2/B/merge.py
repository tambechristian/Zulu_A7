"""merge.py <route_plan.json> <out_rip.json> <out_route.json>
rip_B = prep/rip.json + the hand USB plan's CHAN10 removals; route_B = hand USB copper + router copper."""
import json
import sys

rip = json.load(open('../prep/rip.json'))
usb = json.load(open('usb_hand_plan.json'))
rp = json.load(open(sys.argv[1]))
rip['remove'] = rip['remove'] + usb['remove']
rip['remove_vias'] = rip['remove_vias'] + usb['remove_vias']
json.dump(rip, open(sys.argv[2], 'w'), indent=1)
json.dump({'tracks': usb['tracks'] + rp['tracks'], 'vias': usb['vias'] + rp['vias'], 'remove': [], 'remove_vias': [],
           'log': rp.get('log', [])}, open(sys.argv[3], 'w'), indent=1)
