"""planeweb_b.py <out.json> <name=model.json> ...  -- route/rev2/judge/planeweb.run on each model (L2-GND / L5-VCC3V3
pour components, plane-net vias / drilled pads off the main pour, raw and after a 0.125 mm opening)."""
import json
import sys

JUDGE = 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/judge'
sys.path.insert(0, JUDGE)
import judge as J  # noqa: E402
import planeweb as PW  # noqa: E402


def main():
    out = {}
    for arg in sys.argv[2:]:
        name, path = arg.split('=', 1)
        M = json.load(open(path))
        for v in M['vias']:
            v['span'] = J.span(v)
        out[name] = PW.run(M, name)
        for layer, res in out[name].items():
            for mode, r in res.items():
                print(name, layer, mode, 'comps', r['components'], 'comps w/ net objs', r['components_with_net_objects'],
                      'main mm2', r['main_area_mm2'], 'objs', r['objects'], 'off-main', len(r['objects_off_main']),
                      r['objects_off_main'][:12], flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
