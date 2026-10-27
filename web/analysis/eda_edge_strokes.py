# -*- coding: utf-8 -*-
"""
EDA 3: 把"边缘竖直度"变成可计算的量, 验证核心假设:

    overlap 由接缝两侧的"边缘笔画方向"决定, 而非复杂度
      - 两侧边缘都是竖笔  → 必须留间隙 (overlap 负)
      - 边缘是横/点端头    → 可贴近甚至重叠 (overlap 正)

边缘竖直度定义:
    部件右(左)边界附近 band 宽度内"触及边界"的笔画中,
    竖直笔画 (dy > dx) 的 y 覆盖总长 / 部件高度

用法: python eda_edge_strokes.py [样本数]
"""
import sys, io, json, time
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"
BAND = 12.0


# ============================================================
# 展开 type-99 到叶子笔画, 映射到父坐标系
# ============================================================
def collect_strokes(data, glyph_db, rect=(0, 0, 200, 200), visited=None, depth=0):
    """返回 [(kind, [(x,y),...]), ...] — 坐标在 rect 中"""
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
        parts = seg.split(":")
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            name = parts[7].split("@")[0]
            try:
                bx1, by1, bx2, by2 = (int(parts[3]), int(parts[4]),
                                      int(parts[5]), int(parts[6]))
            except ValueError:
                continue
            if name in glyph_db and name not in visited:
                visited.add(name)
                sub = collect_strokes(glyph_db[name], glyph_db,
                                      (bx1, by1, bx2, by2), visited, depth + 1)
                for k, pts in sub:
                    out.append((k, [(rx1 + (px / 200.0) * rw,
                                     ry1 + (py / 200.0) * rh) for px, py in pts]))
        elif kind in (1, 2, 3, 4, 6, 7):
            pts = []
            for i in range(3, len(parts) - 1, 2):
                try:
                    pts.append((int(parts[i]), int(parts[i + 1])))
                except ValueError:
                    pass
            if pts:
                out.append((kind, [(rx1 + (px / 200.0) * rw,
                                    ry1 + (py / 200.0) * rh) for px, py in pts]))
    return out


def edge_features(strokes, band=BAND):
    """返回 (bbox, 右缘竖直度, 左缘竖直度, 右缘触边数, 左缘触边数)"""
    if not strokes:
        return None
    xs = [x for _, pts in strokes for x, _ in pts]
    ys = [y for _, pts in strokes for _, y in pts]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)
    hh = max(y2 - y1, 1.0)
    ww = max(x2 - x1, 1.0)

    rv = rl = 0.0           # 竖笔 y 覆盖长度
    rt = lt = 0             # 触边笔画数
    rv_frac = rl_frac = 0.0  # 竖笔覆盖的 y 区间并集长度

    for _, pts in strokes:
        px = [p[0] for p in pts]
        py = [p[1] for p in pts]
        dx = max(px) - min(px)
        dy = max(py) - min(py)
        is_ver = dy > dx

        if max(px) >= x2 - band:          # 触及右边界
            rt += 1
            if is_ver:
                rv += dy
        if min(px) <= x1 + band:          # 触及左边界
            lt += 1
            if is_ver:
                rl += dy

    return (x1, y1, x2, y2, rv / hh, rl / hh, rt, lt)


