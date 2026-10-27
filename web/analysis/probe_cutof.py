# -*- coding: utf-8 -*-
"""复现: type3/4 笔画截断到前半后, 每个障碍盒变成什么, 面/腔怎么变"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity, stroke_outer  # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)


def box_of(border):
    xs = [p.x for p in border]
    ys = [p.y for p in border]
    return (min(xs), min(ys), max(xs), max(ys))


for name in ("u9b3c-05", "u9b3c"):
    flat = q(glyph_extend.return_bone, name)
    strokes = ids_anal.stroke_list(flat)
    print(f"===== {name}: {len(strokes)} 笔 =====")
    for s in strokes:
        tp = s.split(":")[0]
        full = q(stroke_outer.generate_border, s)[0]            # 不截断
        trunc = q(stroke_outer.generate_border, s, stroke_outer.bone_shape_function, [8])[0]
        used = q(stroke_outer.strokic_boundary, s, False)       # 实际进障碍的
        ubox = (used.x1, used.y1, used.x2, used.y2) if (used.x2 > used.x1 and used.y2 > used.y1) else None
        mark = "  ← 被截断!" if tp in ("3", "4") else ""
        print(f"  类型{tp:2s} 全笔盒 {f1(box_of(full))}  截断盒 {f1(box_of(trunc))}  "
              f"实际用 {f1(ubox)}{mark}")
    faces, outer = q(cavity.faces, flat)
    cands = cavity.rank_faces(faces, "⿴")
    print(f"  外框 {f1(outer)}  面 {len(faces)}  ⿴候选 {len(cands)}")
    for f in sorted(faces, key=lambda z: -z["area"]):
        b = f["box"]
        bb = (b[2]-b[0])*(b[3]-b[1])
        ok = cavity.NEED["⿴"] <= (cavity.ALL_EDGES - f["open"])
        ins = cavity.inscribed(f["rects"])
        print(f"    box {f1(b)} 填充{f['area']/bb*100:3.0f}% 开口={''.join(sorted(f['open'])) or '无':4s} "
              f"{'✓' if ok else ' '} 面面积{f['area']:6.0f} ins {f1(ins)}")
    print()
