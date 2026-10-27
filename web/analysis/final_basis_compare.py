# -*- coding: utf-8 -*-
"""
最终对比 (内部件一律用 base+"-06", 与 ids_anal 实际一致)

B      = 包围盒基准 (旧): 缩放比 = 空腔/包围盒
规则   = 按轴选基准 (新): 超出 [0,200] 才用包围盒, 否则用 0-200
真实   = GlyphWiki 设计者的放置
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


def sb(g):
    out = []
    for s in strokes(g):
        try:
            b = SO.strokic_boundary(s)
            if b.x2 > b.x1 and b.y2 > b.y1:
                out.append((b.x1, b.y1, b.x2, b.y2))
        except Exception:
            pass
    return out


def union(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs)) if bs else None


def ink(g):
    xs, ys = [], []
    for s in strokes(g):
        p = s.split(":")
        xs += [float(v) for v in p[3::2]]
        ys += [float(v) for v in p[4::2]]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


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


def mapb(inkb, srcx, srcy, cav):
    Ax = cav[0] - srcx[0] / 200.0 * (200.0 * (cav[2] - cav[0]) / (srcx[1] - srcx[0]))
    Wx = 200.0 * (cav[2] - cav[0]) / (srcx[1] - srcx[0])
    Ay = cav[1] - srcy[0] / 200.0 * (200.0 * (cav[3] - cav[1]) / (srcy[1] - srcy[0]))
    Wy = 200.0 * (cav[3] - cav[1]) / (srcy[1] - srcy[0])
    mx = lambda x: Ax + x / 200.0 * Wx
    my = lambda y: Ay + y / 200.0 * Wy
    return (mx(inkb[0]), my(inkb[1]), mx(inkb[2]), my(inkb[3]))


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


CASES = [
    ("問", "u9580", "口", "u53e3", "u554f"),
    ("閒", "u9580", "月", "u6708", "u9591"),
    ("囚", "u56d7", "人", "u4eba", "u56da"),
    ("病", "u7592", "丙", "u4e19", "u75c5"),
    ("府", "u5e7f", "付", "u4ed8", "u5e9c"),
    ("氖", "u6c14", "乃", "u4e43", "u6c16"),
    ("旬", "u52f9", "日", "u65e5", "u65ec"),
]

print("=" * 92)
print(f"  {'字':<4} {'空腔':<14} {'内部件盒':<26} {'B':<12} {'规则':<12} {'真实':<12}")
print("  " + "-" * 88)
for label, cb, ich, ib, pname in CASES:
    cg = flatten(cb + "-05")
    bs = sb(cg)
    if not bs:
        print(f"  {label}: 容器无笔画")
        continue
    outer = union(bs)
    cav = max_empty(outer, bs)
    ig = flatten(ib + "-06")
    ibb = union(sb(ig))
    im = ink(ig)
    if not cav or not ibb or not im:
        print(f"  {label}: 缺空腔/盒")
        continue

    # B: 包围盒基准
    mb = mapb(im, (ibb[0], ibb[2]), (ibb[1], ibb[3]), cav)
    # 规则: 超出 [0,200] 才用包围盒
    sx = (ibb[0], ibb[2]) if (ibb[0] < 0 or ibb[2] > 200) else (0.0, 200.0)
    sy = (ibb[1], ibb[3]) if (ibb[1] < 0 or ibb[3] > 200) else (0.0, 200.0)
    mr = mapb(im, sx, sy, cav)

    # 真实
    pd, _ = "", None
    rg = flatten(pname)
    rf = refs(rg)
    real = None
    for nm, rect in rf:
        if nm.startswith(ib):
            ri = flatten(nm, rect)
            real = ink(ri)
            break

    flags = f"{'bbox' if sx[1]-sx[0]<199 else '0-200'}/{'bbox' if sy[1]-sy[0]<199 else '0-200'}"
    print(f"  {label:<4} {cav[2]-cav[0]:4.0f}x{cav[3]-cav[1]:<4.0f}"
          f"[{cav[0]:.0f},{cav[1]:.0f},{cav[2]:.0f},{cav[3]:.0f}]  "
          f"[{ibb[0]:5.1f},{ibb[1]:5.1f},{ibb[2]:5.1f},{ibb[3]:5.1f}] {flags:<11}"
          f"{mb[2]-mb[0]:4.0f}x{mb[3]-mb[1]:<4.0f}   "
          f"{mr[2]-mr[0]:4.0f}x{mr[3]-mr[1]:<4.0f}   "
          + (f"{real[2]-real[0]:4.0f}x{real[3]-real[1]:<4.0f}" if real else "  --"))
