# -*- coding: utf-8 -*-
"""
验证「按轴决定映射基准」的想法

① 各部件的包围盒到底是不是"满幅" (对比 [0,200] 与 [5,195] 两个阈值)
② 三种映射基准下, 内部件落在空腔里的实际尺寸, 与设计者真实放置对比
"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend
import stroke_outer as SO


def flatten(name, rect=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            if rect is None:
                return glyph_extend.return_bone(name)
            g = ((str(rect[0]), str(rect[1]), str(rect[2]), str(rect[3])),
                 (0, 0), (0, 0))
            return glyph_extend.return_bone(name, g)
        except Exception:
            return ""


def strokes(g):
    return [s.strip() for s in g.split("$")
            if s.strip().split(":")[0] in ("1", "2", "3", "4", "6", "7")]


def strocic_union(g):
    bs = []
    for s in strokes(g):
        try:
            b = SO.strokic_boundary(s)
            if b.x2 > b.x1 and b.y2 > b.y1:
                bs.append((b.x1, b.y1, b.x2, b.y2))
        except Exception:
            pass
    if not bs:
        return None
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def ink_union(g):
    xs, ys = [], []
    for s in strokes(g):
        p = s.split(":")
        xs += [float(v) for v in p[3::2]]
        ys += [float(v) for v in p[4::2]]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


print("=" * 88)
print("① 部件包围盒是否'满幅' (它是否被设计成撑满画布)")
print("=" * 88)
PARTS = [("口", "u53e3-j"), ("田", "u7530-j"), ("人", "u4eba-j"),
         ("月", "u6708-j"), ("日", "u65e5-j"), ("丙", "u4e19-j"),
         ("乃", "u4e43-j"), ("巛", "u5ddb-j"), ("付", "u4ed8-j"),
         ("木", "u6728-j"), ("丶", None)]
print(f"  {'部件':<4} {'字形':<10} {'包围盒':<34} {'x满幅':>7} {'y满幅':>7}")
print("  " + "-" * 84)
for ch, nm in PARTS:
    if nm is None:
        # 丶 = U+4E36
        nm = "u4e36-var-001"
        if not flatten(nm):
            nm = "u4e36"
    g = flatten(nm)
    bb = strocic_union(g)
    if not bb:
        print(f"  {ch:<4} {nm:<10} (无笔画)")
        continue
    fx200 = "是" if (bb[0] < 0 or bb[2] > 200) else "否"
    fy200 = "是" if (bb[1] < 0 or bb[3] > 200) else "否"
    fx195 = "是" if (bb[0] < 5 or bb[2] > 195) else "否"
    fy195 = "是" if (bb[1] < 5 or bb[3] > 195) else "否"
    print(f"  {ch:<4} {nm:<10} [{bb[0]:6.1f},{bb[1]:6.1f},{bb[2]:6.1f},{bb[3]:6.1f}]"
          f"   {fx200}/{fx195}   {fy200}/{fy195}")

print()
print("=" * 88)
print("② 内部件在空腔里的实际尺寸: B(包围盒基准) vs 你的规则 vs 设计者真实")
print("=" * 88)


def max_empty(box, rects):
    X1, Y1, X2, Y2 = box
    Ls = sorted({X1} | {min(max(r[2], X1), X2) for r in rects})
    Rs = sorted({X2} | {min(max(r[0], X1), X2) for r in rects})
    best, ba = None, -1.0
    for L in Ls:
        for R in Rs:
            if R <= L:
                continue
            bl = sorted((max(r[1], Y1), min(r[3], Y2)) for r in rects
                        if r[0] < R and r[2] > L and r[1] < Y2 and r[3] > Y1)
            gaps, cur = [], Y1
            for b0, b1 in bl:
                if b0 > cur:
                    gaps.append((cur, b0))
                if b1 > cur:
                    cur = b1
            if cur < Y2:
                gaps.append((cur, Y2))
            for g0, g1 in gaps:
                a = (R - L) * (g1 - g0)
                if a > ba:
                    ba, best = a, (L, g0, R, g1)
    return best


def map_axis(src, cav, bbox):
    """给定该轴的映射基准 src(长度200或bbox范围), 返回 (A, W) 与映射函数"""
    s0, s1 = src
    W = 200.0 * (cav[1] - cav[0]) / (s1 - s0)
    A = cav[0] - s0 / 200.0 * W
    return A, W


def apply_map(v, A, W):
    return A + v / 200.0 * W


def boxes(g):
    out = []
    for s in strokes(g):
        try:
            b = SO.strokic_boundary(s)
            if b.x2 > b.x1 and b.y2 > b.y1:
                out.append((b.x1, b.y1, b.x2, b.y2))
        except Exception:
            pass
    return out


def refs(g):
    out = []
    for seg in g.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                out.append((p[7], (int(p[3]), int(p[4]), int(p[5]), int(p[6]))))
            except ValueError:
                pass
    return out


# (字, 容器, 内部件, 内部件字形)
CASES = [
    ("問", "u9580-05", "口", "u53e3-j"),
    ("閒", "u9580-05", "月", "u6708-j"),
    ("囚", "u56d7-j", "人", "u4eba-j"),
    ("旬", "u52f9-05", "日", "u65e5-j"),
]

for label, cvar, ich, ivar in CASES:
    cg = flatten(cvar)
    bs = boxes(cg)
    if not bs:
        continue
    outer = (min(b[0] for b in bs), min(b[1] for b in bs),
             max(b[2] for b in bs), max(b[3] for b in bs))
    cav = max_empty(outer, bs)
    ig = flatten(ivar)
    ibb = strocic_union(ig)
    iink = ink_union(ig)
    if not cav or not ibb or not iink:
        continue

    # B: 两轴都用包围盒基准
    Ax, Wx = map_axis((ibb[0], ibb[2]), (cav[0], cav[2]), ibb)
    Ay, Wy = map_axis((ibb[1], ibb[3]), (cav[1], cav[3]), ibb)
    bink = (apply_map(iink[0], Ax, Wx), apply_map(iink[1], Ay, Wy),
            apply_map(iink[2], Ax, Wx), apply_map(iink[3], Ay, Wy))

    # 用户规则: 该轴 bbox 超出 [0,200] 才用包围盒基准, 否则用 0-200
    sx = (ibb[0], ibb[2]) if (ibb[0] < 0 or ibb[2] > 200) else (0.0, 200.0)
    sy = (ibb[1], ibb[3]) if (ibb[1] < 0 or ibb[3] > 200) else (0.0, 200.0)
    Nx, Vx = map_axis(sx, (cav[0], cav[2]), ibb)
    Ny, Vy = map_axis(sy, (cav[1], cav[3]), ibb)
    uink = (apply_map(iink[0], Nx, Vx), apply_map(iink[1], Ny, Vy),
            apply_map(iink[2], Nx, Vx), apply_map(iink[3], Ny, Vy))

    print(f"\n  {label} (⿵/⿴ {ich})   容器={cvar}  内部={ivar}")
    print(f"    空腔        {cav[2]-cav[0]:6.0f} x {cav[3]-cav[1]:6.0f}"
          f"   [{cav[0]:.0f},{cav[1]:.0f},{cav[2]:.0f},{cav[3]:.0f}]")
    print(f"    内部件包围盒 [{ibb[0]:6.1f},{ibb[1]:6.1f},{ibb[2]:6.1f},{ibb[3]:6.1f}]"
          f"   x基准={'bbox' if sx[1]-sx[0]<200 else '0-200'} "
          f"y基准={'bbox' if sy[1]-sy[0]<200 else '0-200'}")
    print(f"    B(包围盒基准) 墨迹 {bink[2]-bink[0]:6.0f} x {bink[3]-bink[1]:6.0f}")
    print(f"    你的规则      墨迹 {uink[2]-uink[0]:6.0f} x {uink[3]-uink[1]:6.0f}")
