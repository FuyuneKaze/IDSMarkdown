# -*- coding: utf-8 -*-
"""⿺/⿸ 的腔: 面 vs 外接框 vs 面内最大内接矩形 (= 应该拿来安放的那块)"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, cavity                        # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def r1(bx):
    return "None" if not bx else "(%5.1f,%5.1f,%5.1f,%5.1f)" % tuple(bx)


def show(op, name):
    flat = q(glyph_extend.return_bone, name)
    fs, outer = q(cavity.faces, flat)
    cands = cavity.rank_faces(fs, op)
    print(f"=== {op} 容器 {name}  障碍 {len(q(cavity.ink_boxes, flat))}   "
          f"面 {len(fs)}   候选 {len(cands)} ===")
    for i, f in enumerate(cands):
        b = f["box"]
        bb = (b[2] - b[0]) * (b[3] - b[1])
        ins = cavity.inscribed(f["rects"])
        print(f"  [{i}] 开口={''.join(sorted(f['open'])) or '无':4s} 填充率 "
              f"{f['area']/bb*100:3.0f}%")
        print(f"      面外接框(现在用的)  {r1(b)}")
        print(f"      面内最大内接矩形     {r1(ins)}"
              f"   {'' if not ins else '(%.0f x %.0f = %.0f)' % (ins[2]-ins[0], ins[3]-ins[1], (ins[2]-ins[0])*(ins[3]-ins[1]))}")
        print(f"      选它会安放在         {r1(cavity.inscribed(f['rects']) or b)}")
    print()


for op, name in [("⿺", "u8fb6-05"), ("⿺", "u5ef4"), ("⿺", "u9b3c"),
                 ("⿸", "u5382-05"), ("⿺", "u200ca"), ("⿴", "u65e5")]:
    show(op, name)
