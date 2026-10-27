

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"
with open(DUMP,encoding="utf-8") as f:
        f.readline(); f.readline()
        dbs = f.readlines()
#print(len(dbs))


def _num(s):
    """数字字段解析 (比 eval 快 ~45 倍: eval 每次都要编译表达式)

    库里的坐标有整数也有小数 (104 / 54.16), 用 '.' 判断走 int 还是 float ——
    用 try/except 反而更慢 (小数占多数, 每次都要抛一次异常)。
    """
    return float(s) if '.' in s else int(s)

def fallback_candidate(entries:list,order:list)->str:#cand:['-05',...]
    selected = entries[0]#(name,ids)
    if not order:
        for cand in entries:
            if len(cand[0]) < len(selected):
                selected = cand
        return selected[1],None#(name,ids)[1],fix
    if len(entries)==1:#返回本身
        entriesparts1=entries[0][1].split("-")
        return entries[0][1],entriesparts1[min(1,len(entriesparts1)-1)]#(name,ids)[1],fix
    #print(order)
    #order.reverse()
    iffindfix = False
    finalfix = ""
    for postfix in order:
        if iffindfix:break
        for cand in entries:
            cand_varidx = cand[0].split("-")[min(1,len(cand[0].split("-"))-1)]
            if "-"+cand_varidx==postfix:#似乎变体标识符都在第二个，不过这样可能选不了var后面的了
                iffindfix=True
                finalfix = postfix
                if "-"+selected[0].split("-")[min(1,len(selected[0].split("-"))-1)]==postfix and len(selected[0]) > len(cand):
                    continue
                selected = cand
                #if postfix=="-05": print("-"+selected[0].split("-")[min(1,len(selected[0].split("-"))-1)],postfix)
           
    return selected[1],finalfix#(ids,fix)

def get_data(targets:str,datas:list=dbs,mode="single",order:list=None,exact:bool=False)->str:
    """查字形数据

    exact=False (默认, 第一轮叶子查找用):
        "名字是目标的**子串**"就算命中, 后面的覆盖前面的 → 最后一个命中胜出。
        查 "u670b-04" 在该变体缺失时会退化成命中 "u670b", 这就是"后缀退化到本体"。
        这条语义必须保留: ids_anal 传进来的是加过后缀的叶子名, 依赖它能退化。

    exact=True (拆笔画递归时用):
        ① 名字**完全相等**优先 (同名重复仍取最后一个);
        ② 没有精确名时, 在子串命中里取**名字最长**的 (同长取行号大的)。
        为什么必须这样: 库里有大量互为子串的拼接名 (u2ff1-cdp-88b4-u6bd4 与
        u6bd4-j / u2ff1 / cdp-88b4 ...), 只按"行号最大"会串味 —— 实测 鹿-05 引用
        u2ff1-cdp-88b4-u6bd4 拿到了比 (5 笔) 而不是正确的 10 笔, 于是 ⿸鹿 的容器
        丢了中间, 腔也跟着错。
    """
    data = ""
    possible_entry = []
    charhead = targets.split("-")[0]#粗略用第一个作为字头
    best_len = -1
    #print(len(datas))
    for line in datas:
        #if not line.startswith(' u'): continue
        cols = line.split(' | ')
        if len(cols) < 3: continue
        name = cols[0].strip()
        if not exact:
            if name in targets:#未设计fallback
                data = cols[2].strip()
        else:
            if name == targets:
                data = cols[2].strip()
                best_len = 1 << 30          # 精确最优, 后续子串命中不再覆盖
            elif name in targets and len(name) > best_len:
                best_len = len(name)
                data = cols[2].strip()
        if mode == "candidate":
            if charhead == name.split("-")[0]:#选的全部都是uxxxx开头的
                possible_entry.append((cols[0].strip(),cols[2].strip()))#(name,ids)
                #键值对方便查找元后缀，[2]是展开后的
    if mode == "single":
        return data#ids
    elif mode == "candidate":#(ids,fix)
        #print(possible_entry)
        return fallback_candidate(possible_entry,order)#和data展开后保持一致
    else:
        return None



class glyph_node:
    def __init__(self,glyph):
        self.glyph = glyph
        self.list = glyph.split(":")
        if self.list[0]=="99":
            self.child = get_data(self.list[7]).strip("$").split("$")
        elif self.list[0]=="0":
            self.child = None
        else:
            self.child = None
    
    def tranform_child(self):
        if self.child:
            rect = [_num(i) for i in self.list[3:7]]
            pd = [_num(i) for i in self.list[1:3]]
            if len(self.list) < 11:
                ps = [0,0]
            else:
                ps = [_num(i) for i in self.list[10:12]]
            for child in self.child:
                child_parts = child.split(":")
                if child_parts[0] == "99":
                    pass

