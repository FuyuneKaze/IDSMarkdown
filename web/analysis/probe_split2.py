import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend, ids_anal, cavity, stroke_outer as so
buf = io.StringIO()
def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)

# ① 不切分类型必须与 strokic_boundary 逐位相同
print("① divide_boundary(单段) vs strokic_boundary")
worst = 0.0; n = 0
GL = ["u9b3c","u9b3c-05","u8fb6","u5fc3","u5fc5","u5ef4","u9e7f","u65e5",
      "u7530","u4e5c","u5c38","u2cea0","u53c9","u6728","u4eba","u96e8","u756a"]
for nm in GL:
    flat = q(glyph_extend.return_bone, nm)
    for s in ids_anal.stroke_list(flat):
        bs = q(so.divide_boundary, s)
        if len(bs) != 1:
            continue
        b0 = q(so.strokic_boundary, s, False)
        b1 = bs[0]
        d = max(abs(b0.x1-b1.x1), abs(b0.y1-b1.y1), abs(b0.x2-b1.x2), abs(b0.y2-b1.y2))
        worst = max(worst, d); n += 1
print(f"   对比 {n} 支不切分笔画, 最大偏差 {worst:.3g}")

# ② 切开后的段: 相邻段是否重叠 (pad 是否生效)
print("\n② 切分段的相邻重叠")
for nm in ("u9b3c-05", "u9e7f-05", "u9e7f"):
    flat = q(glyph_extend.return_bone, nm)
    for s in ids_anal.stroke_list(flat):
        bs = q(so.divide_boundary, s)
        if len(bs) < 2:
            continue
        a, b = bs[0], bs[1]
        sep = (min(a.x2,b.x2)-max(a.x1,b.x1) > 0) and (min(a.y2,b.y2)-max(a.y1,b.y1) > 0)
        print(f"   {nm:10s} 类型{s.split(':')[0]} 段0 ({a.x1:.0f},{a.y1:.0f})-({a.x2:.0f},{a.y2:.0f})"
              f"  段1 ({b.x1:.0f},{b.y1:.0f})-({b.x2:.0f},{b.y2:.0f})  重叠={sep}")

# ③ 默认 SPLIT 下: 零框 / 腔压笔画
print("\n③ 默认配置 (SPLIT=%s)" % cavity.SPLIT)
def inter(a,b):
    return max(0.0,min(a[2],b[2])-max(a[0],b[0]))*max(0.0,min(a[3],b[3])-max(a[1],b[1]))
f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)
zero = 0; tot = 0
for nm in GL:
    flat = q(glyph_extend.return_bone, nm)
    for b in q(cavity.ink_boxes, flat, False, True):
        tot += 1
        if all(abs(v) < 1e-9 for v in b): zero += 1
print(f"   障碍盒 {tot} 个, 全零框 {zero} 个")
for op, cont, inner in (("⿴","u9b3c","u53e3"),("⿴","u8001","u53e3"),("⿴","u65e5","u4e00"),
                        ("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),("⿸","u9e7f","u4e36")):
    with contextlib.redirect_stdout(buf):
        out = ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    flat1 = q(glyph_extend.return_bone, cont+"-05")
    ink = q(cavity.ink_boxes, flat1, False, False)     # 真实墨迹参照(不切分)
    hit = sum(1 for x in ink if b["cavity"] and inter(b["cavity"], x) > 1.0)
    print(f"   {op}{cont}+{inner}: 候选{len(b['candidates'])} 腔{f1(b['cavity'])} 内部件盒{f1(b['components'][1])} 压笔画{hit}")
