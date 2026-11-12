import sys, json, runpy
sys.argv = ['widthcheck.py', 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/Imported zulu_a7.PrjPcb/zulu_a7_fab_b.PcbDoc', 'C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/route/rev2/B/usb_hand_plan.json']
g = runpy.run_path('C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_Fab_B/Rev_2/tools/widthcheck.py')
for r in g['rules']:
    print(r['PRIORITY'], r['NAME'], r['SCOPE1EXPRESSION'], 'min', r['MINLIMIT'], {k: v for k, v in r.items() if k.endswith('_MINWIDTH')})
for n in ['VU','VBATT','USB5V0','VCC3V3','GND','USB_D_P','CHAN7','EE-CLK','N$BTN','FT-VCORE','VCC1V0']:
    r = next(r for r in g['rules'] if g['match'](r['SCOPE1EXPRESSION'], n))
    print(n, r['NAME'], {k: g['mil'](r.get(k+'_MINWIDTH', r['MINLIMIT'])) for k in g['LAYKEY'].values()})
