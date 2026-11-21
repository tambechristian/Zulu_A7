from column2 import *
xs=[round(30.6+0.1*i,2) for i in range(70)]
res=[]
for x in xs:
    b=greedy(['LD0','LD1','LD2','LD3','LD4'],[x],9.8,20.2,1.6)
    if b: res.append((round(b[0],2),x,b[1]))
res.sort()
for r in res[:8]: print(r)
