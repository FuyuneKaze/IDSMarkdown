import numpy as np

class Point:
    def __init__(self,x,y):
        self.x=x
        self.y=y
        self.length = np.sqrt(x**2+y**2)

    def __add__(self, other):
        return Point(self.x+other.x,self.y+other.y)
    def meas(self):
        return np.sqrt((self.x)**2+(self.y)**2)
    def __len__(self):
        return 2
    def __mul__(self, other):
        if isinstance(other,int) or isinstance(other,float):
            return Point(other*self.x,other*self.y)
        elif isinstance(other,Point):
            return self.x*other.y-self.y*other.x
        else:
            return None
    def __sub__(self, other):
        return Point(self.x-other.x,self.y-other.y)
    def __truediv__(self, other):
        return Point(self.x/other,self.y/other)
    def distance(self,other):
        return np.sqrt((self.x-other.x)**2+(self.y-other.y)**2)
    def __str__(self):
        #print(f"({self.x},{self.y})")
        return f"({self.x},{self.y})"
    def normalize(self):
        return self/np.sqrt((self.x)**2+self.y**2)
    def swap(self):
        return Point(self.y,self.x)
    def round(self):
        return Point(round(self.x),round(self.y))


class Bbox:
    def __init__(self,P1:Point,P2:Point):
        self.P1=P1
        self.P2=P2
        self.x1=P1.x
        self.y1=P1.y
        self.x2=P2.x
        self.y2=P2.y
        self.width=self.x2-self.x1
        self.height=self.y2-self.y1
        self.center=(P1+P2)/2
        self.qua=(self.x1,self.y1,self.x2,self.y2)

    def __add__(self, other):
        return Bbox(Point(min(self.x1,other.x1),min(self.y1,other.y1)),Point(max(self.x2,other.x2),max(self.y2,other.y2)))
    def __mul__(self, other):
        if max(self.x1,other.x1)>min(self.x2,other.x2) or max(self.y1,other.y1)>min(self.y2,other.y2):
            return None
        else:
            return Bbox(Point(max(self.x1,other.x1),max(self.y1,other.y1)),Point(min(self.x2,other.x2),min(self.y2,other.y2)))
    def __str__(self):
        return f"[({self.x1},{self.y1}),({self.x1},{self.y2}),({self.x2},{self.y2}),({self.x2},{self.y1})]"

    def outerBox(self, points):
        x1,y1,x2,y2=200,200,0,0
        for p in points:
            x1 = min(p.x,x1)
            x2 = max(p.x,x2)
            y1 = min(p.y,y1)
            y2 = max(p.y,y2)
        self.x1=x1
        self.x2=x2
        self.y1=y1
        self.y2=y2

    def innerBox(self, points, cent=Point(100,100)):
        x1,x2,y1,y2 = 200,200,0,0
        for p in points:
            if p.x < cent.x:
                x1 = max(p.x,x1)
            else:
                x2 = min(p.x,x2)
            if p.y < cent.y:
                y1 = max(p.y,y1)
            else:
                y2 = min(p.y,y2)
        self.x1=x1
        self.x2=x2
        self.y1=y1
        self.y2=y2
    def round(self):
            return Bbox(self.P1.round(),self.P2.round())

def prt_point_in_list(pl:list):
    print("[",end="")
    for e in pl:
        p=e
        if not isinstance(p,float):
            print(p,end=",")
            continue
        print(p.round(),end=",")
    print("\033[1D\033[0J]")
def Interp(E1,E2,t):#插值函数
    t=1-t#我神经病了又懒得改，所以只能打个补丁
    if (isinstance(E1,int) or isinstance(E1,float)) and (isinstance(E2,int) or isinstance(E2,float)):
        return E1*t+E2*(1-t)
    elif isinstance(E1,list) and type(E2) == type(E1) and len(E1)==len(E2):
        inlist=[]
        for i in range(len(E1)):
            inlist.append(E1[i]*t+E2[i]*(1-t))
        return inlist
    elif isinstance(E1,tuple) and type(E2) == type(E1) and len(E1)==len(E2):
        intuple=[]
        for i in range(len(E1)):
                intuple.append(E1[i]*t+E2[i]*(1-t))
        return tuple(intuple)
    elif isinstance(E1,Point) and type(E2) == type(E1) and len(E1)==len(E2):
        return E1*t+E2*(1-t)
    else:
        return None   


def Bezier2(P1:Point,P2:Point,P3:Point,step=0)->Point:
    #sampp=[i/SAMP for i in range(0,SAMP)]
    return Interp(Interp(P1,P2,step),Interp(P2,P3,step),step)
def Bezier3(P1:Point,P2:Point,P3:Point,P4:Point,step=0)->Point:
    return Interp(Bezier2(P1,P2,P3,step),Bezier2(P2,P3,P4,step),step)
