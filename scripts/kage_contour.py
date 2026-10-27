"""
KAGE 轮廓提取 — Python 桥接

通过 subprocess 调用 Node.js (kage_contour.js) 获得带笔宽的笔画轮廓多边形。

每个轮廓是一个封闭多边形的点列表: [[x, y, off], [x, y, off], ...]
  off=0: 直线顶点
  off=1: 二次贝塞尔控制点

坐标范围: 0-200 (KAGE 标准画布)
"""

import json
import subprocess
import os

_SCRIPT = os.path.join(os.path.dirname(__file__), "kage_contour.js")

def get_data(targets,datas):
    
    for line in datas:
        if not line.startswith(' u'): continue
        cols = line.split(' | ')
        if len(cols) < 3: continue
        name = cols[0].strip()
        if name in targets:
            data = cols[2].strip()
            return data
            



def unfold(name,rect,d,s,datas):
    A = []
    parts = get_data(name,datas)

    for poly in parts:#递归出最原初的笔画数据
        if not poly.startswith("99"):
            A.append(poly)
        elif poly.startswith("99"):
            geom = poly.split(":")
            if len(geom)==8:
                geom.extend(["0","0","0"])
            geoml = (geom[3:7],(geom[1:3],geom[9,10]))#((x1,y1,x2,y2),((Dx,Dy),(Sx,Sy))
            A.append(geom[7],geom[3:7],geom[1:3],geom[9,10],datas)
    
    if A == []:
        bbox = None
    else:
        pass




