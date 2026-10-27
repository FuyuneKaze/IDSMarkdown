import glyph_extend
from kage_contour import trans_bone,trans_bones
import numpy as np
import stroke_outer
import cavity
import central_box

prioity = {}
left_weak = "卩丩丬爿片⺝⺼仌耒朿酉镸𨸏马馬弓山巾工土士子牛王歹止日斗木立禾示石矛目白田血虫舟糸羽羊舌缶米里车車身𧾷足豕豸言角齿金骨香音韋韦革面鬲黄黑黍鼠"
right_strong = "乚卩殳攵攴支鸟鳥页頁人卜戈隹犬"
hor_weak = "丨刂亻扌冫讠阝巜口犭彳饣氵忄纟糹㣺钅礻衤𤴔𧾷飠釒𩙿"
top_weak = "乛冖亠丷艹宀䒑𭕄爫㓁龸𰃮𥫗𫩠丷彑罓穴覀襾雨"
bottum_weak = "灬小"
bottum_strong = "齿金巾廾鱼魚食示"
ver_weak = "一𡭔⺌𦉰八人儿入罒皿"
outer_weak = "乙廴辶疒厂飞弋兀尢行辵走"

PART_CAND_L = ['-01','-08']
PART_CAND_M = ['-01','-08','-02']#
PART_CAND_R = ['-02','-08']
PART_CAND_T = ['-03','-09']
PART_CAND_C = ['-03','-24','-14','-04','-09']
PART_CAND_C_S = ['-14','-03','-24','-04','-09']
PART_CAND_B = ['-04','-24','-14','-09']
PART_CAND_B_S = ['-14','-04','-24','-09']


def hor_ver_stroke(glyph):
    hor = []
    ver = []
    for stro in glyph.split("$"):
        li = stro.split(":")
        if li[0] == "99":
            continue
            '''w = eval(li[5])-eval(li[3])
            h = eval(li[6])-eval(li[4])'''
        elif li[0] in ["1", "7"]:#, "2", "3", "4", "6"
            x = [float(i) for i in li[3::2]]
            y = [float(i) for i in li[4::2]]
            w = max(x)-min(x)
            h = max(y)-min(y)
            if w > h:
                hor.append(stro)
            elif h > w:
                ver.append(stro)
            else:
                '''hor.append(stro)
                ver.append(stro)'''
        elif li[0] in ["2","3"]:
            
            util = [[float(li[i+j]) for j in [0,1,2,3]] for i in range(3,len(li)-3,2)]
            for pair in util:
                w = abs(pair[0]-pair[2])
                h = abs(pair[3]-pair[1])
                if w > h:
                    hor.append(stro)
                elif h > w:
                    ver.append(stro)
                else:
                    '''hor.append(stro)
                    ver.append(stro)'''
        else:
            continue
        
    return (len(hor)+1,len(ver)+1)

def stronummap(x):
    x = max(0,x)
    x_q=x^2
    return x_q/(x_q+16)

def bbox(glyph:str)->tuple:
    parts = glyph.split("$")
    x1,y1,x2,y2=200,200,0,0
    all_px = []
    all_py = []
    box=stroke_outer.Bbox(stroke_outer.Point(200,200),stroke_outer.Point(0,0))
    box=stroke_outer.strokic_boundary(parts[0],ifshrink=True)
    for stro in parts:
        li = stro.split(":")
        if li[0] == "99":
            #x1, x2 = min(x1,eval(li[3])),max(x2,eval(li[5]))
            #y1, y2 = min(x1,eval(li[4])),max(x2,eval(li[6]))
            continue

        elif li[0] in ["1", "2", "3", "4", "6", "7"]:
            x = [float(i) for i in li[3::2]]
            y = [float(i) for i in li[4::2]]
            all_px.extend(x)
            all_py.extend(y)
            box = box+stroke_outer.strokic_boundary(stro,ifshrink=True,ofs=[10,5,10,5] # [10,5,10,5],
                                                    )
            #print(x,y)
            #print(x1,y1,x2,y2)
            '''x.extend([x1,x2])
            y.extend([y1,y2])
            x1, x2 = min(x), max(x)
            y1, y2 = min(y), max(y)'''
    x1,x2 = min(all_px),max(all_px)
    y1,y2 = min(all_py),max(all_py)
    b=box.qua
    return b#(x1,y1,x2,y2)
