import numpy as np

class Point:
    def __init__(self,x,y):
        self.x=x
        self.y=y

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

def prt_point_in_list(pl:list):
    print("[",end="")
    for e in pl:
        p=e
        print(p,end=",")
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
    tang=Bz2_tangent(P1,P2,P3,step)
    return Point(-1*tang.y,tang.x)
def Bz3_normal(P1:Point,P2:Point,P3:Point,P4:Point,step=0)->Point:
    tang=Bz3_tangent(P1,P2,P3,P4,step)
    return Point(-1*tang.y,tang.x)

def length_of_line(points:tuple,end=None, key=None)->float:
    length=0
    endflag=len(points)-1
    if end:
        endflag=end
    key_index=-1
    key_ratio=-1
    note=True
    li=[]
    for i in range(endflag):
        length += points[i].distance(points[i+1])
        li.append(length)

    if key:
        for i in range(len(li)):
            lens=li[i]
            if lens>key*length:#如果pi-pi+1间存在
                key_index = i
                if i == 0:
                    cur_len=li[i]
                    key_ratio = (key*length)/cur_len
                    li[i] = key*length
                    li.insert(i+1,cur_len-key*length)
                else:
                    cur_len = li[i]-li[i-1]
                    key_ratio = (key*length-li[i-1])/cur_len
                    li[i] = key*length-li[i-1]
                    li.insert(i+1,cur_len-key*length+li[i-1])
                
                #li.insert(i+1)
                break
    if key :
        return li,key_index,key_ratio
    else:
        return length

def stroke_point(stro:str)->tuple:#return sample point set
    #(type:0:0:x1:y1:x2:y2:x3:y3)
    #   0  1 2 3  4  5  6  7  8
    #type=1 直线，两个点
    #type=2 二次贝塞尔，三个点
    #type=3 折线，折角+圆角，三个点
    #type=4 折线+圆角，三个点
    #type=6 三次贝塞尔，四个点
    #type=7 纵撇，直线嫁接二次贝塞尔，四个点
    keys=stro.split(":")
    keys=[eval(i) for i in keys]
    type=keys[0]
    SAMP=15
    sampp=[i/SAMP for i in range(0,SAMP+1)]
    kMage=10
    normal_p=[]
    match type:
        case 1:
            verts=(Point(keys[i],keys[i+1]) for i in range(3,6,2))
            normal_p=[normal(verts[0],verts[1],1)]*2

            return tuple(verts),tuple(normal_p)
            pass
        case 2:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,8,2)]
            #prt_point_in_list(ctrlP)
            #print()
            verts=[]

            for i in sampp:
                verts.append(Bezier2(ctrlP[0],ctrlP[1],ctrlP[2],i))
                normal_p.append(Bz2_normal(ctrlP[0],ctrlP[1],ctrlP[2],i).normalize())

            return tuple(verts),tuple(normal_p)
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

            return tuple(verts),tuple(normal_p)
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

            return tuple(verts),tuple(normal_p)
            pass
        case 6:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,10,2)]
            verts=[]
            for i in sampp:
                verts.append(Bezier3(ctrlP[0],ctrlP[1],ctrlP[2],ctrlP[3],i))
                normal_p.append(Bz3_normal(ctrlP[0],ctrlP[1],ctrlP[2],ctrlP[3],i).normalize())

            return tuple(verts),tuple(normal_p)
            pass
        case 7:
            ctrlP=[Point(keys[i],keys[i+1]) for i in range(3,10,2)]
            verts=[ctrlP[0]]
            normal_p=[normal(ctrlP[0],ctrlP[1],1)]

            for i in sampp:
                verts.append(Bezier2(ctrlP[1],ctrlP[2],ctrlP[3],i))
                normal_p.append(Bz2_normal(ctrlP[1],ctrlP[2],ctrlP[3],i).normalize())
            return tuple(verts),tuple(normal_p)
            pass


def acute_divide(points:tuple, threshold=np.pi/3)->int:
    total_angle=0
    acute_i = []
    for i in range(len(points[2:])):
        v1 = points[i-2]-points[i-1]
        v2 = points[i] - points[i-1]
        total_angle += np.acos(-1*v1*v2/(len(v1)*len(v2)))
        if total_angle >= threshold:
            acute_i.append(i-1)
            total_angle=0
    return np.round(np.mean(acute_i))

def bone_shape_function(t,k=0.7,d=1):
    if t>1 or t<0:
        return 0
    if t<k:
        return d*k/t
    else:
        return d+d*(t-k)/k-1


def generate_border(points:tuple,normal:tuple,shape=bone_shape_function):
    k=0.9
    d=10
    length,key_i,key_r = length_of_line(points,None,k)#length 已分割添加极值点，key_i是前一个点的索引
    #points需要插入极值点，length已经插入极值点。原始n个点，n-1个线段，分割后n+1个点n个线段
    #ponts n+1, length n。 最后一个点的step就是100%。索引i的点应当是i-1 - i的线段长度作为step，即i-1的长度，逻辑和前面反了
    points=list(points)

    points.insert(key_i+1,Interp(points[key_i+1],points[key_i],key_r))
    border1, border2 = [],[]
    #print(length)
    for i in range(len(points)):
        if i==0: step=0
        else:
            step = length[i-1]/length[-1]
        border1.append()


    return points

    

def curve_normal(points:tuple)->tuple:
    pass

def visual_boundary(if_on,P1:tuple,P2:tuple,P3:tuple=None)->np.array:
    k=0.9#鼓起位置
    d=10#鼓起程度
'''    if if_on:
        boundary_point=(P1,add(Interp(P1,P2,k),offset_on_line(P1,P2,d)),\
                        P2,add(Interp(P1,P2,k),offset_on_line(P1,P2-1*d)))
        return boundary_point
    else:
        pass'''

if __name__ == "__main__":
    stro="2:0:0:10:10:10:190:190:190"
    stro="4:0:0:10:50:10:190:190:190"
    #stro="7:0:7:106:16:106:78:106:157:53:187"
    #print(stroke_point(stro))
    #prt_point_in_list(stroke_point(stro)[0])
    #prt_point_in_list(stroke_point(stro)[1])
    prt_point_in_list(generate_border(stroke_point(stro)[0],(0)))