def Bz2_tangent(P1:Point,P2:Point,P3:Point,step=0)->Point:
    #print(step)
    return P1*2*step+P2*(2-4*step)+P3*(-2+2*step)
def Bz3_tangent(P1:Point,P2:Point,P3:Point,P4:Point,step=0)->Point:
    return P1*3*step+P2*(6*step-9*step**2)+P3*(3-12*step+9*step**2)-P4*3*(1-step)**2


def normal(P1:Point,P2:Point,d=1)->Point:
    #print(P1.distance(P2))
    off =  d/P1.distance(P2)
    #print(P2-P1)
    return Point((P2.y-P1.y)*off, (P1.x-P2.x)*off)
def Bz2_normal(P1:Point,P2:Point,P3:Point,step=0)->Point:
    step=1-step
    tang=Bz2_tangent(P1,P2,P3,step)
    return Point(tang.x,-1*tang.y).swap()
def Bz3_normal(P1:Point,P2:Point,P3:Point,P4:Point,step=0)->Point:
    step=1-step
    tang=Bz3_tangent(P1,P2,P3,P4,step)
    return Point(tang.x,-1*tang.y).swap()

def length_of_line(points:tuple,end=None)->list:
    length=0
    endflag=len(points)-1
    if end:
        endflag=end
    li=[0]
    for i in range(endflag):
        length += points[i].distance(points[i+1])
        li.append(length)
    return li

def points_to_ang(p1:Point,p2:Point)->float:
    if p1.x == p2.x:
        return np.pi/2
    if p1.y == p2.y:
        return 0
    k = abs(p2.y-p1.y)/abs(p2.x-p1.x)
    return np.atan(k)
    pass

def area_slop(pl:list,index:int)->float:
    l=len(pl)
    if index==0:
        return points_to_ang(pl[0],pl[1])
    elif index == l-1:
        return points_to_ang(pl[l-1],pl[l-2])
    else:
        return (points_to_ang(pl[index],pl[index-1])+points_to_ang(pl[index],pl[index+1]))/2

def box_offset(points:list,tips=[None,None,None,None])->tuple:
    maxxi,minxi,maxyi,minyi=0,0,0,0
    maxx,minx,maxy,miny=0,200,0,200
    i=0
    for p in points:
        if p.x > maxx:
            maxx = p.x
            maxxi = i
        elif p.x < minx:
            minx = p.x
            minxi = i
        if p.y > maxy:
            maxy = p.y
            maxyi = i
        elif p.y < miny:
            miny = p.y
            minyi = i
        i+=1
    x1_ofs = 0 if area_slop(points,minxi) > 1.4 else 1#接近平行则该边为0不管，否则为1准备收缩
    x2_ofs = 0 if area_slop(points,maxxi) > 1.4 else 1
    y1_ofs = 0 if area_slop(points,minyi) < 0.1 else 1
    y2_ofs = 0 if area_slop(points,maxyi) < 0.1 else 1

    x1_ofs = tips[0] if tips[0] != None else x1_ofs
    x2_ofs = tips[1] if tips[1] != None else x2_ofs
    y1_ofs = tips[2] if tips[2] != None else y1_ofs
    y2_ofs = tips[3] if tips[3] != None else y2_ofs
    return (x1_ofs,y1_ofs,x2_ofs,y2_ofs)
    pass

