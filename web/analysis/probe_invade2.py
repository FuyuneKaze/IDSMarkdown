import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal, stroke_outer
buf = io.StringIO()
def inter(a, b):
    return (max(0.0, min(a[2], b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[3], b[3]) - max(a[1], b[1])))
fmt = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)
for expr, args in (("⿴", ["u9b3c","u53e3"]), ("⿴", ["u8001","u53e3"]),
                   ("⿴", ["u65e5","u4e00"]), ("⿴", ["u7530","u4e00"]),
                   ("⿸", ["u5382","u4eba"]), ("⿺", ["u8fb6","u5bf8"])):
    with contextlib.redirect_stdout(buf):
        out = ids_anal.IDS(expr, list(args))
    b = ids_anal.LAST_BOXES
    # 容器笔画盒
    with contextlib.redirect_stdout(buf):
        flat1 = __import__("glyph_extend").return_bone(args[0] + "-05")
    boxes = []
    for s in ids_anal.stroke_list(flat1):
        try:
            bb = stroke_outer.strokic_boundary(s, False)
            if bb.x2 > bb.x1 and bb.y2 > bb.y1:
                boxes.append((bb.x1, bb.y1, bb.x2, bb.y2))
        except Exception:
            pass
    hit = [(bx, inter(b["cavity"], bx)) for bx in boxes
           if b["cavity"] and inter(b["cavity"], bx) > 1.0]
    print(f"{expr}{args[0]}+{args[1]}  候选{len(b['candidates'])}  腔 {fmt(b['cavity'])}")
    print(f"    与笔画盒相交: {len(hit)} 个" + ("" if not hit else "  ← 仍在侵入!"))
    for bx, a in hit[:4]:
        print(f"      相交面积 {a:.0f}  vs 盒 {fmt(bx)}")
