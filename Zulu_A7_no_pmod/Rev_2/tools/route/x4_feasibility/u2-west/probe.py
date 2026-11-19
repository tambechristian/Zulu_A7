import geo,sys
RELOC={'BTN','LD0','LD1','LD2','LD3','LD4','C155','C158','C159'}
ux,uy,cx,rot=map(float,sys.argv[1:5])
M,D=geo.build({'U2':(ux,uy,rot)},s2b=(cx,4.9))
M['pads']=[p for p in M['pads'] if p['ref'] not in RELOC]
f=[r for r in geo.body_findings(M,D,{'U2','X4'})]
print('body:',sorted(set(f)))
print('pads:',geo.pad_checks(M,{'U2','X4'}))
