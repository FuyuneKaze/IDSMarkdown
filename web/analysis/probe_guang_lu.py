# -*- coding: utf-8 -*-
"""⿸广粤 / ⿸鹿丶: 把全部面、候选、选中腔、以及和笔画盒的相交情况摊开"""
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


def inter(a, b):
    return (max(0.0, min(a[2], b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[3], b[3]) - max(a[1], b[1])))


f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)

for op, cont, inner in (("⿸", "u7592", "u7ca4"), ("⿸", "u9e7f", "u4e36")):
    cname = cont + "-05"
    flat = q(glyph_extend.return_bone, cname)
    faces, outer = q(cavity.faces, flat)
    cands = cavity.rank_faces(faces, op)
    boxes = []
    for s in ids_anal.stroke_list(flat):
        try:
            bb = stroke_outer.strokic_boundary(s, False)
            if bb.x2 > bb.x1 and bb.y2 > bb.y1:
                boxes.append((bb.x1, bb.y1, bb.x2, bb.y2))
        except Exception:
            pass
    print(f"===== {op}{cont}+{inner}   容器 {cname}: {len(ids_anal.stroke_list(flat))} 笔, "
          f"外框 {f1(outer)} =====")
    print(f"  面 {len(faces)} 个 (按面积排):")
    for f in sorted(faces, key=lambda z: -z["area"]):
        b = f["box"]
        bb_area = (b[2]-b[0]) * (b[3]-b[1])
        need = cavity.NEED[op]
        ok = need <= (cavity.ALL_EDGES - f["open"])
        ins = cavity.inscribed(f["rects"])
        ins_a = 0 if not ins else (ins[2]-ins[0])*(ins[3]-ins[1])
        print(f"    box {f1(b)} 填充{f['area']/bb_area*100:3.0f}% 开口={''.join(sorted(f['open'])) or '无':4s} "
              f"{'✓合格' if ok else ' 不合格'}  面面积{f['area']:6.0f}  ins {f1(ins)} ins面积{ins_a:6.0f}")
    print(f"  → 候选 {len(cands)} 个")
    # 复现 surround 的选择
    cav = None
    if cands:
        cav = max(cands, key=lambda f: (f["ins"][2]-f["ins"][0])*(f["ins"][3]-f["ins"][1]))["ins"]
    if cav is None and faces:
        big = max(faces, key=lambda f: f["area"])
        cav = cavity.inscribed(big["rects"]) or big["box"]
    print(f"  → 选中腔 {f1(cav)}")
    hit = [(bx, inter(cav, bx)) for bx in boxes if inter(cav, bx) > 1.0]
    print(f"  → 与笔画盒相交 {len(hit)} 个")
    for bx, a in hit[:5]:
        print(f"      相交 {a:6.0f}  vs 盒 {f1(bx)}")
    print()
