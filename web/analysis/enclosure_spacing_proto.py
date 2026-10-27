# -*- coding: utf-8 -*-
"""
① bbox_adjust 的扩张量到底是多少 (角度 → dh/dw)
② 把 bbox_adjust 的"角度相关扩张"用来求包围空腔, 看是否自动给出正确间距
③ 顺手统计: 被当作包围外框的字里, 有多少存在 -05 变体 (fallback 缺口)
"""
import sys, io, os, math, contextlib
from collections import Counter
import numpy as np

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

# ============================================================
print("=" * 78)
print("① bbox_adjust 的扩张量:  dh = 20*(pi/3-|bang|)^2   dw = 20*(pi/3-|pi/2-bang|)^2")
print("=" * 78)
print(f"  {'角度':>7} {'bang(rad)':>10} {'dh (纵向扩)':>12} {'dw (横向扩)':>12}  生效分支")
for deg in [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]:
    bang = math.radians(deg)
    dh = 20 * (math.pi / 3 - abs(bang)) ** 2
    dw = 20 * (math.pi / 3 - abs(math.pi / 2 - bang)) ** 2
    if bang <= math.pi / 6:
        br = "横 → 扩 y (±dh)"
    elif bang >= math.pi / 3:
        br = "竖 → 扩 x (±dw)"
    else:
        br = "斜 → 不扩"
    print(f"  {deg:>6}° {bang:>10.4f} {dh:>12.2f} {dw:>12.2f}  {br}")
print(f"\n  临界角 pi/6={math.degrees(math.pi/6):.1f}°  pi/3={math.degrees(math.pi/3):.1f}°")
print(f"  最大扩张 (正横/正竖): {20*(math.pi/3)**2:.2f} px")
print(f"  临界处扩张:            {20*(math.pi/6)**2:.2f} px")


# ============================================================
def flatten(name, rect=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if rect is None:
            return glyph_extend.return_bone(name)
        g = ((str(rect[0]), str(rect[1]), str(rect[2]), str(rect[3])), (0, 0), (0, 0))
        return glyph_extend.return_bone(name, g)


def stroke_boxes_angles(data):
    """每笔画: (bbox, 角度 bang) —— 与 bbox_adjust 的算法一致"""
    out = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        try:
            xs = [float(v) for v in p[3::2]]
            ys = [float(v) for v in p[4::2]]
        except ValueError:
            continue
        if len(xs) < 2 or len(ys) < 2:
            continue
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        bang = math.pi / 2 if w == 0 else math.atan(h / w)
        out.append(((min(xs), min(ys), max(xs), max(ys)), bang))
    return out


def adjust(box, bang, smin=1.0, smax=1.0):
    """复刻 bbox_adjust 的单笔画分支"""
    x1, y1, x2, y2 = box
    dh = 20 * (math.pi / 3 - abs(bang)) ** 2
    dw = 20 * (math.pi / 3 - abs(math.pi / 2 - bang)) ** 2
    if bang <= math.pi / 6:
        return (x1, y1 - dh * smin, x2, y2 + dh * smax)
    if bang >= math.pi / 3:
        return (x1 - dw * smin, y1, x2 + dw * smax, y2)
    return (x1, y1, x2, y2)


def maximal_empty_rects(box, rects):
    X1, Y1, X2, Y2 = box
    Ls = sorted({X1} | {min(max(r[2], X1), X2) for r in rects})
    Rs = sorted({X2} | {min(max(r[0], X1), X2) for r in rects})
    uniq = {}
    for L in Ls:
        for R in Rs:
            if R <= L:
                continue
            bl = sorted((max(r[1], Y1), min(r[3], Y2))
                        for r in rects if r[0] < R and r[2] > L and r[1] < Y2 and r[3] > Y1)
            gaps, cur = [], Y1
            for b0, b1 in bl:
                if b0 > cur:
                    gaps.append((cur, b0))
                if b1 > cur:
                    cur = b1
            if cur < Y2:
                gaps.append((cur, Y2))
            for g0, g1 in gaps:
                uniq[(round(L, 2), round(g0, 2), round(R, 2), round(g1, 2))] = (L, g0, R, g1)
    return list(uniq.values())


def desmos(r):
    x1, y1, x2, y2 = r
    return (f"[({x1:.1f},{y1:.1f}),({x2:.1f},{y1:.1f}),"
            f"({x2:.1f},{y2:.1f}),({x1:.1f},{y2:.1f})]")


CASES = [
    ("衣-05", "u8863-05", "u516c-jn", (7, 40, 192, 120), "衮·公"),
    ("行-05", "u884c-05", "u543e-j", (55, 0, 145, 200), "衙·吾"),
    ("虍-10", "u864d-10", "u7530-j", (42, 90, 185, 145), "慮·田"),
    ("鹿-11", "u9e7f-11", "u571f-04@7", (20, 45, 200, 200), "塵·土"),
    ("麻-05", "u9ebb-05-var-003", "u624b-04", (25, -5, 200, 200), "摩·手"),
    ("广-05", "u5e7f-05", None, None, "参考·纯半包围"),
    ("囗-j", "u56d7-j", None, None, "参考·全包围"),
]

print()
print("=" * 78)
print("② 三种障碍模型求包围空腔, 对比设计者真实放置")
print("=" * 78)

for label, cname, iname, irect, note in CASES:
    cfl = flatten(cname)
    if not cfl:
        print(f"\n{label}: 展平失败")
        continue
    sa = stroke_boxes_angles(cfl)
    if not sa:
        print(f"\n{label}: 无笔画")
        continue
    raw = [b for b, _ in sa]
    adj = [adjust(b, a) for b, a in sa]

    for boxes in (raw, adj):
        pass

    def outer_of(bs):
        return (min(b[0] for b in bs), min(b[1] for b in bs),
                max(b[2] for b in bs), max(b[3] for b in bs))

    # 三种模型: 原始 bbox / bbox_adjust / 再放大 1.5 倍
    adj15 = [adjust(b, a, 1.5, 1.5) for b, a in sa]

    r_raw = maximal_empty_rects(outer_of(raw), raw)
    r_adj = maximal_empty_rects(outer_of(adj), adj)
    r_a15 = maximal_empty_rects(outer_of(adj15), adj15)

    def top(rs):
        return max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))

    print(f"\n{'─'*78}")
    print(f"{label}   ({note})   笔画 {len(sa)}")
    print(f"{'─'*78}")
    m = top(r_raw)
    print(f"  原始bbox   空腔 {desmos(m)}  {(m[2]-m[0]):.0f}x{(m[3]-m[1]):.0f}")
    m = top(r_adj)
    print(f"  +bbox_adj  空腔 {desmos(m)}  {(m[2]-m[0]):.0f}x{(m[3]-m[1]):.0f}")
    m = top(r_a15)
    print(f"  +adj×1.5   空腔 {desmos(m)}  {(m[2]-m[0]):.0f}x{(m[3]-m[1]):.0f}")
    if iname and irect:
        ifl = flatten(iname, irect)
        if ifl:
            ip = [(float(v) for v in [])]
            xs, ys = [], []
            for seg in ifl.split("$"):
                p = seg.strip().split(":")
                if p[0] not in ("1", "2", "3", "4", "6", "7"):
                    continue
                try:
                    xs += [float(v) for v in p[3::2]]
                    ys += [float(v) for v in p[4::2]]
                except ValueError:
                    pass
            if xs:
                fp = (min(xs), min(ys), max(xs), max(ys))
                print(f"  真实放置   内部件 {desmos(fp)}  "
                      f"{(fp[2]-fp[0]):.0f}x{(fp[3]-fp[1]):.0f}")
