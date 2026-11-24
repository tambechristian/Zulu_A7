"""Final silk edit per board = swap + GND horizontal at pin 21 + title lowered + U1/U4 designators. Writes edits json."""
import json, sys
G = json.load(open(sys.argv[1])); swap = json.load(open(sys.argv[2])); out = sys.argv[3]
E = {'delete': list(swap['delete']), 'set': dict(swap['set'])}
T = G['texts']
def one(pred, what):
    h = [t for t in T if pred(t)]
    assert len(h) == 1, (what, len(h)); return h[0]
p21 = one(lambda t: t['layer'] == 33 and t['kind'] == 'free' and t['text'] in ('21', '21 GND'), 'pin21')
E['delete'] = [i for i in E['delete'] if i != p21['idx']]
# Fab B: vertical '21 GND' -> vertical 'GND' in place (horizontal would hit JP4-1's mask);
# Rev 3: vertical 'GND' would hit X5-MP1's mask (why Rev 3 printed only '21'), so GND goes horizontal in the name row
E['set'][str(p21['idx'])] = {'text': 'GND'} if p21['text'] == '21 GND' else {'text': 'GND', 'rot': 0, 'x': 58.45, 'y': 2.411}
title = one(lambda t: t['layer'] == 33 and t['kind'] == 'free' and t['text'].startswith('ZULU A7 '), 'title')
E['set'][str(title['idx'])] = {'y': 3.77}
u1 = one(lambda t: t['layer'] == 33 and t['kind'] == 'designator' and t['ref'] == 'U1', 'U1')
E['set'][str(u1['idx'])] = {'x': 45.867, 'y': 5.63}
u4 = one(lambda t: t['layer'] == 33 and t['kind'] == 'designator' and t['ref'] == 'U4', 'U4')
E['set'][str(u4['idx'])] = {'x': 52.6, 'y': 19.4, 'shown': True}
json.dump(E, open(out, 'w'), indent=1)
print(out, 'title', title['text'], 'idx', title['idx'], 'U1 idx', u1['idx'], 'U4 idx', u4['idx'], 'pin21', p21['text'])