def strength(glyph:str)->str:
    return
def stre_map(a1:int,a2:int,rang = 0.8)->float:
    k = (a1/a2)**2
    return 0.5-0.5*rang*(1-k)/(1+k)

def bbox_adjust(glyph:str,smin=1,smax=1,mode = "ver")->tuple:
    parts = glyph.split("$")

    box = []

    for stroke in parts:
        li = stroke.split(":")
        x = [float(i) for i in li[3::2]]
        y = [float(i) for i in li[4::2]]
        w = max(x)-min(x)
        h = max(y)-min(y)
        if w == 0:
            bang = np.pi/2
        else:
            bang = np.atan(h/w)
        dh = 20*(np.pi/3-abs(bang))**2
        dw = 20*(np.pi/3-abs(np.pi/2-bang))**2
        if mode == "ver":
            dw = 0
        elif mode == "hor":
            dh == 0
        if bang <= np.pi/6:#横
            box.append([min(x),min(y)-dh*smin,max(x),max(y)+dh*smax])
        elif bang >= np.pi/3:
            box.append([min(x)-dw*smin,min(y),max(x)+dw*smax,max(y)])
        else:
            box.append([min(x),min(y),max(x),max(y)])
    res = box[0]
    for b in box:
        res[0] = min(res[0],b[0])
        res[1] = min(res[1],b[1])
        res[2] = max(res[2],b[2])
        res[3] = max(res[3],b[3])
    return tuple(res)

def minmax(minv,val,maxv):
    minv,maxv = min(minv,maxv),max(minv,maxv) 
    return min(maxv,max(minv,val))


# ============================================================
# 调试侧信道: IDS() 每次执行会记录本次实际用到的包围盒
#   供 preview 等工具原样画出(不同用途的盒故意不同, 不能重新猜)
#   components: 各输入部件该次实际使用的盒, 按参数顺序
#   cavity    : 包围运算符求出的空腔
#   outer     : 包围容器自身的外框
# ============================================================
LAST_BOXES = {"components": [], "cavity": None, "outer": None, "candidates": []}


def _clear_boxes():
    LAST_BOXES["components"] = []
    LAST_BOXES["cavity"] = None
    LAST_BOXES["outer"] = None
    LAST_BOXES["candidates"] = []


# ============================================================
# 字形名 fallback 查询
# ============================================================
_NAME_LINES = None


def name_lines():
    """字形名 → 文件行号 的精确索引 (首次调用构建一次)"""
    global _NAME_LINES
    if _NAME_LINES is None:
        m = {}
        for ln, line in enumerate(glyph_extend.dbs):
            p = line.find(" | ")
            if p > 0:
                m[line[:p].strip()] = ln
        _NAME_LINES = m
    return _NAME_LINES


def fallback_of(name:str):
    """报告某个字形名的 fallback 情况 → (实际命中的字形名, 是否发生了退化)

        fallback_of("u5e7f-05") → ("u5e7f-05", False)   变体存在, 没退化
        fallback_of("u7592-05") → ("u7592",    True)    无 -05, 退化到本体

    原理: 复刻 glyph_extend.get_data 的子串语义 ——
    在 name 的所有子串里取"文件行号最大"的那个命中。
    用途: 判断"作为外包围的部件是否真取到了 -05", 以决定是否要
    把它撑开、或找它的子节点表达式改写成三元表达式来优化。
    """
    idx = name_lines()
    best, hit = -1, None
    n = len(name)
    for i in range(n):
        for j in range(i + 1, n + 1):
            ln = idx.get(name[i:j])
            if ln is not None and ln > best:
                best, hit = ln, name[i:j]
    if hit is None:
        return None, True
    return hit, hit != name


# ============================================================
# 包围 (半包围/全包围) 用工具
# ============================================================

# 包围外框用 -05, 包围内部用 -06。缺失时 return_bone 会自己退化到可用字形,
# 不需要额外判存在性 (glyph_extend.get_data 本身就是子串匹配的退化语义)。
# 需要知道到底退化成谁时, 用上面的 fallback_of()。
def stroke_list(glyph:str)->list:
    """取直绘笔画行 (排除 99 引用与特殊行)"""
    out = []
    for s in glyph.split("$"):
        s = s.strip()
        if s and s.split(":")[0] in ("1", "2", "3", "4", "6", "7"):
            out.append(s)
    return out