def extract_contours(glyphs: list[dict]) -> list[dict]:
    """
    批量提取字形轮廓

    参数:
      glyphs: [{"name": "u4ebb-j", "data": "1:0:0:24:10:..."}, ...]

    返回:
      [{"name": "u4ebb-j", "contours": [[[x,y,off],...], ...]}, ...]
      如有错误: {"name": "...", "contours": [], "error": "..."}
    """
    input_json = json.dumps({"glyphs": glyphs}, ensure_ascii=False)
    proc = subprocess.run(
        ["node", _SCRIPT],
        input=input_json,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Node.js 错误 (code={proc.returncode}):\n{proc.stderr}")
    result = json.loads(proc.stdout)
    return result["glyphs"]


def extract_one(name: str, data: str) -> dict:
    """提取单个字形的轮廓"""
    results = extract_contours([{"name": name, "data": data}])
    return results[0]

def bbox(glyph: str, mode="glyph") -> tuple:
    
    if mode=="glyph":
        data = glyph.get("data",[])
        x1,y1,x2,y2=100,100,100,100
        for poly in data:
            for pnt in poly:
                x1 = min(x1,pnt[0])
                x2 = max(x2,pnt[0])
                y1 = min(y1,pnt[1])
                y2 = max(y2,pnt[1])
    else:
        data = glyph.split("$")
        x1,y1,x2,y2=100,100,100,100
        for prt in data:
            dts = prt.split(":")
            x1 = min(x1,eval(dts[3]))
            y1 = min(y1,eval(dts[4]))
            x2 = max(x2,eval(dts[5]))
            y2 = max(y2,eval(dts[6]))

    w = x2-x1
    h = y2-y1
    x0,y0 = 0.5*(x1+x2),0.5*(y1+y2)#center
    return (x1,x2,y1,y2,w,h,(x0,y0))

def trans_bone(part:str,dw=1,dh=1,dx=0,dy=0,center:tuple=None)->str:
    param = part.split(":")
    if param[0] == "99":
        x1 ,y1 = eval(param[3]), eval(param[4])
        x2, y2 = eval(param[5]), eval(param[6])
        w = x2-x1
        h = y2-y1
        x0, y0 = 0.5*(x1+x2),0.5*(y1+y2)
        if not center:
            center = (x0,y0)
        dc = (center[0]-x0,center[1]-y0)
        nx1, ny1 = center[0]-(dc[0]+w/2)*dw+dx, center[1]-(dc[1]+h/2)*dh+dy
        nx2, ny2 = center[0]-(dc[0]-w/2)*dw+dx, center[1]-(dc[1]-h/2)*dh+dy
        res = f"{int(param[0])}:{int(param[1])}:{int(param[2])}:{int(nx1)}:{int(ny1)}:{int(nx2)}:{int(ny2)}:{param[-1]}"#:{x2}:{y2}:{dw*x2}:{dh*y2}
    else:
        ctlpnt = [(eval(param[i*2-1]),eval(param[i*2])) for i in range(2,1+(len(param)-1)//2)]
        x1,x2 = min([p[0] for p in ctlpnt]), max([p[0] for p in ctlpnt])
        y1,y2 = min([p[1] for p in ctlpnt]), max([p[1] for p in ctlpnt])
        w = x2-x1
        h = y2-y1
        x0, y0 = 0.5*(x1+x2),0.5*(y1+y2)
        if not center:
            center = (x0,y0)
        dc = (center[0]-x0,center[1]-y0)
        res = f"{int(param[0])}:{int(param[1])}:{int(param[2])}"
        for p in ctlpnt:
            res += f":{int(center[0]-dw*(center[0]-p[0])+dx)}:{int(center[1]-dh*(center[1]-p[1])+dy)}"

    return res
def trans_bones(parts:str,dw=1,dh=1,dx=0,dy=0,center = None)->str:
    part = parts.split("$")
    res=""
    if center == None:
        center = bbox(parts,mode="bone")[-1]
    for prt in part:
        res+=f"{trans_bone(prt,dw,dh,dx,dy,center)}$"
    res.strip("$")
    return res
def adjust(db,name,dw=1,dh=1,dx=0,dy=0):
    for key in db:
        if name in key:
            glyph = db[key]
            db[key] = trans_bones(glyph,dw,dh,dx,dy)
    return db


def trans_glyph(json, dw=1,dh=1,dx=1,dy=1,angle=0):
    cent = bbox()
    return

def ch_uni(ch:str)->str:
    return "u"+f"{hex(ord(ch))}"[2:]

def printglyph(glyph:str):
    r = extract_one(ch,glyph)
    dats = r.get("contours", [])
    parse_and_draw_bezier(dats)
def getglyph(cod:str)->str:
    return glyph_extend.return_bone(cod)
# --- 测试 ---
if __name__ == "__main__":
    from test_bbox_alloc import load_glyph_db
    from draw_glyph import parse_and_draw_bezier

    DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"
    import glyph_extend, ids_anal

    ch = "u6234"#6234,7570,22a0b
    #glyph = glyph_extend.unfold(ch)
    #glyph = "".join([f"{i}$" for i in glyph]).strip("$")
    #glyph = glyph_extend.return_bone(ch,trans="")#0:99:1:0:0:200:200
    #glyph = glyph_extend.trans(glyph,(("0","0","200","200")⿰,("0","0"),("0","0")),tran="0:99:2.5:0:0:200:200")
    #glyph = ids_anal.IDS("⿱",[ch_uni("喵"),ch_uni("灬")])
    #glyph = ids_anal.IDS("⿰",[ch_uni("口"),ch_uni("鷄")])
    #glyph = ids_anal.IDS("⿲",[ch_uni("口"),ch_uni("口"),ch_uni("口")])
    #glyph = ids_anal.IDS("⿸",[ch_uni("鹿"),ch_uni("一")])
    glyph = ids_anal.IDS("⿺",[ch_uni("鬼"),ch_uni("口")])
    print(glyph)
    r = extract_one(ch,glyph)
    dats = r.get("contours", [])
    parse_and_draw_bezier(dats)
    '''cjk = glyph_extend.return_bone("u5fc3-02")
    printglyph(glyph_extend.trans(cjk,(("0","100","200","200"),("0","0"),("0","0"))))'''
    #printglyph(glyph_extend.trans(glyph_extend.trans(getglyph('u5fc3-09'),(("0","54","200","254"),("0","0"),("0","0"))),(("60","12","198","200"),("0","0"),("0","0"))))
    # 加载一个测试字形
'''    db = load_glyph_db(DUMP, {"u7389-j","u56d7"})

    db = adjust(db,"u7389",dw=0.75,dh=0.75)
    #db = adjust(db,"u738b",dw=0.75,dh=0.75)
    print(db)
    all = []
    for name, data in db.items():
        #print(data)
        r = extract_one(name, data)
        #print(r)
        dats = r.get("contours", [])'''
'''     if "u7389" in r.get("name",[]) or "u738b" in r.get("name",[]):
            for poly in dats:
                for pnt in poly:
                    #pnt[0] = 100+(pnt[0]-100)*0.7
                    #pnt[1] = 100+(pnt[1]-100)*0.7
                    pass
        '''
'''        all.extend(dats)
        n_contours = len(r.get("contours", []))
        n_pts = sum(len(c) for c in r.get("contours", []))
        print(f"{name}: {n_contours} 个轮廓, {n_pts} 个点")
        if r.get("error"):
            print(f"  错误: {r['error']}")
    #print(all)
    parse_and_draw_bezier(all)'''
    