def eval1(n):
    if isinstance(n,int) or isinstance(n,float):
        return n
    elif isinstance(n,str):
        return _num(n)
    else:
        return n

def unfold(name,glyph=(("0","0","200","200"),(0,0),(0,0)),datas=dbs,mode="single",order:list=None,exact:bool=False)->list:
    """拆笔画

    exact=False (默认): 顶层叶子查找, 保留"子串退化"语义 (查 u670b-04 可退化到 u670b)。
    exact=True       : 字形**内部**的 99 引用, 用精确优先 (见 get_data 的说明)。
    递归一律 exact=True —— 内部的引用名是库里的真实名字, 不存在"加后缀"的需求,
    走子串会串味。
    """
    A = []
    print(name)
    if A == [] and mode == "candidate":
        kage_data = get_data(name,datas,mode=mode,order=order)[0]#(ids,fix)[0]
    else:
        kage_data = get_data(name,datas,mode="single",order=order,exact=exact)#ids-> 99:0:0.......$99:....
        '''if not kage_data.startswith("99") and kage_data.startswith("u"):
        kage_data = "99:0:0:0:0:200:200:"+kage_data'''

    parts = kage_data.strip("$").split("$")#["99:...","99:..."]
    #print(parts)
    print(glyph)
    
    for L in parts:
        Lp = L.split(":")
        #print(Lp)
        if int(Lp[0]) in (1, 2, 3, 4, 6, 7):#底层笔画
            A.append(L)
        elif int(Lp[0]) == 0 and int(Lp[1]) in (97, 98, 99):#翻转
            print("op:",L)
            A.append(L)
        elif int(Lp[0]) == 99:#字形引用
            # 栏数补齐到 11 栏再把空栏当 0: 库里有 21 行是 9/10 栏的第三方数据
            # (hkcs_/xicheng_/zihai- 等, 形如 "...:name:0:"), 老代码只补 8 栏那种,
            # 遇到 9 栏取 Lp[10] 会 IndexError, 遇到 10 栏尾栏为空会在 eval1 里
            # eval('') 报 SyntaxError。这些行的 sx,sy 都是 0, 补齐后按"不拉伸"处理,
            # 与 kage-bundle.js (Math.floor(undefined)=NaN, 但 sx=sy=0 时整段跳过) 一致。
            if len(Lp) < 11 :
                Lp.extend(["0"]*(11-len(Lp)))
            Lp = [i if str(i).strip() else "0" for i in Lp]
            child_unfold = unfold(Lp[7],(Lp[3:7],(Lp[1],Lp[2]),(Lp[9],Lp[10])),datas,exact=True)
            #(x1,y1,x2,x3),(dx,dy),(sx,sy)
            A.extend(child_unfold)
    all_points = []#int

    for E in A:
        Ep = E.split(":")
        if int(Ep[0]) in (1, 2, 3, 4, 6, 7):
            for i in range(3,len(Ep)-1,2):
                all_points.append((_num(Ep[i]),_num(Ep[i+1])))
    bbox = None
    if all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        bbox = (min(xs), min(ys), max(xs), max(ys))#int
    #print(glyph)
    # 99 行两个点的权威语义在 kage-bundle.js 的 getEachStrokesOfBuhin:
    #   缝   sp = (列9,10)+100   (sx2,sy2)
    #   目标 dp = (列1,2)+100    (sx,sy)
    # 且 sx>100 时 sx-=200 (右半区位置折成负偏移), 否则把缝归到中心 (sx2=sy2=0)。
    # 写成 stretch(dp, sp, p, min, max): p<sp+100 → [min,sp+100]→[min,dp+100],
    #                                    否则      → [sp+100,max]→[dp+100,max]
    # 关键: 目标必须落在 min~max 之内, 两段才都是增函数; 早期版本把列1,2 当缝、
    # 列9,10 当目标再加 100, 于是 130/200 这类"右半区位置"变成 230/300 —— 跑出
    # 子件盒右沿, 右半段退化成减函数, 就是 忽(心)/鼻(自) 那种反向拉伸。
    sp = (eval1(glyph[2][0]),eval1(glyph[2][1]))#int 缝偏移 (列9,10)
    dp = (eval1(glyph[1][0]),eval1(glyph[1][1]))#int 目标偏移 (列1,2)

    if dp[0] != 0 or dp[1] != 0:
        if dp[0] > 100:
            dp = (dp[0]-200,dp[1])
        else:
            sp = (0,0)

    ps0 = (sp[0]+100,sp[1]+100)#int 缝的绝对坐标
    pd0 = (dp[0]+100,dp[1]+100)#int 目标的绝对坐标

    #拉伸
    if bbox is not None and dp != (0,0):
        x1,y1,x2,y2 = bbox
        sx,sy = ps0#int
        dx,dy = pd0

        count = 0
        for E in A:
            Ep = E.split(":")#str
            if int(Ep[0]) in (1, 2, 3, 4, 6, 7):

                #控制点
                for i in range(3,len(Ep)-1,2):
                    x = _num(Ep[i])
                    y = _num(Ep[i+1])

                    if x < sx:
                        x0 = x1 + (x-x1)*(dx-x1)/(sx-x1) if sx != x1 else dx
                    elif x > sx:
                        x0 = dx + (x-sx)*(x2-dx)/(x2-sx) if x2 != sx else dx
                    else:
                        x0 = dx
                    
                    if y < sy:
                        y0 = y1 + (y-y1)*(dy-y1)/(sy-y1) if sy != y1 else dy
                    elif y > sy:
                        y0 = dy + (y-sy)*(y2-dy)/(y2-sy) if y2 != sy else dy
                    else:
                        y0 = dy

                    Ep[i] = f"{x0}"
                    Ep[i+1] = f"{y0}"
            A[count] = "".join([f"{i}:" for i in Ep]).strip(":")
            count += 1
    
    x1,y1,x2,y2 = [int(x) for x in glyph[0]]#[float(x) for x in glyph[0]]
    w = x2-x1
    h = y2-y1

    count = 0
    for E in A:
        Ep = E.split(":")#str
        if int(Ep[0]) in (1, 2, 3, 4, 6, 7):

            for i in range(3,len(Ep)-1,2):
                x = _num(Ep[i])
                y = _num(Ep[i+1])

                x0 = (x/200)*w + x1
                y0 = (y/200)*h + y1

                Ep[i] = f"{x0}"
                Ep[i+1] = f"{y0}"
        A[count] = "".join([f"{i}:" for i in Ep]).strip(":")
        count += 1
    #print(A)
    return A