def strokic_box(stro:str,ifshrink=False,pts=None):
    """单笔画的 strokic_boundary → (x1,y1,x2,y2); 失败返回 None

    pts: 已算好的骨架点 (stroke_point 的结果), 与中宫盒共用一次采样。
    """
    try:
        b = stroke_outer.strokic_boundary(stro,ifshrink,pts=pts)
    except Exception:
        return None
    if b.x2 > b.x1 and b.y2 > b.y1:
        return (b.x1, b.y1, b.x2, b.y2)
    return None


def union_boxes(boxes:list):
    """矩形并集 (外包)"""
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def glyph_boxes(glyph:str,ifshrink=True):
    """字形各笔画的 strokic 盒列表"""
    return [b for b in (strokic_box(s,ifshrink) for s in stroke_list(glyph)) if b]


def max_empty_rect(box:tuple, rects:list):
    """矩形障碍下的最大空矩形 (精确枚举, 不用栅格)

    候选左边界 ∈ {外框左沿} ∪ {障碍右沿}
    候选右边界 ∈ {外框右沿} ∪ {障碍左沿}
    固定 [L,R] 竖条后, y 方向的最大空隙即该条带的最优高度。
    因为障碍都是轴对齐矩形, 相邻 y 事件点之间覆盖关系恒定, 所以是精确解。
    返回 (x1,y1,x2,y2) 或 None
    """
    X1, Y1, X2, Y2 = box
    Ls = sorted({X1} | {min(max(r[2], X1), X2) for r in rects})
    Rs = sorted({X2} | {min(max(r[0], X1), X2) for r in rects})
    best, best_area = None, -1.0
    for L in Ls:
        for R in Rs:
            if R <= L:
                continue
            bl = sorted((max(r[1], Y1), min(r[3], Y2)) for r in rects
                        if r[0] < R and r[2] > L and r[1] < Y2 and r[3] > Y1)
            gaps, cur = [], Y1
            for b0, b1 in bl:
                if b0 > cur:
                    gaps.append((cur, b0))
                if b1 > cur:
                    cur = b1
            if cur < Y2:
                gaps.append((cur, Y2))
            for g0, g1 in gaps:
                a = (R - L) * (g1 - g0)
                if a > best_area:
                    best_area, best = a, (L, g0, R, g1)
    return best


def enclosure_cavity(glyph:str):
    """容器字形 → (空腔, 外框); 求不出返回 (None,None)

    这是**兜底**路径: 容器压根没形成封闭/半封闭口袋时 (比如 厂 只有两笔、
    或者该算符要求的边没被墨迹封住), cavity_list 会给空, 就退回老做法 ——
    最大内接空矩形。宁可排得难看, 也不要字消失。
    """
    bs = glyph_boxes(glyph,ifshrink=True)
    outer = union_boxes(bs)
    if not outer:
        return None, None
    return max_empty_rect(outer, bs), outer


# 包围算符方向表在 cavity.NEED (与空腔枚举放在一起, 只有一份)

def list_Int(list1,list2,t):
    lst=[]
    l = min(len(list1),len(list2))
    return [list1[i]*t+list2[i]*(1-t) for i in range(l)]
def I(A,B,t):return A*t+B*(1-t)

def value_map(val,omin=0,omax=1,tmin=0,tmax=1):
    return tmin+(tmax-tmin)*(val-omin)/max(0.01,omax-omin)
def box_map(box:list,central,k=1):
    xm,ym = central[0],central[1]
    #[x1,y1,x2,y2]
    x1,y1,x2,y2 = box[0],box[1],box[2],box[3]
    x1 = xm-k*(xm-x1)
    y1 = ym-k*(ym-y1)
    x2 = xm+k*(x2-xm)
    y2 = ym+k*(y2-ym)
    '''x1 = value_map(x1,xm,x1,I(xm,x1,k),I(x1,xm,k))
    y1 = value_map(y1,ym,y1,I(ym,y1,k),I(y1,ym,k))
    x2 = value_map(x2,xm,x2,I(xm,x2,k),I(x2,xm,k))
    y2 = value_map(y2,ym,y2,I(ym,y2,k),I(y2,ym,k))'''
    return [x1,y1,x2,y2]

