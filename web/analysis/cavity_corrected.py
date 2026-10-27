# -*- coding: utf-8 -*-
"""
修正版: 内部件的"真实落位"必须解析嵌套矩形

用 return_bone(name, geom=(父矩形,...)) 把内部件按其被引用的矩形展开,
得到它在合成字里的真实 footprint, 再与容器空腔比对。
"""
import sys, io, contextlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
from matplotlib.path import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = line.split(" | ") if False else _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())


def fast_get(t, datas=None, **kw):
    best, bd = -1, ""
    n = len(t)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(t[i:j])
            if h is not None and h[0] > best:
                best, bd = h[0], h[1]
    return bd


glyph_extend.get_data = fast_get
from stroke_outer import generate_border  # noqa: E402


def flatten(name, rect=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if rect is None:
            return glyph_extend.return_bone(name)
        g = ((str(rect[0]), str(rect[1]), str(rect[2]), str(rect[3])), (0, 0), (0, 0))
        return glyph_extend.return_bone(name, g)


def outlines(data):
    out = []
    for seg in data.split("$"):
        if seg.strip().split(":")[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        try:
            pl = [(float(p.x), float(p.y)) for p in generate_border(seg)]
            if len(pl) >= 3:
                out.append(pl)
        except Exception:
            pass
    return out


def bbox_of_polys(polys):
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def coverage(rect, polys, model="poly", N=200):
    x1, y1, x2, y2 = rect
    gx = np.linspace(x1, x2, N)
    gy = np.linspace(y1, y2, N)
    XX, YY = np.meshgrid(gx, gy)
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    hit = np.zeros(len(pts), dtype=bool)
    for poly in polys:
        if model == "poly":
            hit |= Path(poly).contains_points(pts)
        else:
            bx1, by1, bx2, by2 = bbox_of_polys([poly])
            hit |= ((pts[:, 0] >= bx1) & (pts[:, 0] <= bx2) &
                    (pts[:, 1] >= by1) & (pts[:, 1] <= by2))
    return hit.mean()


def cavity(polys, N=300):
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    X1, Y1, X2, Y2 = min(xs), min(ys), max(xs), max(ys)
    gx = np.linspace(X1, X2, N); gy = np.linspace(Y1, Y2, N)
    XX, YY = np.meshgrid(gx, gy)
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    bl = np.zeros(len(pts), dtype=bool)
    for poly in polys:
        bl |= Path(poly).contains_points(pts)
    bl = bl.reshape(N, N)
    hts = np.zeros(N, dtype=int); best = None
    for j in range(N):
        hts = np.where(bl[j], 0, hts + 1)
        st = []
        for i in range(N + 1):
            h = int(hts[i]) if i < N else 0
            s = i
            while st and st[-1][1] >= h:
                x0, hh = st.pop()
                if hh > 0:
                    a = (i - x0) * hh
                    if best is None or a > best[0]:
                        best = (a, x0, j - hh + 1, i, j + 1)
                s = x0
            st.append((s, h))
    if not best:
        return None
    _, i0, j0, i1, j1 = best
    return (gx[i0], gy[j0], gx[min(i1, N - 1)], gy[min(j1, N - 1)])


def desmos(r):
    x1, y1, x2, y2 = r
    return (f"[({x1:.1f},{y1:.1f}),({x2:.1f},{y1:.1f}),"
            f"({x2:.1f},{y2:.1f}),({x1:.1f},{y2:.1f})]")


# (标签, 容器变体, 内部件名, 内部件被引用的父矩形, 说明)
CASES = [
    ("衣-05", "u8863-05", "u516c-jn", (7, 40, 192, 120), "衮·公"),
    ("行-05", "u884c-05", "u543e-j", (55, 0, 145, 200), "衙·吾"),
    ("虍-10", "u864d-10", "u7530-j", (42, 90, 185, 145), "慮·田"),
    ("鹿-11", "u9e7f-11", "u571f-04@7", (20, 45, 200, 200), "塵·土"),
    ("麻-05", "u9ebb-05-var-003", "u624b-04", (25, -5, 200, 200), "摩·手"),
]

print("=" * 90)
print("容器空腔 vs 内部件【真实 footprint】(已解析嵌套矩形)")
print("=" * 90)

for label, cname, iname, irect, note in CASES:
    cfl = flatten(cname)
    if not cfl:
        print(f"\n{label}: 容器展平失败")
        continue
    cpolys = outlines(cfl)
    if not cpolys:
        print(f"\n{label}: 容器无轮廓")
        continue

    ifl = flatten(iname, irect)
    fp = None
    if ifl:
        ipolys = outlines(ifl)
        if ipolys:
            fp = bbox_of_polys(ipolys)

    cav = cavity(cpolys)
    cbox = bbox_of_polys(cpolys)

    print(f"\n{'─'*90}")
    print(f"{label}   ({note})")
    print(f"{'─'*90}")
    print(f"  容器外框   {desmos(cbox)}")
    print(f"  容器空腔   {desmos(cav)}"
          f"   {cav[2]-cav[0]:.0f}x{cav[3]-cav[1]:.0f}")
    if fp:
        print(f"  内部件真实 {desmos(fp)}   {fp[2]-fp[0]:.0f}x{fp[3]-fp[1]:.0f}")
        inside = (fp[0] >= cav[0] - 2 and fp[1] >= cav[1] - 2 and
                  fp[2] <= cav[2] + 2 and fp[3] <= cav[3] + 2)
        print(f"  → footprint 是否落在空腔内: "
              f"{'是 ✓' if inside else '否 (超出空腔)'}")
        cb = coverage(fp, cpolys, "bbox")
        cp = coverage(fp, cpolys, "poly")
        print(f"  → 该处容器笔画覆盖率: bbox模型 {cb*100:.1f}%  轮廓模型 {cp*100:.1f}%"
              f"   (差 {(cb-cp)*100:+.1f}pp)")
    else:
        print(f"  内部件 {iname} 展平失败/无轮廓")
