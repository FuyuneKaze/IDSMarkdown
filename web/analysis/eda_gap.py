# -*- coding: utf-8 -*-
"""
EDA 11 (收官): 量化"当前 kageEngine 算法"与"真实机制"的差距

真实机制 : 位置变体 + 接近全画布的矩形 (位置由变体自带)
当前算法 : split 切分画布 + 把部件 bbox 对齐到 split

对比指标: 两个部件最终视觉边界的 overlap
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"
df = pd.read_csv(CSV, encoding="utf-8-sig")

h = df[df["op"] == "⿰"].dropna(subset=[
    "c1_orig_x1", "c1_orig_x2", "c2_orig_x1", "c2_orig_x2",
    "c1_str_x1", "c1_str_x2", "c2_str_x1", "c2_str_x2"]).copy()
h = h[(h["c1_orig_x2"] > h["c1_orig_x1"]) & (h["c2_orig_x2"] > h["c2_orig_x1"])].copy()
print(f"⿰ 样本: {len(h)}\n")

# ---- 真实: 真实矩形下两部件的位置 ---- (CSV 已给出 str bbox)
h["ov_real"] = h["c1_str_x2"] - h["c2_str_x1"]


def kage_engine_rects(w1, h1, w2, h2, b1x2, b2x1):
    """复刻 kageEngine.buildComposite 的 ⿰ 分支"""
    w1c = w1 if w1 < 170 else 100.0
    w2c = w2 if w2 < 170 else 100.0
    w1c = max(w1c, 5.0)
    w2c = max(w2c, 5.0)
    split = 3 + np.floor(194 * w1c / (w1c + w2c))
    split = np.clip(split, 20, 180)

    left_x2 = np.floor(split * 200 / max(b1x2, 1))
    left_x2 = np.clip(left_x2, 5, 200)
    right_x1 = np.floor(200 - 200 * (200 - split) / (200 - b2x1))
    right_x1 = np.clip(right_x1, 0, 190)
    return left_x2, right_x1


def map_x(x, rx1, rx2):
    return rx1 + (x / 200.0) * (rx2 - rx1)


rows = []
for r in h.itertuples(index=False):
    w1 = r.c1_orig_x2 - r.c1_orig_x1
    h1 = r.c1_orig_y2 - r.c1_orig_y1
    w2 = r.c2_orig_x2 - r.c2_orig_x1
    h2 = r.c2_orig_y2 - r.c2_orig_y1
    lx2, rx1 = kage_engine_rects(w1, h1, w2, h2, r.c1_orig_x2, r.c2_orig_x1)

    # 左部件矩形 (3,3,lx2,200)  右部件矩形 (rx1,3,200,200)
    b1_cx2 = map_x(r.c1_orig_x2, 3, lx2)     # 左部件右边界映射后
    b2_cx1 = map_x(r.c2_orig_x1, rx1, 200)   # 右部件左边界映射后
    ov_kage = b1_cx2 - b2_cx1
    rows.append({"ov_real": r.c1_str_x2 - r.c2_str_x1, "ov_kage": ov_kage})

d = pd.DataFrame(rows)
print("=" * 76)
print("1. overlap: 真实机制 vs 当前 kageEngine")
print("=" * 76)
for c in ["ov_real", "ov_kage"]:
    o = d[c]
    print(f"  {c:<9} mean={o.mean():7.2f} std={o.std():6.2f} "
          f"p5={np.percentile(o,5):7.1f} p50={o.median():7.1f} p95={np.percentile(o,95):7.1f}")

diff = d["ov_kage"] - d["ov_real"]
print(f"\n  差异 (kage - real): mean={diff.mean():+.2f} std={diff.std():.2f}")
print(f"  |差异| 中位 = {diff.abs().median():.2f} px  (200 空间)")
print(f"  |差异| > 10px 占比 = {(diff.abs() > 10).mean()*100:.1f}%")
print(f"  |差异| > 20px 占比 = {(diff.abs() > 20).mean()*100:.1f}%")
print(f"\n  相关 corr(ov_real, ov_kage) = {d['ov_real'].corr(d['ov_kage']):+.3f}")
print(f"  真实 std={d['ov_real'].std():.2f}  vs  kage 预测 std={d['ov_kage'].std():.2f}")
print(f"  → kage 把真实 ±{d['ov_real'].std():.0f}px 的波动压缩成 ±{d['ov_kage'].std():.0f}px")

print()
print("=" * 76)
print("2. 当前算法是'恒定 overlap'吗? 检查 split 的 clamp 效应")
print("=" * 76)
print(f"  ov_kage 分位: " + "  ".join(f"p{q}={np.percentile(d['ov_kage'],q):.1f}"
                                     for q in [5, 25, 50, 75, 95]))
print(f"  ov_kage 落在 [-2,2] 的占比: {(d['ov_kage'].abs() <= 2).mean()*100:.1f}%")
print(f"  ov_real 落在 [-2,2] 的占比: {(d['ov_real'].abs() <= 2).mean()*100:.1f}%")

print()
print("=" * 76)
print("3. 用真实机制的下界: 若直接沿用真实 overlap 的均值, 能减少多少误差?")
print("=" * 76)
mean_pred = np.full(len(d), d["ov_real"].mean())
print(f"  常数预测 MAE            = {np.abs(mean_pred - d['ov_real']).mean():.2f}")
print(f"  kageEngine 预测 MAE     = {np.abs(d['ov_kage'] - d['ov_real']).mean():.2f}")
print(f"  真实 std                = {d['ov_real'].std():.2f}")