def surround(op:str, args:list):
    """9 个包围算符的统一实现 (容器 -05, 内部件 -06, 内部件填进容器的腔)

    算符之间的差别只在 cavity.NEED 那一行 —— 这里没有 if/elif 的分叉。
    默认取**面积最大**的候选, 不是文档 §6.6 的"从上到下第一个":
    评分器实测 (web/analysis/score_cavity.py) 400 个真包围字里, 对"真有得选"
    的那些, 最大面积命中设计者的字形 95.8%, "第一个"只有 4.2%。
    """
    cjk1 = glyph_extend.return_bone(args[0]+"-05")
    cjk2 = glyph_extend.return_bone(args[1]+"-06")
    if not cjk1:
        return ""
    if not cjk2:
        return cjk1

    # faces() 顺带把墨迹外框还回来, 省掉一次 union(glyph_boxes(...))
    #cavity.SPLIT=True
    faces, outer = cavity.faces(cjk1,split=True)
    cands = cavity.rank_faces(faces, op)
    # 内部件外框: 走 stroke_outer 的盒 (glyph_boxes → strokic_box → strokic_boundary)
    #1.把ibb1和ibb2的return_bone路线复用
    #2.顺便接入ibb1的框比例放到ibb2的归一化
    #3.通过笔画复杂/内外框比例映射两种算法的混合比例
    # 骨架点只采一次, ibb1 的轮廓盒和 ibb2 的中宫盒共用 (两边原本各跑一次
    # stroke_point, 而 ibb2 还多跑了一次 return_bone)
    stros2 = stroke_list(cjk2)
    alpha = stronummap(2*len(stros2)-2)
    #print(alpha)
    pts2 = [stroke_outer.stroke_point(s) for s in stros2]   # (点, 法向, edgeofs)
    ibb1 = union_boxes([b for b in (strokic_box(s, True, p)
                                    for s, p in zip(stros2, pts2)) if b])
    ibb2,mp = central_box.return_segement(pts_list=[p[0] for p in pts2],
                                          perc=1,ifnormal=True)
    ibb2 = box_map(ibb2,[(ibb2[0]+ibb2[2])/2,(ibb2[1]+ibb2[3])/2],2)
    ibb = list_Int(ibb1,ibb2,alpha)
    #print(ibb)
    LAST_BOXES["outer"] = outer
    LAST_BOXES["components"] = [outer, ibb]
    LAST_BOXES["candidates"] = [f["box"] for f in cands]

    # 安放盒取**面内最大内接矩形**(f["ins"]), 不要用面的外接框(f["box"]):
    # 面常常是 L/U/梳形, 外接框会直接盖住容器墨迹 —— 视觉上就是"腔侵入字里"。
    cav = None
    if cands:
        cav = max(cands, key=lambda f: (f["ins"][2] - f["ins"][0]) *
                                        (f["ins"][3] - f["ins"][1]))["ins"]
    if cav is None and faces:
        # 兜底①: 没有合格口袋 → 取**最大的面**(不管开口方向)的内接矩形。
        # 面是补集, 按构造不含墨迹; 而下面的 max_empty_rect 会真的压到笔画上
        # (实测 鬼 相交 2 个笔画盒、老 相交 1 个)。
        big = max(faces, key=lambda f: f["area"])
        cav = cavity.inscribed(big["rects"]) or big["box"]
    if cav is None:
        # 兜底②: 连面都没有 (容器只有零碎笔画) → 老算法
        cav, _ = enclosure_cavity(cjk1)
    LAST_BOXES["cavity"] = cav

    if not cav or not ibb:
        print("  没腔/没内部件盒, 容器+内部件直接拼", op, args)
        return cjk1 + "$" + cjk2
    target = fit_into(ibb, cav, use_bbox=True)     # 用 return_segement 的框当基准
    if not target:
        return cjk1 + "$" + cjk2
    print("包围", op, args, "外框", outer, "候选", len(cands), "空腔", cav, "内部件盒", ibb)
    cjk2 = glyph_extend.trans(cjk2, (target, (0, 0), (0, 0)))
    return cjk1 + "$" + cjk2



