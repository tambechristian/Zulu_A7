"""Build the X2 label swap: names move to the pin-number row, numbers are deleted. Read-only on geom; writes edits."""
import json, sys
G = json.load(open(sys.argv[1])); out = sys.argv[2]; gnd21 = sys.argv[3] == 'gnd21'
T = [t for t in G['texts'] if t['kind'] == 'free' and t['layer'] == 33]
E = {'delete': [], 'set': {}}
near = lambda a, b: abs(a - b) < 1e-3
for t in T:
    s = t['text']; r = round(t['rot']) % 360
    if r == 0 and near(t['y'], 22.189) and s.isdigit(): E['delete'].append(t['idx'])           # top pin numbers
    elif r == 0 and near(t['y'], 2.411) and s.isdigit(): E['delete'].append(t['idx'])          # bottom pin numbers
    elif r == 0 and near(t['y'], 20.939): E['set'][t['idx']] = {'y': 22.189}                     # top names -> number row
    elif r == 0 and near(t['y'], 3.661): E['set'][t['idx']] = {'y': 2.411}                      # bottom names -> number row
    elif r == 90 and s == '2 CLK': E['set'][t['idx']] = {'text': 'CLK', 'y': round(t['y'] + 2 * t['h'], 4)}   # CLK stays put
    elif r == 90 and s == '30 C20': E['set'][t['idx']] = {'text': 'C20'}                         # C20 takes 30's place
    elif r == 90 and s == '21 GND': E['set'][t['idx']] = {'text': 'GND'}                         # GND takes 21's place
    elif r == 90 and s == '21': (E['set'].__setitem__(t['idx'], {'text': 'GND'}) if gnd21 else E['delete'].append(t['idx']))
json.dump(E, open(out, 'w'), indent=1)
names = {t['idx']: t['text'] for t in T}
print(out, 'delete', len(E['delete']), [names[i] for i in E['delete']])
print('set', {names[int(k)]: v for k, v in E['set'].items()})
