"""Group an Altium Messages-panel export (tab separated) by message kind."""
import sys, re, collections
rows=[]
for l in open(sys.argv[1],encoding='utf-8',errors='replace'):
    m=re.match(r'\[(\w+)\]\t([^\t]*)\t([^\t]*)\t([^\t]*)',l.rstrip('\n'))
    if m: rows.append(m.groups())
print(len(rows),'messages;', collections.Counter(r[0] for r in rows))
kinds=[
 ('floating input', r'contains floating input pins'),
 ('unconnected pin', r'^Unconnected Pin'),
 ('no driving source', r'has no driving source'),
 ('IO pin with power pin', r'contains IO Pin and Power Pin'),
 ('IO pin with output pin', r'contains IO Pin and Output Pin'),
 ('output with output', r'contains Output Pin and Output Pin|Multiple Output'),
 ('duplicate designator', r'[Dd]uplicate'),
 ('net label floating', r'Floating Net Label|Net Label .* floating'),
 ('off grid', r'[Oo]ff grid'),
 ('unconnected wire/junction', r'Floating|floating wire|Unconnected line|Unconnected Junction'),
 ('cross reference', r'Cross References'),
 ('single node net', r'only one pin|single pin'),
]
groups=collections.defaultdict(list)
for cls,doc,src,msg in rows:
    for name,pat in kinds:
        if re.search(pat,msg): groups[(cls,name)].append((doc,msg)); break
    else: groups[(cls,'other')].append((doc,msg))
for (cls,name),items in sorted(groups.items(), key=lambda kv:(-len(kv[1]),kv[0])):
    docs=collections.Counter(d for d,_ in items)
    print(f'\n{cls:8} {name:26} {len(items):3}   sheets: {dict(docs)}')
    for d,m in items[:60 if name in ('other','floating input','IO pin with output pin','unconnected pin','cross reference') else 8]:
        print('     ',m[:150])