def fit_into(inner_box:tuple, rect:tuple, lo=10, hi=190.0, use_bbox=False):
    """求 glyph_extend.trans 的目标矩形 (分轴决定映射基准)

    trans 的映射是  x' = R.x1 + (x/200)*(R.x2-R.x1)。
    基准按轴分别选:
      该轴包围盒超出 [lo,hi] → 用包围盒范围映射 (满幅/越界部件, 防溢出)
      否则                  → 用 0-200 整幅映射 (保留部件自带留白)

    为什么后者是默认: 部件的留白是设计者有意留的。若一律拿包围盒当基准,
    缩放比变成 空腔/包围盒, 越小的部件被放得越狠 —— 一个"点"的包围盒
    只有 ~36x66, 会被撑成整个空腔(实测差 5.5 倍)。
    lo/hi 取 20/180 是为了把"本该撑满"的大部件(人/付/乃等, 盒到 11~188)
    归到包围盒基准, 而留白大的小部件(口 32~168, 月 25.7~157)走 0-200。

    use_bbox=True : **无视 lo/hi, 一律用 inner_box 当基准**。
      给"内部件盒本身就是设计好的基准框"的场景用 —— central_box_new.return_segement
      给的框常常整块落在 [10,190] 里面, 走默认分支会被完全无视, 缩放不变
      (实测 (77.8,75.6)-(114.2,135.0) 和旧的 (54.9,50.0)-(140.3,153.8) 得到同一个结果)。
    """
    x1, y1, x2, y2 = inner_box
    if use_bbox:
        sx0, sx1 = x1, x2
        sy0, sy1 = y1, y2
    else:
        sx0, sx1 = (x1, x2) if (x1 < lo or x2 > hi) else (lo, hi)
        sy0, sy1 = (y1, y2) if (y1 < lo or y2 > hi) else (lo, hi)
    if sx1 <= sx0 or sy1 <= sy0:
        return None
    W = 200.0 * (rect[2] - rect[0]) / (sx1 - sx0)
    H = 200.0 * (rect[3] - rect[1]) / (sy1 - sy0)
    A = rect[0] - sx0 / 200.0 * W
    B = rect[1] - sy0 / 200.0 * H
    return (f"{A}", f"{B}", f"{A + W}", f"{B + H}")


