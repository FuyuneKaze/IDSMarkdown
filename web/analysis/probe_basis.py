# -*- coding: utf-8 -*-
"""验证"骨架点方向均值当基准框"的效果: 口 / 乂 / 国 / 人 / 乃 各得到多大的基准"""
import sys, io, contextlib, math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, stroke_outer as so  # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def skeleton_points(flat, per=6):
    """沿骨架均匀取点 (弧长均分; 曲线按 stroke_point 的采样再线性重采样)"""
    pts = []
    for s in ids_anal.stroke_list(flat):
        raw, _n, _e = q(so.stroke_point, s)
        raw = [(float(p.x), float(p.y)) for p in raw]
        if len(raw) < 2:
            pts.extend(raw)
            continue
        acc = [0.0]
        for a, b in zip(raw, raw[1:]):
            acc.append(acc[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
        total = acc[-1] or 1.0
        for k in range(per):
            t = total * (k + 0.5) / per
            j = max(0, min(len(acc) - 2, next((i for i, d in enumerate(acc) if d >= t), len(acc) - 1)))
            while j > 0 and acc[j] > t:
                j -= 1
            seg = acc[j+1] - acc[j] or 1.0
            f = (t - acc[j]) / seg
            a, b = raw[j], raw[j+1]
            pts.append((a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f))
    return pts


def basis(pts, quantile=0.5):
    """方向均值/分位: 中心以上点的 y 统计当上界, 以下当下界; x 同理"""
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    up = sorted(p[1] for p in pts if p[1] < cy)
    dn = sorted(p[1] for p in pts if p[1] > cy)
    lf = sorted(p[0] for p in pts if p[0] < cx)
    rt = sorted(p[0] for p in pts if p[0] > cx)

    def pick(v, default):
        if not v:
            return default
        k = int(round((1 - quantile) * (len(v) - 1)))     # 0.5 → 中位数
        return v[k]

    return (pick(lf, cx), pick(up, cy), pick(rt, cx), pick(dn, cy)), (cx, cy)


COMPS = [("口", "u53e3"), ("乂", "u4e42"), ("国", "u56fd"), ("日", "u65e5"),
         ("田", "u7530"), ("人", "u4eba"), ("乃", "u4e43"), ("木", "u6728"),
         ("丶", "u4e36"), ("心", "u5fc3")]

CAV = 100.0     # 假设空腔 100x100, 看各自会被放大/缩小多少倍
print(f"{'部件':6s} {'骨架点':>5s} {'墨迹盒':>22s} {'基准框(均值)':>22s} {'基准/盒':>8s} {'放入100空腔的缩放':>10s}")
for ch, nm in COMPS:
    flat = q(glyph_extend.return_bone, nm)
    st = ids_anal.stroke_list(flat)
    if not st:
        print(f"{ch:6s}   (没有直绘笔画)")
        continue
    pts = skeleton_points(flat)
    b = q(ids_anal.bbox, flat)
    bb = tuple(float(v) for v in b)
    bas, c = basis(pts)
    bw = bas[2] - bas[0]
    bh = bas[3] - bas[1]
    ix = (bb[2] - bb[0])
    print(f"{ch:6s} {len(pts):5d} ({bb[0]:6.1f},{bb[1]:6.1f})-({bb[2]:6.1f},{bb[3]:6.1f}) "
          f"({bas[0]:6.1f},{bas[1]:6.1f})-({bas[2]:6.1f},{bas[3]:6.1f}) "
          f"{bw/ix*100 if ix else 0:7.0f}% {CAV/bw if bw else 0:9.2f}x")
