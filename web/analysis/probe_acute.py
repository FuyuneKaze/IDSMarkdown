# -*- coding: utf-8 -*-
"""acute_divide 实测: 在真实的 竖弯钩 笔画上它给出什么"""
import sys, io, contextlib, math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, stroke_outer as so            # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def turn_angles(pts):
    """每个内点的转角 (0 = 直, π/2 = 直角, π = 折回)"""
    out = []
    for i in range(1, len(pts) - 1):
        v1 = (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
        v2 = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        n1 = math.hypot(*v1) or 1e-9
        n2 = math.hypot(*v2) or 1e-9
        c = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
        out.append(math.acos(max(-1.0, min(1.0, c))))
    return out


for name in ("u8fb6-05", "u5ef4", "u8fb6"):
    flat = q(glyph_extend.return_bone, name)
    strokes = [s for s in flat.split("$") if s.split(":")[0] in ("1", "2", "3", "4", "6", "7")]
    print(f"=== {name}: {len(strokes)} 笔 ===")
    for s in strokes:
        kind = s.split(":")[0]
        try:
            pts_obj, _n, _e = q(so.stroke_point, s)
        except Exception as e:
            print(f"  类型{kind}: stroke_point 失败 {type(e).__name__}")
            continue
        pts = [(float(p.x), float(p.y)) for p in pts_obj]
        if len(pts) < 4:
            continue
        ta = turn_angles(pts)
        kmax = max(range(len(ta)), key=lambda i: ta[i]) + 1
        try:
            d = q(so.acute_divide, tuple(pts_obj))
            d = None if d is None or (isinstance(d, float) and math.isnan(d)) else int(d)
        except Exception as e:
            d = f"异常 {type(e).__name__}: {e}"
        print(f"  类型{kind} {len(pts)} 点   最大转角 {max(ta)*180/math.pi:5.1f}° @内点{kmax}"
              f"   累计转角 {sum(ta)*180/math.pi:6.1f}°   acute_divide → {d}")
    print()