def stroke_point(stro:str,SAMP=15)->tuple:#return sample point set
    #(type:0:0:x1:y1:x2:y2:x3:y3)
    #   0  1 2 3  4  5  6  7  8
    #type=1 直线，两个点
    #type=2 二次贝塞尔，三个点
    #type=3 折线，折角+圆角，三个点
    #type=4 折线+圆角，三个点
    #type=6 三次贝塞尔，四个点
    #type=7 纵撇，直线嫁接二次贝塞尔，四个点
    keys = stro.split("$")[0]
    keys=keys.split(":")
    keys=[float(i) if '.' in i else int(i) for i in keys]
    type=keys[0]
    SAMP=SAMP
    sampp=[i/SAMP for i in range(0,SAMP+1)]
    kMage=10
    normal_p=[]
    tail_type = keys[2]
    tips_list = [None,None,None,None]
    match tail_type:
        case 4:
            tips_list[3]=0#横钩
        case 5:
            tips_list[2]=0#竖钩
    
    match type:
        case 1:
            verts=[Point(keys[i],keys[i+1]) for i in range(3,6,2)]
            normal_p=[normal(verts[0],verts[1],1)]*2

            return tuple(verts),tuple(normal_p),box_offset(verts,tips_list)
            pass
        case 2:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,8,2)]
            #prt_point_in_list(ctrlP)
            #print()
            verts=[]

            for i in sampp:
                verts.append(Bezier2(ctrlP[0],ctrlP[1],ctrlP[2],i))
                normal_p.append(Bz2_normal(ctrlP[0],ctrlP[1],ctrlP[2],i).normalize())

            if tail_type==4:
                print(tips_list,box_offset(verts),box_offset(verts,tips_list))
            
            return tuple(verts),tuple(normal_p),box_offset(verts,tips_list)
            pass
        case 3:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,8,2)]
            #T1,T2=Point()
            T1=Interp(ctrlP[1],ctrlP[0],kMage/ctrlP[1].distance(ctrlP[0]))
            T2=Interp(ctrlP[1],ctrlP[2],kMage/ctrlP[1].distance(ctrlP[2]))

            verts=[ctrlP[0]]
            normal_p=[normal(T1,ctrlP[0],1)]

            for i in sampp:
                verts.append(Bezier2(T1,ctrlP[1],T2,i))
                normal_p.append(Bz2_normal(T1,ctrlP[1],T2,i).normalize())

            verts.append(ctrlP[2])
            normal_p.append(normal(ctrlP[2],T2,1))

            return tuple(verts),tuple(normal_p),box_offset(verts,tips_list)
            pass
        case 4:
            rate=6
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,8,2)]
            if ctrlP[1].distance(ctrlP[2]) < 120:
                rate=ctrlP[1].distance(ctrlP[2])/20
            #T1,T2=Point()
            T1=Interp(ctrlP[1],ctrlP[0],kMage*rate/ctrlP[1].distance(ctrlP[0]))
            T2=Interp(ctrlP[1],ctrlP[2],kMage*rate/ctrlP[1].distance(ctrlP[2]))

            verts=[ctrlP[0]]
            #print(ctrlP[0],T1)
            normal_p=[normal(T1,ctrlP[0],1)]

            for i in sampp:
                verts.append(Bezier2(T1,ctrlP[1],T2,i))
                normal_p.append(Bz2_normal(T1,ctrlP[1],T2,i).normalize())

            verts.append(ctrlP[2])
            normal_p.append(normal(ctrlP[2],T2,1))

            return tuple(verts),tuple(normal_p),box_offset(verts,tips_list)
            pass
        case 6:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,10,2)]
            verts=[]
            for i in sampp:
                verts.append(Bezier3(ctrlP[0],ctrlP[1],ctrlP[2],ctrlP[3],i))
                normal_p.append(Bz3_normal(ctrlP[0],ctrlP[1],ctrlP[2],ctrlP[3],i).normalize())

            return tuple(verts),tuple(normal_p),box_offset(verts)
            pass
        case 7:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,10,2)]
            verts=[ctrlP[0]]
            normal_p=[normal(ctrlP[0],ctrlP[1],1)]

            for i in sampp:
                verts.append(Bezier2(ctrlP[1],ctrlP[2],ctrlP[3],i))
                normal_p.append(Bz2_normal(ctrlP[1],ctrlP[2],ctrlP[3],i).normalize())
            return tuple(verts),tuple(normal_p),box_offset(verts)
            pass


def acute_divide(points:tuple, threshold=np.pi/3)->int:
    total_angle=0
    acute_i = []
    for i in range(len(points[2:])):
        v1 = points[i-2]-points[i-1]
        v2 = points[i] - points[i-1]
        total_angle += np.acos(v1*v2*(-1)/((v1.length)*(v2.length)))
        print(total_angle)
        if total_angle >= threshold:
            acute_i.append(i-1)
            total_angle=0
    return np.round(np.mean(acute_i))

def bone_shape_function(t,d=15,k=0.2):
    if t>1 or t<0:
        return 0
    else:
        return d*(1-t)+d*k*t


def generate_border(stro:str,shape=bone_shape_function,cutof=None,pts=None):

    # pts: 已经算好的 stroke_point 结果 (骨架点/法向/edgeofs) —— 同一条笔画要同时
    # 算"轮廓盒"和"中宫盒"时, 让两边共用一次采样, 别各算一次。
    points,normal,edgeofs = stroke_point(stro) if pts is None else pts
    border1=[]
    border2=[]
    ratio = length_of_line(points)
    #prt_point_in_list(ratio)
    ratio_nor = []
    for r in ratio:
        ratio_nor.append(r/ratio[-1])

    for i in range(len(points)):
        p=points[i]
        n=normal[i]
        r=ratio_nor[i]
        width = shape(r)
        border1.append(p+n*width)
        border2.append(p-n*width)

    border2.reverse()


    return tuple(border2+border1),edgeofs

