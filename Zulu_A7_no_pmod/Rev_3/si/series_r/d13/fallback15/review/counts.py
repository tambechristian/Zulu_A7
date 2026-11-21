import json, collections, sys
B='C:/Users/tambe/Documents/Electronics/Zulu_A7/Zulu_A7_no_pmod/Rev_2/si/series_r/'
def stats(fn):
    p=json.load(open(B+fn))
    t=p['tracks']; v=p['vias']
    rt=sum(1 for x in t if x.get('why')=='rename'); rv=sum(1 for x in v if x.get('why')=='rename')
    print('==',fn)
    print(' remove',len(p['remove']),'remove_vias',len(p['remove_vias']),'tracks',len(t),'vias',len(v))
    print(' renames tracks',rt,'vias',rv,'renamed_existing',p.get('renamed_existing'))
    print(' net: tracks -%d/+%d vias -%d/+%d'%(len(p['remove'])-rt,len(t)-rt,len(p['remove_vias'])-rv,len(v)-rv))
    print(' microvias',len(p['microvias']),collections.Counter(m['type'] for m in p['microvias']))
    print(' vippo', 'vippo' in p,[x['pad'] for x in p.get('vippo',[])], [ (x['x'],x['y']) for x in p.get('vippo',[])])
    print(' parts',len(p['parts']),collections.Counter(x['side'] for x in p['parts']))
    print(' renet',[(x['ref'],x['pad'],x['net']) for x in p.get('renet_pads',[])])
    print(' nca', {k:len(v) for k,v in p.get('net_class_add',{}).items()})
    print(' why', collections.Counter(x.get('why') for x in t), collections.Counter(x.get('why') for x in v))
    nonthru=[x for x in v if not (x['from']=='Top Layer' and x['to']=='Bottom Layer')]
    print(' nonthrough new vias',len(nonthru), 'thru', len(v)-len(nonthru))
    return p
p=stats('dq_series_r_plan.json'); stats('dq_series_r_plan_13.json'); stats('dq_series_r_plan_16.json')
for x in p['parts']: print(x['ref'],x['net_bit'],x['side'],x['x'],x['y'],x['rot'],x['pad1'],x['pad2'])
print('designator_moves',p['designator_moves'])
# per-net
for n in ['D14','SDRAM-D14','D15','SDRAM-D15','D13','SDRAM-D13']:
    print('--',n)
    for x in p['remove']:
        if x['net']==n: print(' REM',x)
    for x in p['remove_vias']:
        if x['net']==n: print(' REMV',x)
    for x in p['tracks']:
        if x['net']==n: print(' ADD',x)
    for x in p['vias']:
        if x['net']==n: print(' ADDV',x)
nets=collections.Counter([x['net'] for x in p['remove']+p['tracks']+p['vias']+p['remove_vias'] if x.get('why')!='rename'])
print(nets)