def is_in(stroke,box):
    parts = stroke.split(":")
    if parts[0] not in ["1", "2", "3", "4", "6", "7"]:
        return False
    
    for i in range(3, len(parts)-1, 2):
        x = float(parts[i])
        y = float(parts[i+1])
        if not (box[0] <= x <= box[2] and box[1] <= y <= box[3]):
            return False
    return True

def transf(stroke, mode, multi, box):
    """单笔画的翻转/旋转 —— 逐式对齐 kage-bundle.js 的 dfTransform

    mode : "97" 上下翻转 / "98" 左右翻转 / "99" 旋转
    multi: 旋转的四分之一圈计数 1=90°, 2=180°, 3=270° (97/98 忽略)
    box  : (x1,y1,x2,y2) 命令框。旋转的公式要用四条边, 只给中心算不出来。

    老写法 (x_new = cx + x*cos + y*sin) 是错的: 用了绝对坐标又加了一次中心,
    等于绕原点转再平移, 不是绕框中心转。库里 0:99:2 (180°) 出现 79 次,
    0:99:1 只有 1 次 —— ⿿ 的默认是 180°。
    """
    parts = stroke.split(":")
    if parts[0] not in ["1", "2", "3", "4", "6", "7"]:
        return stroke

    x1, y1, x2, y2 = [float(v) for v in box]

    for i in range(3, len(parts)-1, 2):
        x = float(parts[i])
        y = float(parts[i+1])

        if mode == "97":        # 上下翻转
            parts[i+1] = str(y1 + y2 - y)
        elif mode == "98":      # 左右翻转
            parts[i] = str(x1 + x2 - x)
        elif mode == "99":      # 旋转 (四分之一圈的整数倍)
            if multi == 1:
                parts[i] = str(x1 + (y2 - y))
                parts[i+1] = str(y1 + (x - x1))
            elif multi == 2:
                parts[i] = str(x1 + x2 - x)
                parts[i+1] = str(y1 + y2 - y)
            elif multi == 3:
                parts[i] = str(x1 + (y - y1))
                parts[i+1] = str(y2 - (x - x1))

    return ":".join(parts)



def bone_to_desmos(stroke):
    pl = stroke.split(":")
    #print(pl)
    res = "["
    if pl[0] not in ["1", "2", "3", "4", "6", "7"]:
        return[]
    else:
        for i in range(3,len(pl)-1,2):
            res+=f"({pl[i]},{pl[i+1]}),"
        res=res[:-1]
        res+="]"
        return res


