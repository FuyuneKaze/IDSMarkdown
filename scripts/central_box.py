from glyph_extend import return_bone
from stroke_outer import (Point, Bbox, prt_point_in_list, stroke_point,
                          strokic_boundary, bone_shape_function)
import numpy as np
class Segment:
    def __init__(self, P1=Point(0, 0), P2=Point(0, 0)):
        self.P1 = P1
        self.P2 = P2
        self.x1 = P1.x
        self.y1 = P1.y
        self.x2 = P2.x
        self.y2 = P2.y
        self.dx = abs(self.x2 - self.x1)
        self.dy = abs(self.y2 - self.y1)
        self.length = np.sqrt(self.dx ** 2 + self.dy ** 2)
        self.angle = np.inf if self.dx == 0 else np.atan(self.dy / self.dx)
        self.central = (P1 + P2) / 2
        self.xmax = max(self.x1, self.x2)
        self.xmin = min(self.x1, self.x2)
        self.ymax = max(self.y1, self.y2)


    def __str__(self):
        return f"polygon({self.P1},{self.P2})"
    def print_each(self,value=1):
        if value==1: return f"{self.P1}"
        elif value==2: return f"{self.P2}"

class Section:
    def __init__(self,v1=0,v2=0,weight=1):#约定v1<=v2
        v1,v2=min(v1,v2),max(v1,v2)
        self.v1=v1
        self.v2=v2
        self.central=(v1+v2)/2
        self.length=abs(v2-v1)
        self.weight=weight
    def __str__(self):
        return f"[{self.v1},{self.v2}]"
    def divide(self,div):
        if div <= self.v1:
            return (None, self,0)
        elif div >= self.v2:
            return (self,None,1)#先小区间再大区间,最后分割比，1为v2
        else:
            _n=(div-self.v1)/self.length
            return (Section(self.v1,div,self.weight*_n),Section(div,self.v2,self.weight*(1-_n)),_n)
    def percentile(self,perc=0.5):
        return self.v1+perc*self.length   

def I(A,B,i):
    return A*i+B*(1-i)
def I_MAX(A,B,i):
    return I(max(A,B),min(A,B),i)
def I_MIN(A,B,i):
    return I(min(A,B),max(A,B),i)
def points2segs(pts:list):
    if len(pts) <= 1:
        return []            # 原来返回单个 Segment(), 调用方 segs.extend() 会 TypeError
    segs = []
    for i in range(len(pts)-1):
        segs.append(Segment(pts[i],pts[i+1]))
    return segs
def seg2sec(seg:Segment,axis=None):
    if axis == 'x':
        return Section(seg.P1.x,seg.P2.x,weight=seg.length)
    if axis == 'y':
        return Section(seg.P1.y,seg.P2.y,weight=seg.length)
    #print(seg.length)
    return (Section(seg.P1.x,seg.P2.x,seg.length),Section(seg.P1.y,seg.P2.y,seg.length))
def central(segs:list):
    res = Point(0,0)
    total_len = 0
    for seg in segs:
        #print(res,total_len,seg.central * seg.length)
        res += seg.central * seg.length
        total_len += seg.length

    if total_len == 0:          # 所有段长度都为 0 (点状/退化) → 退化成简单平均
        if not segs:
            raise ValueError("central: 一个采样点都没有")
        acc = Point(0,0)
        for seg in segs:
            acc += seg.central
        return acc / len(segs)
    return res / total_len

def divide_part(sections:list,div:float):
    part1,part2=[],[]
    #prt_point_in_list(sections)
    for sec in sections:
        p1,p2,_n=sec.divide(div)
        '''print(p1,p2,end="\t")
        if p1:print("p1",end="\t")
        if p2:print("p2",end='')'''
        
        if p1:
            #print(p1.weight)
            part1.append((p1,_n))
        if p2:
            part2.append((p2,1-_n))
        '''print()'''
        #prt_point_in_list([part1[i][0] for i in range(len(part1))])
    return part1,part2