def IDS(opertor:str,args:list)->str:
    _clear_boxes()
    match opertor:
        case "⿰":
            cjk1 = glyph_extend.return_bone(args[0]+"-01",parts_mode='single',order=PART_CAND_L)#获取骨架
            cjk2 = glyph_extend.return_bone(args[1]+"-02",parts_mode='single',order=PART_CAND_R)
            b1, b2 = bbox(cjk1), bbox(cjk2)#获取bbox
            LAST_BOXES["components"] = [b1, b2]
            w1, w2 = b1[2]-b1[0], b2[2]-b2[0]#宽度
            w1, w2 = minmax(5,w1,195),minmax(5,w2,195)
            split = 3+197*w1/(w1+w2)
            split = minmax(5,split,195)
            print(w1,w2,split)
            leftbound = split * 200 / max(b1[2], 1)
            rightbound = 200-200*(200-split)/(200-max(1,b2[0]))
            #leftbound = minmax(5,leftbound,200)
            #rightbound = minmax(0,rightbound,195)

            print(split,leftbound,rightbound)
            '''n_stroke1 = len(cjk1.split("$"))
            n_stroke2 = len(cjk2.split("$"))
            b1 = bbox_adjust(cjk1,0,0.5,'hor')
            b2 = bbox_adjust(cjk2,0,0,'hor')
            overlap1 = 1/n_stroke1
            overlap2 = 1/n_stroke2
            n_stroke1,n_stroke2 = hor_ver_stroke(cjk1)[1],hor_ver_stroke(cjk2)[1]
            adjust = stre_map(n_stroke1,n_stroke2,0.6)'''
            #print(n_stroke1,n_stroke2,adjust)
            #cjk1 = glyph_extend.trans(cjk1,(("0","0","100","200"),("0","0"),("0","0")))
            #cjk2 = glyph_extend.trans(cjk2,(("100","0","200","200"),("0","0"),("0","0")))
            #cjk1 = glyph_extend.trans(cjk1,(("0","0",f"{200*adjust*200/b1[2]-20*overlap1}","200"),("0","0"),("0","0")))
            #cjk2 = glyph_extend.trans(cjk2,((f"{200*(1-200*(1-adjust)/(200-b2[0]))+20*overlap2}","0","200","200"),("0","0"),("0","0")))
            cjk1 = glyph_extend.trans(cjk1,(("0","0",f"{leftbound}","200"),("0","0"),("0","0")))
            cjk2 = glyph_extend.trans(cjk2,((f"{rightbound}","0","200","200"),("0","0"),("0","0")))
            print(bbox(cjk1),bbox(cjk2))
            return cjk1+"$"+cjk2
        case "⿱":
            cjk1 = glyph_extend.return_bone(args[0]+"-03",parts_mode='single',order=PART_CAND_T)
            if chr(int('0x'+args[0][1:],16)) in top_weak.join(ver_weak):
                cjk2 = glyph_extend.return_bone(args[1]+"-04",parts_mode='single',order=PART_CAND_B_S)
            else:
                cjk2 = glyph_extend.return_bone(args[1]+"-04",parts_mode='single',order=PART_CAND_B)
            b1, b2 = bbox(cjk1), bbox(cjk2)
            LAST_BOXES["components"] = [b1, b2]
            h1, h2 = b1[3]-b1[1], b2[3]-b2[1]#高度
            h1, h2 = minmax(5,h1,195),minmax(5,h2,195)
            split = 3+197*h1/(h1+h2)
            split = minmax(5,split,195)
            print(h1,h2,split)
            bottombound = split * 200/ max(b1[3],1)
            topbound = 200-200*(200-split)/(200-max(1,b2[1]))
            print(split,bottombound,topbound,b2[1])
            '''n_stroke1 = len(cjk1.split("$"))
            n_stroke2 = len(cjk2.split("$"))
            b1 = bbox_adjust(cjk1,0,0.5,'ver')
            b2 = bbox_adjust(cjk2,0,0,'ver')
            n_stroke1,n_stroke2 = hor_ver_stroke(cjk1)[0],hor_ver_stroke(cjk2)[0]

            overlap1 = 1/n_stroke1
            overlap2 = 1/n_stroke2
            #adjust = 1+(n_stroke1/n_stroke2-1)*0.4
            adjust = stre_map(n_stroke1,n_stroke2,0.6)
            print(n_stroke1,n_stroke2,adjust)
            from kage_contour import trans_bones

            #cjk1 = trans_bones(cjk1,1,adjust,0,0,center=(0,20))
            #cjk2 = trans_bones(cjk2,1,1-adjust,0,0,center=(0,180))
            cjk1 = glyph_extend.trans(cjk1,(("0","0","200",f"{200*adjust*200/b1[3]-20*overlap1}"),("0","0"),("0","0")))
            cjk2 = glyph_extend.trans(cjk2,(("0",f"{200*(1-200*(1-adjust)/(200-b2[1]))+20*overlap2}","200","200"),("0","0"),("0","0")))
            '''
            cjk1 = glyph_extend.trans(cjk1,(("0","0","200",f"{bottombound}"),("0","0"),("0","0")))
            cjk2 = glyph_extend.trans(cjk2,(("0",f"{topbound}","200","200"),("0","0"),("0","0")))

            #print(200*adjust*200/b1[3],200*(1-200*(1-adjust)/(200-b2[1])))
            print(b1,b2)
            return cjk1+"$"+cjk2
        case "⿲":
            cjk1 = glyph_extend.return_bone(args[0]+"-01")
            cjk2 = glyph_extend.return_bone(args[1]+"-01")
            cjk3 = glyph_extend.return_bone(args[2]+"-02")
            b1, b2, b3 = bbox(cjk1), bbox(cjk2), bbox(cjk3)
            LAST_BOXES["components"] = [b1, b2, b3]
            w1, w2 ,w3 = b1[2]-b1[0], b2[2]-b2[0], b3[2]-b3[0]
            w1, w2 ,w3 = minmax(5,w1,195),minmax(5,w2,195),minmax(5,w3,195)
            split1 = 1+199*w1/(w1+w2+w3)
            split2 = 199-199*w3/(w1+w2+w3)
            split1, split2 = minmax(2,split1,90),minmax(110,split2,198)
            print(w1,w2,w3,split1,split2)
            leftbound = split1 * 200 / max(b1[2], 1)
            rightbound = 200-200*(200-split2)/(200-max(1,b3[0]))

            k_c = (split2-split1)/(b2[2]-b2[0])
            centerbound1 = split1 - b2[0]*k_c
            centerbound2 = split2 + (200-b2[2])*k_c

            print(leftbound,rightbound,b1[2],b2[0],b2[2],b3[0])
            cjk1 = glyph_extend.trans(cjk1,(("0","0",f"{leftbound}","200"),("0","0"),("0","0")))
            cjk2 = glyph_extend.trans(cjk2,((f"{centerbound1}","0",f"{centerbound2}","200"),("0","0"),("0","0")))
            cjk3 = glyph_extend.trans(cjk3,((f"{rightbound}","0","200","200"),("0","0"),("0","0")))
            #return IDS("⿰",[args[0],IDS("⿰",[args[1],args[2]])])
            return cjk1+"$"+cjk2+"$"+cjk3
            pass
        case "⿳":
            cjk1 = glyph_extend.return_bone(args[0]+"-03")
            cjk2 = glyph_extend.return_bone(args[1]+"-03")
            cjk3 = glyph_extend.return_bone(args[2]+"-04")
            b1, b2, b3 = bbox(cjk1), bbox(cjk2), bbox(cjk3)
            LAST_BOXES["components"] = [b1, b2, b3]
            h1, h2 ,h3 = b1[3]-b1[1], b2[3]-b2[1], b3[3]-b3[1]
            h1, h2 ,h3 = minmax(5,h1,195),minmax(5,h2,195),minmax(5,h3,195)
            split1 = 1+199*h1/(h1+h2+h3)
            split2 = 199-199*h3/(h1+h2+h3)
            split1, split2 = minmax(2,split1,90),minmax(110,split2,198)
            topbound = split1 * 200 / max(b1[3], 1)
            bottombound = 200-200*(200-split2)/(200-max(1,b3[1]))

            k_c = (split2-split1)/(b2[3]-b2[1])
            centerbound1 = split1 - b2[1]*k_c
            centerbound2 = split2 + (200-b2[3])*k_c

            cjk1 = glyph_extend.trans(cjk1,(("0","0","200",f"{topbound}"),("0","0"),("0","0")))
            cjk2 = glyph_extend.trans(cjk2,(("0",f"{centerbound1}","200",f"{centerbound2}"),("0","0"),("0","0")))
            cjk3 = glyph_extend.trans(cjk3,(("0",f"{bottombound}","200","200"),("0","0"),("0","0")))
            #return IDS("⿰",[args[0],IDS("⿰",[args[1],args[2]])])
            return cjk1+"$"+cjk2+"$"+cjk3
            pass
        # 一元变换 ⿾镜像 / ⿿旋转: 部件不缩放, 只追加一条变换命令
        # 命令由渲染器 dfTransform 对**成品轮廓**执行 (权威语义), 所以这里不需要
        # 自己算坐标。两个约定见 kage-bundle.js:
        #   ① a3 = 四分之一圈计数 (1=90° 2=180° 3=270°); 库里 0:99:2 有 79 次,
        #      0:99:1 只有 1 次 → ⿿ 默认 180°
        #   ② 命令框要比画布宽: dfTransform 要求一条多边形的所有点都在框内才变换,
        #      墨迹经常超出 0-200 几个像素, 用紧框就会"只转一半"
        case "⿾" | "⿿":
            cjk = glyph_extend.return_bone(args[0])
            if not cjk:
                return ""
            xform = "0:98:0:-20:-20:220:220" if opertor == "⿾" else "0:99:2:-20:-20:220:220"
            return cjk + "$" + xform

        # 包围算符 9 个: 语义差别只在"要求容器的哪几条边被墨迹封住",
        # 所以共用一个分支 (见 cavity.NEED 那张方向表)。
        case "⿴" | "⿵" | "⿶" | "⿷" | "⿸" | "⿹" | "⿺" | "⿼" | "⿽":
            return surround(opertor, args)
