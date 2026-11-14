"""exact delta of ../final_plan.json against dq_series_r_plan.json -> delta_report.json (printed too)"""
import json, os, collections
import lib
B = lib.load_base()
F = json.load(open(os.path.join(lib.D13, 'final_plan.json')))
def k(o): return json.dumps(o, sort_keys=True)
rep = {}
for key in ('remove', 'remove_vias', 'tracks', 'vias', 'microvias', 'parts', 'renet_pads'):
    b = collections.Counter(k(o) for o in B[key]); f = collections.Counter(k(o) for o in F[key])
    assert not (b - f), ('base item missing in final', key)
    rep[key] = [json.loads(x) for x in (f - b).elements()]
rep['net_class_add'] = sorted(set(F['net_class_add']['SDRAM_DATA']) - set(B['net_class_add']['SDRAM_DATA']))
rep['emit_counts_final'] = {x: len(F[x]) for x in ('remove', 'tracks', 'remove_vias', 'vias', 'microvias', 'parts', 'renet_pads')}
rep['emit_counts_base'] = {x: len(B[x]) for x in ('remove', 'tracks', 'remove_vias', 'vias', 'microvias', 'parts', 'renet_pads')}
rep['renamed_existing'] = F['renamed_existing']
json.dump(rep, open(os.path.join(lib.HERE, 'delta_report.json'), 'w', newline='\n'), indent=1)
print('emit counts base', rep['emit_counts_base']); print('emit counts final', rep['emit_counts_final'], F['renamed_existing'])
for key in ('parts', 'renet_pads', 'remove', 'remove_vias', 'tracks', 'vias', 'microvias'):
    print('==', key, len(rep[key]))
    for o in rep[key]:
        if key == 'parts':
            print('  %s %s (%.4f,%.4f) rot %d pad1 %s (%.4f,%.4f) pad2 %s (%.4f,%.4f)' % (o['ref'], o['side'], o['x'], o['y'], o['rot'], o['pad1']['net'], o['pad1']['x'], o['pad1']['y'], o['pad2']['net'], o['pad2']['x'], o['pad2']['y']))
        elif key in ('remove', 'tracks'):
            print('  %-9s %-12s %-12s w%.4f (%.4f,%.4f)-(%.4f,%.4f) %s' % (o['net'], o['layer'], '', o['w'], o['x1'], o['y1'], o['x2'], o['y2'], o.get('why', '')))
        elif key in ('vias', 'microvias'):
            print('  %-9s (%.4f,%.4f) %s>%s %.2f/%.2f %s' % (o['net'], o['x'], o['y'], o['from'], o['to'], o['size'], o['hole'], o.get('why', o.get('type', ''))))
        else:
            print('  ', o)
print('net_class_add +', rep['net_class_add'])
