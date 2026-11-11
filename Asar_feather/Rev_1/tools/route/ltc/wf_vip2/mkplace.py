import json,sys
P=json.load(open('../wf_vip/placement_vip_final.json'))
P['C150']=['B',10.3,13.55,0]
P['C151']=['B',13.6,14.45,180]
P['L8']=['B',13.05,12.05,90]
P['C147']=['B',14.9,12.35,90]
if len(sys.argv)>2: P['C167']=['B',float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])]
json.dump(P,open(sys.argv[1],'w'),indent=1)