def return_segement(name:str=None,SAMP=15,perc=0.5,ifnormal=False,pts_list=None):
    """内部件 → (中宫盒[x1,y1,x2,y2], 中心[xm,ym])

    pts_list: 已经算好的骨架点集 (每笔一个点表)。给了就不再做 return_bone 和
              stroke_point —— 调用方 (ids_anal.surround) 的 ibb1 通路已经算过一次,
              同一条笔画没必要算两遍。不给就退化成原来的"名字 → 展平 → 采样"。
    """
    if pts_list is None:
        bone = return_bone(name)
        pts_list = [stroke_point(s, SAMP)[0] for s in bone.split("$")]
    segs = []
    for pts in pts_list:
        segs.extend(points2segs(pts))
    #prt_point_in_list(segs)
    pm = central(segs)
    xm,ym = pm.x,pm.y
    #prt_point_in_list(segs)
    #print(xm,ym)
    x_sec,y_sec=[],[]
    for seg in segs:#转换成两个方向的分段区间
        xs,ys=seg2sec(seg)
        #print(xs.weight,ys.weight)
        #print(seg,xs,ys)
        x_sec.append(xs)
        y_sec.append(ys)
        #prt_point_in_list(x_sec)
    
    x_secg = divide_part(x_sec,xm)
    y_secg = divide_part(y_sec,ym)
    '''for i in x_sec[0]:
        print(i[0],i[1])'''
    '''for i in x_sec[1]:
        print(i[0],i[1])'''
    x1=x2=0
    y1=y2=0
    lx1=lx2=ly1=ly2=0
    #print(len(x_sec[0]),len(x_sec[1]))
    for sec,_n in x_secg[0]:
        #print(sec.weight,_n)
        #print(sec,_n)
        x1 += I_MIN(sec.v1,sec.v2,perc)*sec.weight
        lx1 += sec.weight
    for sec,_n in x_secg[1]:
        #print(sec,_n)
        x2 += I_MAX(sec.v1,sec.v2,perc)*sec.weight
        lx2 += sec.weight
    for sec,_n in y_secg[0]:
        y1 += I_MIN(sec.v1,sec.v2,perc)*sec.weight
        ly1 += sec.weight
    for sec,_n in y_secg[1]:
        y2 += I_MAX(sec.v1,sec.v2,perc)*sec.weight
        ly2 += sec.weight
    #print(y1,ly1)
    # 除零修正: 某一侧**没有墨量**时 (例如纯横线在 y 方向上两侧都空), 那些区间
    # 全是零长度的, divide() 会把它们全分给另一侧, 于是这里的 lx/ly 为 0。
    # 原来写的是 x1 /= max(lx1,1) —— 等于 0/1 = 0.0, 得到一个落在画布原点的
    # 假边界 (实测 一 给出 y1=0.0, 丨 给出 x1=0.0)。正确语义是"该侧边界就在中心",
    # 后面 min(x1, xm-15) / max(x2, xm+15) 会再保证一个最小半幅。
    x1 = x1 / lx1 if lx1 else xm
    x2 = x2 / lx2 if lx2 else xm
    y1 = y1 / ly1 if ly1 else ym
    y2 = y2 / ly2 if ly2 else ym
    x1 = min(x1,xm-15)
    x2 = max(x2,xm+15)
    y1 = min(y1,ym-15)
    y2 = max(y2,ym+15)
    if ifnormal:
        S = (x2-x1)*(y2-y1)
        kx = (x2-xm)/(x2-x1)
        ky = (y2-ym)/(y2-y1)
        L = np.sqrt(S)
        x1 = xm - L*(1-kx)
        x2 = xm + L*kx
        y1 = ym - L*(1-ky)
        y2 = ym + L*ky
    print(x1,',',y1,',',x2,',',y2)
    return [x1,y1,x2,y2],[xm,ym]#Bbox(Point(x1,y1),Point(x2,y2))
if __name__ == "__main__":
    return_segement('u4e00',perc=0.5)
