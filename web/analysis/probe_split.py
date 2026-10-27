import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend, ids_anal, cavity, stroke_outer as so
buf = io.StringIO()
def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)

# ① split=False 必须与旧行为逐位一致: 盒数 == 笔画数
print("① split=False: 障碍盒数 vs 笔画数")
for nm in ("u9b3c-05", "u8fb6-05", "u65e5", "u7530", "u9e7f-05"):
    flat = q(glyph_extend.return_bone, nm)
    n_st = len(ids_anal.stroke_list(flat))
    b0 = q(cavity.ink_boxes, flat, False, False)
    b1 = q(cavity.ink_boxes, flat, False, True)
    zero0 = sum(1 for b in b0 if all(abs(v) < 1e-9 for v in b))
    zero1 = sum(1 for b in b1 if all(abs(v) < 1e-9 for v in b))
    print(f"   {nm:10s} 笔画{n_st:2d}  split=False→{len(b0):2d}盒   split=True→{len(b1):2d}盒  零框 {zero0}/{zero1}")

# ② divide_boundary 逐笔有没有零框/退化框
print("\n② divide_boundary 全库抽样 (找零框)")
bad = 0; total = 0
for nm in ("u9b3c-05","u8fb6-05","u5fc3","u5fc5","u5ef4","u9e7f-05","u65e5","u7530","u4e5c","u5c38","u2cea0","u53c9"):
    flat = q(glyph_extend.return_bone, nm)
    for s in ids_anal.stroke_list(flat):
        total += 1
        for b in q(so.divide_boundary, s):
            if all(abs(v) < 1e-9 for v in (b.x1,b.y1,b.x2,b.y2)) or b.x2<=b.x1 or b.y2<=b.y1:
                bad += 1
                print(f"    问题框 {nm} {s}")
print(f"   笔画 {total} 支, 问题框 {bad} 个")

# ③ split=True 时腔是否仍然不压笔画
print("\n③ split=True: 腔 vs 笔画盒相交")
def inter(a,b):
    return max(0.0,min(a[2],b[2])-max(a[0],b[0]))*max(0.0,min(a[3],b[3])-max(a[1],b[1]))
f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)
for op, cont in (("⿴","u9b3c"),("⿴","u8001"),("⿴","u65e5"),("⿸","u5382"),("⿺","u8fb6")):
    flat = q(glyph_extend.return_bone, cont+"-05")
    ink = q(cavity.ink_boxes, flat, False, False)   # 用未切分的墨迹盒做"真实墨迹"参照
    for sp in (False, True):
        fs, outer = q(cavity.faces, flat, 0.75, 5.0, sp)
        cands = cavity.rank_faces(fs, op)
        cav = None
        if cands:
            cav = max(cands, key=lambda f:(f["ins"][2]-f["ins"][0])*(f["ins"][3]-f["ins"][1]))["ins"]
        hit = sum(1 for b in ink if cav and inter(cav,b) > 1.0)
        print(f"   {op}{cont} split={str(sp):5s} 面{len(fs):2d} 候选{len(cands):2d} 外框{f1(outer)} 腔{f1(cav)} 压笔画{hit}")
