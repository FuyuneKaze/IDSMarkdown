# -*- coding: utf-8 -*-
"""扫 divide_boundary: 全零框/退化框出现在哪种笔画上"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, stroke_outer as so  # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


GLYPHS = ["u9b3c", "u9b3c-05", "u8fb6", "u8fb6-05", "u5fc3", "u5fc5",
          "u5ef4", "u9e7f", "u65e5", "u7530", "u4e5c", "u5c38"]
bad_total = 0
for nm in GLYPHS:
    flat = q(glyph_extend.return_bone, nm)
    for s in ids_anal.stroke_list(flat):
        tp = s.split(":")[0]
        boxes = q(so.divide_boundary, s)
        pts = q(so.stroke_point, s)[0]
        info = []
        for b in boxes:
            qd = (float(b.x1), float(b.y1), float(b.x2), float(b.y2))
            zero = all(abs(v) < 1e-9 for v in qd)
            degen = (qd[2] <= qd[0] + 1e-9) or (qd[3] <= qd[1] + 1e-9)
            if zero or degen:
                bad_total += 1
                info.append(f"{'全零' if zero else '退化'} {tuple(round(v,1) for v in qd)}")
        if info:
            print(f"{nm:9s} 类型{tp:2s} 采样{len(pts):2d}点 分{len(boxes)}段  "
                  f"坐标首末 ({pts[0].x:.0f},{pts[0].y:.0f})→({pts[-1].x:.0f},{pts[-1].y:.0f})  "
                  + " | ".join(info))
            print(f"          stroke: {s}")
print(f"\n问题框合计 {bad_total} 个")
