# -*- coding: utf-8 -*-
"""
对比: 用"笔画 bbox" 还是用"笔画真实轮廓" 求空腔

你手上其实已经有轮廓 —— stroke_outer.generate_border(stro) 返回的就是轮廓点列,
只是 strokic_boundary 又对它取了 bbox。这里直接拿轮廓用。

指标: 把设计者真实放置的内部件矩形, 分别用两种障碍模型测"覆盖率"
      (bbox 模型下覆盖率高 = 误判碰撞 = 空腔丢失)
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
    _c = _line.split(" | ")
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
from stroke_outer import generate_border, strokic_boundary  # noqa: E402


def flatten(name):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return glyph_extend.return_bone(name)


def outlines(data):
    """每笔画 → 真实轮廓点列 (generate_border)"""
    out = []
    for seg in data.split("$"):
        if seg.strip().split(":")[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        try:
            pts = generate_border(seg)
            pl = [(float(p.x), float(p.y)) for p in pts]
            if len(pl) >= 3:
                out.append(pl)
        except Exception:
            pass
    return out


def bbox_of(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def coverage(rect, polys, model="poly", N=200):
    """rect 内被障碍覆盖的面积占比"""
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
            bx1, by1, bx2, by2 = bbox_of(poly)
            hit |= ((pts[:, 0] >= bx1) & (pts[:, 0] <= bx2) &
                    (pts[:, 1] >= by1) & (pts[:, 1] <= by2))
    return hit.mean()


def cavity_poly(polys, N=300):
    """用真实轮廓求极大空矩形 (栅格 + 单调栈)"""
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    X1, Y1, X2, Y2 = min(xs), min(ys), max(xs), max(ys)
    gx = np.linspace(X1, X2, N)
    gy = np.linspace(Y1, Y2, N)
    XX, YY = np.meshgrid(gx, gy)
    pts = np.column_stack([XX.ravel(), YY.ravel()])
    blocked = np.zeros(len(pts), dtype=bool)
    for poly in polys:
        blocked |= Path(poly).contains_points(pts)
    blocked = blocked.reshape(N, N)
    heights = np.zeros(N, dtype=int)
    best = None
    for j in range(N):
        heights = np.where(blocked[j], 0, heights + 1)
        stack = []
        for i in range(N + 1):
            h = int(heights[i]) if i < N else 0
            start = i
            while stack and stack[-1][1] >= h:
                x0, hh = stack.pop()
                if hh > 0:
                    area = (i - x0) * hh
                    if best is None or area > best[0]:
                        best = (area, x0, j - hh + 1, i, j + 1)
                start = x0
            stack.append((start, h))
    if not best:
        return None, (X1, Y1, X2, Y2)
    _, i0, j0, i1, j1 = best
    return (gx[i0], gy[j0], gx[min(i1, N - 1)], gy[min(j1, N - 1)]), (X1, Y1, X2, Y2)


def desmos(r):
    if r is None:
        return "None"
    x1, y1, x2, y2 = r
    return (f"[({x1:.1f},{y1:.1f}),({x2:.1f},{y1:.1f}),"
            f"({x2:.1f},{y2:.1f}),({x1:.1f},{y2:.1f})]")


CASES = [
    ("衣-05", "u8863-05", (7, 40, 192, 120), "衮·公"),
    ("行-05", "u884c-05", (55, 0, 145, 200), "衙·吾"),
    ("虍-10", "u864d-10", (42, 90, 185, 145), "慮·田"),
    ("鹿-11", "u9e7f-11", (20, 45, 200, 200), "塵·土"),
    ("麻-05", "u9ebb-05-var-003", (25, -5, 200, 200), "摩·手"),
    ("气-05", "u6c14-05", None, "氕·丿"),
]

print("=" * 88)
print("① 把设计者真实放置的内部件矩形, 用两种障碍模型测覆盖率")
print("   覆盖率高 = 误判为该位置被占满 (bbox 模型的毛病)")
print("=" * 88)
print(f"  {'容器':<8} {'真实放置内部件':<12} {'bbox模型':>9} {'轮廓模型':>9}  差")
print("  " + "-" * 72)
for label, name, inner, note in CASES:
    fl = flatten(name)
    if not fl:
        print(f"  {label}: 展平失败")
        continue
    pols = outlines(fl)
    if not pols or inner is None:
        continue
    cb = coverage(inner, pols, "bbox")
    cp = coverage(inner, pols, "poly")
    print(f"  {label:<8} {note:<12} {cb*100:>8.1f}% {cp*100:>8.1f}%  "
          f"{(cb-cp)*100:>+6.1f}pp")

print()
print("=" * 88)
print("② 用真实轮廓求出的空腔 (栅格300 + 单调栈)")
print("=" * 88)
for label, name, inner, note in CASES:
    fl = flatten(name)
    if not fl:
        continue
    pols = outlines(fl)
    if not pols:
        continue
    cav, outer = cavity_poly(pols)
    w = (cav[2] - cav[0]) if cav else 0
    h = (cav[3] - cav[1]) if cav else 0
    print(f"\n  {label}  ({name})")
    print(f"    外框     {desmos(outer)}")
    print(f"    轮廓空腔 {desmos(cav)}   {w:.0f}x{h:.0f} 面积={w*h:.0f}")
    if inner:
        iw, ih = inner[2] - inner[0], inner[3] - inner[1]
        print(f"    真实放置 {desmos(inner)}   {iw}x{ih} 面积={iw*ih}  ({note})")
