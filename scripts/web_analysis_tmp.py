import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import central_box_old as cb
from glyph_extend import return_bone
from stroke_outer import strokic_boundary
buf = io.StringIO()
f1 = lambda t: f"({t[0]:5.1f},{t[1]:5.1f})-({t[2]:5.1f},{t[3]:5.1f})"
CASES = [("口","u53e3"),("乂","u4e42"),("人","u4eba"),("我","u6211"),
         ("鹿","u9e7f"),("粤","u7ca4"),("影","u5f71"),("道","u9053"),("繁","u7e41")]
print(f"{'部件':5s} {'笔数':>4s} {'len权重 基准宽':>14s} {'ink权重 基准宽':>14s} {'墨迹宽':>7s} {'ink/len':>8s}")
import ids_anal
for ch, nm in CASES:
    with contextlib.redirect_stdout(buf):
        bones = return_bone(nm)
    st = [s for s in bones.split("$") if s.strip() and s.split(":")[0] in cb.STROKE_KINDS]
    boxes = []
    for s in st:
        with contextlib.redirect_stdout(buf):
            b = strokic_boundary(s, False)
        boxes.append((b.x1,b.y1,b.x2,b.y2))
    if not boxes: continue
    ink = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    res = {}
    for wgt in ("len","ink"):
        cb.WEIGHT = wgt
        b = cb.central_box(bones, ink_box=ink)
        res[wgt] = b[2]-b[0]
    print(f"{ch:5s} {len(st):4d} {res['len']:14.1f} {res['ink']:14.1f} "
          f"{ink[2]-ink[0]:7.1f} {res['ink']/res['len']*100:7.0f}%")
