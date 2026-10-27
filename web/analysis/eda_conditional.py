# -*- coding: utf-8 -*-
"""
EDA 5: 控制变量法验证 overlap 规律

上轮失误: 在全部字对上算 corr(overlap, R_left_v) = -0.005,
         被"左部件身份"的巨大变异淹没 → 必须固定一侧再看。

本脚本:
  1. 提取更精确的特征: 边缘竖笔的 y 区间 + 两侧区间交集长度
  2. 固定左部件, 在组内算 corr(overlap, 右缘特征) → 看规律是否浮现
  3. 双变量回归: overlap ~ 左侧特征 + 右侧特征 (组内去均值)
"""
import sys, io, json, time
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"
BAND = 12.0


def collect_strokes(data, db, rect=(0, 0, 200, 200), visited=None, depth=0):
    if visited is None:
        visited = set()
    if depth > 12:
        return []
    rx1, ry1, rx2, ry2 = rect
    rw, rh = rx2 - rx1, ry2 - ry1
    out = []
    for seg in data.split("$"):
        seg = seg.strip()
        if not seg:
            continue
        p = seg.split(":")
        try:
            kind = int(p[0])
        except ValueError:
            continue
        if kind == 99 and len(p) >= 8:
            name = p[7].split("@")[0]
            try:
                bx1, by1, bx2, by2 = int(p[3]), int(p[4]), int(p[5]), int(p[6])
            except ValueError:
                continue
            if name in db and name not in visited:
                visited.add(name)
                for k, pts in collect_strokes(db[name], db, (bx1, by1, bx2, by2), visited, depth + 1):
                    out.append((k, [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
        elif kind in (1, 2, 3, 4, 6, 7):
            pts = []
            for i in range(3, len(p) - 1, 2):
                try:
                    pts.append((int(p[i]), int(p[i + 1])))
                except ValueError:
                    pass
            if pts:
                out.append((kind, [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
    return out


def edge_profile(strokes, band=BAND):
    """归一化到 0-1 的 y 区间 (以部件 bbox 为基准)

    返回 (bbox, right_ver_segs, left_ver_segs, right_ver_ratio, left_ver_ratio)
    segs 为 [(y0,y1), ...] 归一化区间
    """
    if not strokes:
        return None
    xs = [x for _, pts in strokes for x, _ in pts]
    ys = [y for _, pts in strokes for _, y in pts]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    hh = max(y2 - y1, 1e-6)

    rsegs, lsegs = [], []
    for _, pts in strokes:
        px = [q[0] for q in pts]
        py = [q[1] for q in pts]
        dx, dy = max(px) - min(px), max(py) - min(py)
        if dy <= dx:                       # 只取竖笔
            continue
        a, b = (min(py) - y1) / hh, (max(py) - y1) / hh
        if max(px) >= x2 - band:
            rsegs.append((a, b))
        if min(px) <= x1 + band:
            lsegs.append((a, b))

    r_ratio = sum(b - a for a, b in rsegs)
    l_ratio = sum(b - a for a, b in lsegs)
    return ((x1, y1, x2, y2), rsegs, lsegs, min(r_ratio, 1.0), min(l_ratio, 1.0))


def seg_intersection(segs_a, segs_b):
    """两组区间的交集总长"""
    if not segs_a or not segs_b:
        return 0.0
    total = 0.0
    for a0, a1 in segs_a:
        for b0, b1 in segs_b:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                total += hi - lo
    return total


def main():
    t0 = time.time()
    db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
    print(f"core_glyphs: {len(db)} ({time.time()-t0:.1f}s)")

    df = pd.read_csv(CSV, encoding="utf-8-sig")
    h = df[df["op"] == "⿰"].dropna(
        subset=["c1_str_x1", "c1_str_x2", "c2_str_x1", "c2_str_x2"]).copy()
    h = h.dropna(subset=["c1_variant", "c2_variant"])
    h = h[(h["c1_variant"].astype(str).str.len() > 0) &
          (h["c2_variant"].astype(str).str.len() > 0)].copy()
    h["overlap"] = h["c1_str_x2"] - h["c2_str_x1"]
    h = h.reset_index(drop=True)
    print(f"⿰ 样本: {len(h)}")

    pcache = {}
    def prof(name):
        if name in pcache:
            return pcache[name]
        data = db.get(name) or db.get(name.split("@")[0])
        r = edge_profile(collect_strokes(data, db)) if data else None
        pcache[name] = r
        return r

    rows = []
    for r in h.itertuples(index=False):
        p1, p2 = prof(r.c1_variant), prof(r.c2_variant)
        if p1 is None or p2 is None:
            continue
        _, rsegs1, _, rrat1, _ = p1
        _, _, lsegs2, _, lrat2 = p2
        rows.append({
            "char": r.char, "c1": r.c1_char, "c2": r.c2_char,
            "overlap": r.overlap,
            "L_rv": rrat1, "R_lv": lrat2,
            "seg_ov": seg_intersection(rsegs1, lsegs2),
        })
    d = pd.DataFrame(rows)
    print(f"有效: {len(d)}  ({time.time()-t0:.1f}s)\n")

    d.to_csv(r"D:\2026harucpp\web\analysis\cond_features.csv", index=False, encoding="utf-8-sig")

    print("=" * 76)
    print("1. 全局相关 (对照: 上轮同量级)")
    print("=" * 76)
    for c in ["L_rv", "R_lv", "seg_ov"]:
        print(f"  corr(overlap, {c:<7}) = {d['overlap'].corr(d[c]):+.3f}")

    print()
    print("=" * 76)
    print("2. 控制变量: 固定左部件, 组内 corr(overlap, R_lv) 与 corr(overlap, seg_ov)")
    print("=" * 76)
    print(f"  {'左部件':<6} {'n':>6} {'corr_R_lv':>11} {'corr_seg_ov':>13}")
    res = []
    for ch, g in d.groupby("c1"):
        if len(g) < 150:
            continue
        if g["R_lv"].std() < 1e-6 or g["seg_ov"].std() < 1e-6:
            continue
        c1 = g["overlap"].corr(g["R_lv"])
        c2 = g["overlap"].corr(g["seg_ov"])
        res.append((ch, len(g), c1, c2))
    res.sort(key=lambda x: x[2])
    for ch, n, c1, c2 in res[:18]:
        print(f"  {ch:<6} {n:>6} {c1:>11.3f} {c2:>13.3f}")
    if len(res) > 24:
        print("  ...")
        for ch, n, c1, c2 in res[-6:]:
            print(f"  {ch:<6} {n:>6} {c1:>11.3f} {c2:>13.3f}")

    if res:
        a = np.array([x[2] for x in res])
        b = np.array([x[3] for x in res])
        print(f"\n  组数 n={len(res)}")
        print(f"  corr_R_lv   : 均值={a.mean():+.3f} 中位={np.median(a):+.3f} "
              f"负值占比={(a<0).mean()*100:.0f}%")
        print(f"  corr_seg_ov : 均值={b.mean():+.3f} 中位={np.median(b):+.3f} "
              f"负值占比={(b<0).mean()*100:.0f}%")

    print()
    print("=" * 76)
    print("3. 对称: 固定右部件, 组内 corr(overlap, L_rv)")
    print("=" * 76)
    res2 = []
    for ch, g in d.groupby("c2"):
        if len(g) < 150 or g["L_rv"].std() < 1e-6:
            continue
        res2.append((ch, len(g), g["overlap"].corr(g["L_rv"])))
    res2.sort(key=lambda x: x[2])
    for ch, n, c1 in res2[:12]:
        print(f"  {ch:<6} {n:>6} {c1:>11.3f}")
    if res2:
        a = np.array([x[2] for x in res2])
        print(f"\n  组数 n={len(res2)}  均值={a.mean():+.3f} 中位={np.median(a):+.3f} "
              f"负值占比={(a<0).mean()*100:.0f}%")

    print()
    print("=" * 76)
    print("4. 组内去均值后的净效应 (控制两侧身份)")
    print("=" * 76)
    d["ov_c"] = d["overlap"] - d.groupby("c1")["overlap"].transform("mean")
    d["L_rv_c"] = d["L_rv"] - d.groupby("c1")["L_rv"].transform("mean")
    d["R_lv_c"] = d["R_lv"] - d.groupby("c1")["R_lv"].transform("mean")
    print(f"  corr(ov_c, L_rv_c) = {d['ov_c'].corr(d['L_rv_c']):+.3f}")
    print(f"  corr(ov_c, R_lv_c) = {d['ov_c'].corr(d['R_lv_c']):+.3f}")

    # 多元线性
    X = d[["L_rv_c", "R_lv_c"]].values
    y = d["ov_c"].values
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    pred = X1 @ beta
    ss_res = ((y - pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    print(f"\n  overlap_c = {beta[0]:+.2f} {beta[1]:+.2f}*L_rv_c {beta[2]:+.2f}*R_lv_c")
    print(f"  R² = {1 - ss_res/ss_tot:.4f}   (残差 std = {np.sqrt(ss_res/len(y)):.2f})")
    print(f"  原始 overlap std = {d['overlap'].std():.2f}")


if __name__ == "__main__":
    main()