def cut_index(tp:str, n:int)->list:
    """笔画类型 → 切点索引列表 (n = 采样点数)。想加新切法 (纵撇等) 只改这里。

    切点 i 表示"第 i 个采样点之后断开"。空列表 = 不切 (走一笔一盒的等价路径)。
    """
    match tp:
        case "3" | "4":      # 撇/捺/弯: 弯曲处在采样中点
            return [n // 2]
        case "2":
            return [n//2]
        case "7":
            return [1,1+(n-1)//2]
        case "6":
            return [n//3,2*n//3]
        case _:
            return []


def divide_boundary(stro:str,shape=bone_shape_function,ifshrink:bool=True,ofs=[15,10,15,10],pad=1.0):
    """一笔 → 若干 Bbox (按 cut_index 切开, 代替"一笔一盒")

    pad : 切成多段时每段外扩量。**必须 > 0**: 两段盒只"相切"时, 补集会沿那个角
          的对角缝连通, 两个腔被并成一个 (实测 日 的两格并成整字一个大面)。
          外扩方向是安全的 —— 盒偏大只会让腔变小/分裂。
    ifshrink/ofs : 只在**不切分**时生效 (edgeofs 描述的是整笔, 套到半段没意义)。

    不切分时返回**单个** box, 数值与 strokic_boundary 完全一致 —— 所以这条路径
    对所有类型都可以直接替代一笔一盒, 不需要特判。

    这里**不做任何容错**: 多笔画串直接 raise; 退化段 (宽或高为 0) 原样返回,
    由 cavity.part_boxes 统一按"没面积就不挡路"过滤 (与老路径 strokic_box 同一条
    规则, 只在一处)。以前那种"某段没点就 continue"的写法会留下 Bbox(0,0,0,0),
    打印成 [(0,0),(0,0),(0,0),(0,0)], 悄悄污染整个腔的判据。
    """
    if "$" in stro:
        raise ValueError(f"divide_boundary 只接受单笔画: {stro[:40]}")

    points, nor, edgeofs = stroke_point(stro)
    cuts = cut_index(stro.split(":")[0].strip(), len(points))

    # 轮廓点按切点分段 (每段 = 骨架点 ± 法向*该点笔宽)
    ratio = length_of_line(points)
    total = ratio[-1] or 1.0
    groups = {}
    seg = 0
    for i, p in enumerate(points):
        while seg < len(cuts) and i >= cuts[seg]:
            seg += 1
        w = shape(ratio[i] / total)
        b1, b2 = groups.setdefault(seg, ([], []))
        b1.append(p + nor[i] * w)
        b2.append(p - nor[i] * w)

    out = []
    for k in sorted(groups):
        b1, b2 = groups[k]
        bb = Bbox(Point(0, 0), Point(0, 0))
        bb.outerBox(tuple(b2[::-1] + b1))
        if len(groups) > 1 and pad:
            bb = Bbox(Point(bb.x1 - pad, bb.y1 - pad),
                      Point(bb.x2 + pad, bb.y2 + pad))
        elif ifshrink:
            bb.x1 += edgeofs[0] * ofs[0]
            bb.y1 += edgeofs[1] * ofs[1]
            bb.x2 -= edgeofs[2] * ofs[2]
            bb.y2 -= edgeofs[3] * ofs[3]
        out.append(bb)
    return out

def strokic_boundary(stro:str,ifshrink:bool=False,ofs=[15,10,15,10],shape=bone_shape_function,pts=None)->Bbox:
    
    
    border,edgeofs=generate_border(stro,shape=shape,pts=pts)
    '''if type == '3' or type == '4':
            print(stro)
            border,edgeofs=generate_border(stro,shape=shape,cutof=[i for i in range(9,18)])
            prt_point_in_list(border)
            pass'''
    bbox=Bbox(Point(0,0),Point(0,0))
    bbox.outerBox(border)
    #print(edgeofs)
    if ifshrink:
        bbox.x1 += edgeofs[0]*ofs[0]
        bbox.y1 += edgeofs[1]*ofs[1]
        bbox.x2 -= edgeofs[2]*ofs[2]
        bbox.y2 -= edgeofs[3]*ofs[3]
    
    return bbox

if __name__ == "__main__":
    stro="2:0:0:10:10:10:190:190:190"
    stro="3:0:0:50:50:10:190:190:190"
    #stro="6:0:0:100:10:100:80:100:150:10:190"
    #stro="7:0:7:106:16:106:78:106:157:53:187"
    #print(stroke_point(stro))
    #prt_point_in_list(stroke_point(stro)[0])
    #prt_point_in_list(stroke_point(stro)[1])
    #prt_point_in_list(generate_border(stroke_point(stro)[0],(0)))
    #prt_point_in_list(generate_border(stro))[0]
    #print(strokic_boundary(stro))
    #prt_point_in_list((stroke_point(stro)[0]))
    #print(acute_divide(stroke_point(stro)[0],threshold=np.pi/2))
    prt_point_in_list(divide_boundary(stro))

