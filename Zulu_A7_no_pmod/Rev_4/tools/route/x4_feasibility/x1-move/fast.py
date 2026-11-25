from common import *
import common
def _pd(px,py,ax,ay,bx,by):
    vx,vy=bx-ax,by-ay; L=vx*vx+vy*vy
    t=0 if L==0 else max(0,min(1,((px-ax)*vx+(py-ay)*vy)/L))
    return math.hypot(px-ax-t*vx,py-ay-t*vy)
def _inter(p1,p2,q1,q2):
    def cr(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    d1,d2,d3,d4=cr(q1,q2,p1),cr(q1,q2,p2),cr(p1,p2,q1),cr(p1,p2,q2)
    return d1*d2<0 and d3*d4<0
def seg_box(x1,y1,x2,y2,b):
    def inb(x,y): return b[0]<=x<=b[2] and b[1]<=y<=b[3]
    if inb(x1,y1) or inb(x2,y2): return 0.0
    C=[(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]
    for i in range(4):
        if _inter((x1,y1),(x2,y2),C[i],C[(i+1)%4]): return 0.0
    d=min(_pd(cx,cy,x1,y1,x2,y2) for cx,cy in C)
    for x,y in ((x1,y1),(x2,y2)):
        dx=max(b[0]-x,0,x-b[2]); dy=max(b[1]-y,0,y-b[3]); d=min(d,math.hypot(dx,dy))
    return d
common.seg_box_dist=seg_box
