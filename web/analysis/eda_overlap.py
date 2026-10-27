# -*- coding: utf-8 -*-
"""
EDA 1: 用 composition_v3.csv 的真实人工布局, 先看 overlap / 比例的基本信号。

数据语义 (来自 analyze_composition_v3.py):
  c1_str_x1..x2 / c2_str_x1..x2  = 部件在父坐标系(200x200)中的实际视觉 bbox
                                   (含 STROKE_PAD=4 的笔画粗细补偿)
  c1_orig_*  = 部件在自身 200x200 空间的 bbox
  cN_strokes = 递归展开后的叶子笔画数
  cN_variant = 实际引用的变体名 (空 = 该部件是直接笔画段)

真实 overlap:
  ⿰ : c1_str_x2 - c2_str_x1   (>0 重叠, <0 间隙)
  ⿱ : c1_str_y2 - c2_str_y1
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"

df = pd.read_csv(CSV, encoding="utf-8-sig")
print(f"总行数: {len(df)}")
print(f"操作符分布:\n{df['op'].value_counts().to_string()}")
print()

# ------------------------------------------------------------
# 1. 分左右 / 上下, 计算真实 overlap
# ------------------------------------------------------------
h = df[df["op"] == "⿰"].copy()
v = df[df["op"] == "⿱"].copy()

# 只保留两侧都有有效 str bbox 的行
def valid(d, cols):
    for c in cols:
        d = d[d[c].notna()]
    return d

h = h.dropna(subset=["c1_str_x2", "c2_str_x1"])
v = v.dropna(subset=["c1_str_y2", "c2_str_y1"])

h["overlap"] = h["c1_str_x2"] - h["c2_str_x1"]
v["overlap"] = v["c1_str_y2"] - v["c2_str_y1"]

# 部件宽度/高度 (实际占用)
h["w1"] = h["c1_str_x2"] - h["c1_str_x1"]
h["w2"] = h["c2_str_x2"] - h["c2_str_x1"]
v["h1"] = v["c1_str_y2"] - v["c1_str_y1"]
v["h2"] = v["c2_str_y2"] - v["c2_str_y1"]

print("=" * 70)
print("1. 真实 overlap 分布 (px)")
print("=" * 70)
for name, d in [("⿰ 左右", h), ("⿱ 上下", v)]:
    o = d["overlap"]
    print(f"\n{name}  n={len(d)}")
    print(f"  mean={o.mean():7.2f}  std={o.std():7.2f}  median={o.median():7.2f}")
    qs = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    print("  分位数: " + "  ".join(f"p{q}={np.percentile(o, q):6.1f}" for q in qs))
    print(f"  重叠(>0)占比: {(o > 0).mean() * 100:5.1f}%")
    print(f"  间隙(<0)占比: {(o < 0).mean() * 100:5.1f}%")
    print(f"  |overlap|<5 占比: {(o.abs() < 5).mean() * 100:5.1f}%")

# ------------------------------------------------------------
# 2. overlap 是否主要由"复杂度"解释? (对照假设: 应该解释不了)
# ------------------------------------------------------------
print()
print("=" * 70)
print("2. overlap vs 部件笔画数 (复杂度代理)")
print("=" * 70)
for name, d in [("⿰", h), ("⿱", v)]:
    d = d.dropna(subset=["c1_strokes", "c2_strokes"])
    if len(d) < 50:
        continue
    d["s1"] = pd.to_numeric(d["c1_strokes"], errors="coerce")
    d["s2"] = pd.to_numeric(d["c2_strokes"], errors="coerce")
    d = d.dropna(subset=["s1", "s2"])
    print(f"\n{name}  n={len(d)}")
    print(f"  corr(overlap, strokes_1) = {d['overlap'].corr(d['s1']):+.3f}")
    print(f"  corr(overlap, strokes_2) = {d['overlap'].corr(d['s2']):+.3f}")
    print(f"  corr(overlap, strokes_1+strokes_2) = {d['overlap'].corr(d['s1'] + d['s2']):+.3f}")
    print(f"  corr(overlap, |s1-s2|) = {d['overlap'].corr((d['s1'] - d['s2']).abs()):+.3f}")

# ------------------------------------------------------------
# 3. 比例: split 位置 vs 复杂度
# ------------------------------------------------------------
print()
print("=" * 70)
print("3. 比例 (部件占用) vs 复杂度")
print("=" * 70)

# ⿰: 左部件占比 = w1 / (w1+w2)
h2 = h[(h["w1"] > 0) & (h["w2"] > 0)].copy()
h2["share1"] = h2["w1"] / (h2["w1"] + h2["w2"])
v2 = v[(v["h1"] > 0) & (v["h2"] > 0)].copy()
v2["share1"] = v2["h1"] / (v2["h1"] + v2["h2"])

h2 = h2.dropna(subset=["c1_strokes", "c2_strokes"])
h2["s1"] = pd.to_numeric(h2["c1_strokes"], errors="coerce")
h2["s2"] = pd.to_numeric(h2["c2_strokes"], errors="coerce")
h2 = h2.dropna(subset=["s1", "s2"])
h2["stroke_share1"] = h2["s1"] / (h2["s1"] + h2["s2"])

print(f"\n⿰  n={len(h2)}")
print(f"  share1 vs stroke_share1 : corr = {h2['share1'].corr(h2['stroke_share1']):+.3f}")
print(f"  share1 vs w-based share (orig) : corr = {h2['share1'].corr(h2['c1_orig_w'] / (h2['c1_orig_w'] + h2['c2_orig_w'])):+.3f}")
print(f"  share1 分位数: " + "  ".join(f"p{q}={np.percentile(h2['share1'], q):.3f}" for q in [5, 25, 50, 75, 95]))

v3 = v2.dropna(subset=["c1_strokes", "c2_strokes"]).copy()
v3["s1"] = pd.to_numeric(v3["c1_strokes"], errors="coerce")
v3["s2"] = pd.to_numeric(v3["c2_strokes"], errors="coerce")
v3 = v3.dropna(subset=["s1", "s2"])
v3["stroke_share1"] = v3["s1"] / (v3["s1"] + v3["s2"])
print(f"\n⿱  n={len(v3)}")
print(f"  share1 vs stroke_share1 : corr = {v3['share1'].corr(v3['stroke_share1']):+.3f}")
print(f"  share1 分位数: " + "  ".join(f"p{q}={np.percentile(v3['share1'], q):.3f}" for q in [5, 25, 50, 75, 95]))

# ------------------------------------------------------------
# 4. 单部件聚合 vs 三元组: "口" 的比例在固定对手后是否稳定?
# ------------------------------------------------------------
print()
print("=" * 70)
print("4. 控制变量: 固定左部件, 看它的 share1 是否随对手变化")
print("=" * 70)
for ch in ["口", "木", "日", "氵", "亻", "土", "王", "月"]:
    sub = h2[h2["c1_char"] == ch]
    if len(sub) < 5:
        continue
    print(f"\n  ⿰{ch}?  n={len(sub)}")
    print(f"    share1: mean={sub['share1'].mean():.3f}  std={sub['share1'].std():.3f}  "
          f"range=[{sub['share1'].min():.3f}, {sub['share1'].max():.3f}]")

print()
print("=" * 70)
print("5. 同一个字对 (c1,c2) 的 share1 稳定性 (有多个 IDS 变体时)")
print("=" * 70)
grp = h2.groupby(["c1_char", "c2_char"])["share1"].agg(["count", "mean", "std"])
multi = grp[grp["count"] > 1]
print(f"  重复字对数: {len(multi)}")
if len(multi) > 0:
    print(f"  组内 std 均值: {multi['std'].mean():.4f}")
    print(f"  组内 std 中位: {multi['std'].median():.4f}")