def return_bone(name,geom = (("0","0","200","200"),(0,0),(0,0)),trans="",datas=dbs,parts_mode="single",order:list=None) ->str:
    A = unfold(name,glyph=geom,datas=datas,mode=parts_mode,order=order)#["99:...","99:..."]
    if trans:
        A.append(trans)
    res = []
    for part in A:
        if part.startswith("0:9"):
            cmd = part.split(":")
            mode = cmd[1]
            multi = cmd[2]
            box = [_num(i) for i in cmd[3:7]]
            count = 0
            for stroke in res:
                if is_in(stroke,box):
                    #print(stroke)
                    print(bone_to_desmos(stroke))
                    res[count] = transf(stroke,mode,multi,box)
                    print(bone_to_desmos(res[count]))
                    print("-"*10)
                else:
                    #print("\n",stroke)
                    pass
                count+=1
            pass
        else:
            res.append(part)
    glyph = "".join([f"{i}$" for i in res]).strip("$")
    return glyph
        
def trans(glyph,geom,tran=(None,None)):

    A = glyph.split("$")
    all_points = []
    for E in A:
        Ep = E.split(":")
        if int(Ep[0]) in (1, 2, 3, 4, 6, 7):
            for i in range(3,len(Ep)-1,2):
                all_points.append((_num(Ep[i]),_num(Ep[i+1])))
    bbox = None
    if all_points:
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        bbox = (min(xs), min(ys), max(xs), max(ys))#int
    #print(glyph)
    # 与 unfold 同一套 (见那里的注释): 缝=(列9,10)+100, 目标=(列1,2)±100
    sp = (eval1(geom[2][0]),eval1(geom[2][1]))#str->int 缝偏移
    dp = (eval1(geom[1][0]),eval1(geom[1][1]))#目标偏移

    if dp[0] != 0 or dp[1] != 0:
        if dp[0] > 100:
            dp = (dp[0]-200,dp[1])
        else:
            sp = (0,0)

    ps0 = (sp[0]+100,sp[1]+100)#int
    pd0 = (dp[0]+100,dp[1]+100)#int

    #拉伸
    if bbox is not None and dp != (0,0):
        x1,y1,x2,y2 = bbox
        sx,sy = ps0#int
        dx,dy = pd0

        count = 0
        for E in A:
            Ep = E.split(":")#str
            if int(Ep[0]) in (1, 2, 3, 4, 6, 7):

                #控制点
                for i in range(3,len(Ep)-1,2):
                    x = _num(Ep[i])
                    y = _num(Ep[i+1])

                    if x < sx:
                        x0 = x1 + (x-x1)*(dx-x1)/(sx-x1) if sx != x1 else dx
                    elif x > sx:
                        x0 = dx + (x-sx)*(x2-dx)/(x2-sx) if x2 != sx else dx
                    else:
                        x0 = dx
                    
                    if y < sy:
                        y0 = y1 + (y-y1)*(dy-y1)/(sy-y1) if sy != y1 else dy
                    elif y > sy:
                        y0 = dy + (y-sy)*(y2-dy)/(y2-sy) if y2 != sy else dy
                    else:
                        y0 = dy

                    Ep[i] = f"{x0}"
                    Ep[i+1] = f"{y0}"
            A[count] = "".join([f"{i}:" for i in Ep]).strip(":")
            count += 1
    
    x1,y1,x2,y2 = [float(x) for x in geom[0]]#[float(x) for x in glyph[0]]
    w = x2-x1
    h = y2-y1

    count = 0
    for E in A:
        Ep = E.split(":")#str
        if int(Ep[0]) in (1, 2, 3, 4, 6, 7):

            for i in range(3,len(Ep)-1,2):
                x = _num(Ep[i])
                y = _num(Ep[i+1])

                x0 = (x/200)*w + x1
                y0 = (y/200)*h + y1

                Ep[i] = f"{x0}"
                Ep[i+1] = f"{y0}"
        A[count] = "".join([f"{i}:" for i in Ep]).strip(":")
        count += 1
    if tran != (None,None):
        print(tran)
        if tran.startswith("0:9"):
            cmd = tran.split(":")
            mode = cmd[1]
            multi = cmd[2]
            box = [_num(i) for i in cmd[3:7]]
            count = 0
            for stroke in A:
                if is_in(stroke,box):
                    #print(stroke)
                    #print(bone_to_desmos(stroke))
                    A[count] = transf(stroke,mode,multi,box)
                    #print(bone_to_desmos(A[count]))
                    #print("-"*10)
                else:
                    #print("\n",stroke)
                    pass
                count+=1

    return "".join([f"{i}$" for i in A]).strip("$")


order=["-ww","-05","-04","-03","-02"]
print(get_data("u4eba-06",dbs,"candidate",order=order))