# ============================================================
def main():
    n_sample = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    t0 = time.time()
    print("加载 core_glyphs.json ...", flush=True)
    glyph_db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
    print(f"  {len(glyph_db)} 字形 ({time.time()-t0:.1f}s)\n")

    df = pd.read_csv(CSV, encoding="utf-8-sig")
    h = df[df["op"] == "⿰"].dropna(
        subset=["c1_str_x1", "c1_str_x2", "c2_str_x1", "c2_str_x2"]).copy()
    h["w1"] = h["c1_str_x2"] - h["c1_str_x1"]
    h["w2"] = h["c2_str_x2"] - h["c2_str_x1"]
    h = h[(h["w1"] > 1) & (h["w2"] > 1)].copy()
    h["overlap"] = h["c1_str_x2"] - h["c2_str_x1"]
    # 只要两侧都是明确变体引用的行 (最干净)
    h = h.dropna(subset=["c1_variant", "c2_variant"])
    h = h[(h["c1_variant"].astype(str).str.len() > 0) &
          (h["c2_variant"].astype(str).str.len() > 0)].copy()

    if n_sample and len(h) > n_sample:
        h = h.sample(n_sample, random_state=42)
    h = h.reset_index(drop=True)
    print(f"⿰ 有效样本(两侧均为变体): {len(h)}\n")

    # ---- 特征提取 (按变体名缓存) ----
    print("提取边缘竖直度 ...", flush=True)
    cache = {}
    missing = 0

    def feat(name):
        nonlocal missing
        if name in cache:
            return cache[name]
        data = glyph_db.get(name)
        if data is None:
            base = name.split("@")[0]
            data = glyph_db.get(base)
        if data is None:
            missing += 1
            cache[name] = None
            return None
        st = collect_strokes(data, glyph_db)
        f = edge_features(st)
        cache[name] = f
        return f

    rows = []
    for r in h.itertuples(index=False):
        f1 = feat(r.c1_variant)
        f2 = feat(r.c2_variant)
        if f1 is None or f2 is None:
            continue
        rows.append({
            "char": r.char, "c1": r.c1_char, "c2": r.c2_char,
            "c1v": r.c1_variant, "c2v": r.c2_variant,
            "overlap": r.overlap,
            "L_right_v": f1[4], "L_left_v": f1[5],
            "R_right_v": f2[4], "R_left_v": f2[5],
            "L_w": f1[2] - f1[0], "L_h": f1[3] - f1[1],
            "R_w": f2[2] - f2[0], "R_h": f2[3] - f2[1],
        })
    d = pd.DataFrame(rows)
    print(f"  有效: {len(d)}  变体缺失={missing}  唯一变体={len(cache)}\n")

    print("=" * 74)
    print("1. 边缘竖直度校验 (预期: 口/日/月 右缘≈1, 氵/扌/禾 右缘≈0)")
    print("=" * 74)
    print(f"  {'部件':<4} {'右缘竖':>8} {'左缘竖':>8} {'n':>6}")
    for ch in ["口", "日", "月", "目", "田", "山", "木", "氵", "扌", "禾", "土", "亻", "纟", "讠"]:
        s = d[d["c1"] == ch]
        if len(s) < 10:
            continue
        print(f"  {ch:<4} {s['L_right_v'].mean():>8.3f} {s['L_left_v'].mean():>8.3f} {len(s):>6}")

    d.to_csv(r"D:\2026harucpp\web\analysis\edge_features.csv",
             index=False, encoding="utf-8-sig")
    print(f"\n  已保存 edge_features.csv ({len(d)} 行)")

    # ---- 2. 二维验证 ----
    print()
    print("=" * 74)
    print("2. 核心验证: overlap vs (左部件右缘竖直度, 右部件左缘竖直度)")
    print("=" * 74)
    print(f"\n  corr(overlap, L_right_v) = {d['overlap'].corr(d['L_right_v']):+.3f}")
    print(f"  corr(overlap, R_left_v)  = {d['overlap'].corr(d['R_left_v']):+.3f}")
    print(f"  corr(overlap, L_right_v + R_left_v) = "
          f"{d['overlap'].corr(d['L_right_v'] + d['R_left_v']):+.3f}")
    print(f"  corr(overlap, L_right_v * R_left_v) = "
          f"{d['overlap'].corr(d['L_right_v'] * d['R_left_v']):+.3f}")

    d["vsum"] = d["L_right_v"] + d["R_left_v"]
    d["vbin"] = pd.cut(d["vsum"], [-0.01, 0.15, 0.4, 0.7, 1.0, 5],
                       labels=["0-0.15", "0.15-0.4", "0.4-0.7", "0.7-1.0", ">1.0"])
    print(f"\n  {'两侧竖度之和':<14} {'n':>7} {'overlap均值':>12} {'std':>8}")
    for b, gg in d.groupby("vbin", observed=True):
        print(f"  {str(b):<14} {len(gg):>7} {gg['overlap'].mean():>12.2f} {gg['overlap'].std():>8.2f}")

    # 四象限
    print(f"\n  四象限 (阈值 0.35):")
    print(f"  {'左缘竖':<8} {'右缘竖':<8} {'n':>7} {'overlap均值':>12} {'std':>8}")
    for lv in [False, True]:
        for rv in [False, True]:
            s = d[((d["L_right_v"] > 0.35) == lv) & ((d["R_left_v"] > 0.35) == rv)]
            if len(s) < 5:
                continue
            print(f"  {('高' if lv else '低'):<8} {('高' if rv else '低'):<8} "
                  f"{len(s):>7} {s['overlap'].mean():>12.2f} {s['overlap'].std():>8.2f}")

    # ---- 3. 与 bbox 空白对比 ----
    print()
    print("=" * 74)
    print("3. 对比: 边缘竖度 vs bbox 空白, 谁更能解释 overlap")
    print("=" * 74)
    d["gap_both"] = (200 - d["L_right_v"] * 0)  # placeholder
    # 用左部件右缘 x 位置与右部件左缘 x 位置 (原始空间) 的空白代理
    d["blank"] = (200 - d["L_w"]) / 2 + (200 - d["R_w"]) / 2
    print(f"  corr(overlap, |vsum| 边缘竖度)      = {d['overlap'].corr(d['vsum']):+.3f}")
    print(f"  corr(overlap, blank bbox 空白代理)  = {d['overlap'].corr(d['blank']):+.3f}")
    print(f"  corr(overlap, L_w)                 = {d['overlap'].corr(d['L_w']):+.3f}")
    print(f"  corr(overlap, R_w)                 = {d['overlap'].corr(d['R_w']):+.3f}")


if __name__ == "__main__":
    main()
