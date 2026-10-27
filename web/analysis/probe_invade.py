# -*- coding: utf-8 -*-
"""腔为什么会压进字里: 逐笔查障碍盒 (有没有笔画被丢掉/盒过小), 再和腔对撞"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity              # noqa: E402
import stroke_outer                                # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def inter(a, b):
    return (max(0.0, min(a[2], b[2]) - max(a[0], b[0])) *
            max(0.0, min(a[3], b[3]) - max(a[1], b[1])))


for name, op in (("u9b3c-05", "⿴"), ("u8001-05", "⿴"), ("u9b3c", "⿴"), ("u8001", "⿴")):
    flat = q(glyph_extend.return_bone, name)
    strokes = ids_anal.stroke_list(flat)
    print(f"===== {name} ({op})  直绘笔画 {len(strokes)} 笔 =====")

    ok, dropped = [], []
    for s in strokes:
        p = s.split(":")
        try:
            b = stroke_outer.strokic_boundary(s, False)
            box = (b.x1, b.y1, b.x2, b.y2) if (b.x2 > b.x1 and b.y2 > b.y1) else None
        except Exception as e:
            box = None
        label = f"类型{p[0]:2s} 点{len(p[3:])//2}  {s[:44]}"
        if box:
            ok.append((label, box))
            print(f"  ✓ {label}  → ({box[0]:6.1f},{box[1]:6.1f})-({box[2]:6.1f},{box[3]:6.1f})")
        else:
            dropped.append(label)
            print(f"  × {label}  → 盒无效, 被丢掉!")

    print(f"  障碍盒 {len(ok)} 个, 丢掉 {len(dropped)} 个")
    fs, outer = q(cavity.faces, flat)
    cands = cavity.rank_faces(fs, op)
    print(f"  面 {len(fs)} 个, {op} 候选 {len(cands)} 个")
    for i, f in enumerate(cands):
        ins = f["ins"]
        hits = [(lb, bx) for lb, bx in ok if inter(ins, bx) > 1.0]
        print(f"    [{i}] face_box={tuple(round(v,1) for v in f['box'])}")
        print(f"         ins     ={tuple(round(v,1) for v in ins)}  填充率 {f['area']/((f['box'][2]-f['box'][0])*(f['box'][3]-f['box'][1]))*100:.0f}%")
        print(f"         与 ins 相交的笔画盒: {len(hits)} 个")
        for lb, bx in hits[:6]:
            print(f"            ! {lb}  盒({bx[0]:.0f},{bx[1]:.0f})-({bx[2]:.0f},{bx[3]:.0f})")
    if not cands:
        cav, _ = ids_anal.enclosure_cavity(flat)
        hits = [(lb, bx) for lb, bx in ok if inter(cav, bx) > 1.0]
        print(f"  0 候选 → 兜底 max_empty_rect 腔 = {tuple(round(v,1) for v in cav)}")
        print(f"     与腔相交的笔画盒: {len(hits)} 个")
        for lb, bx in hits[:6]:
            print(f"        ! {lb}  盒({bx[0]:.0f},{bx[1]:.0f})-({bx[2]:.0f},{bx[3]:.0f})")
    print()
