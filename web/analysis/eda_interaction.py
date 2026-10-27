# -*- coding: utf-8 -*-
"""
EDA 6: 验证"交互效应"解释

假说: overlap 取决于"接缝两侧边缘类型的组合", 而非各自独立相加
  - 右部件左缘"开放"(撇/横/点, R_lv 低)  → 左部件右缘竖笔主导 → 强负相关
  - 右部件左缘"封闭"(竖笔, R_lv 高)      → 两侧都是竖, 关系不同

同时给出最直观的二维规律表: L_rv箱 × R_lv箱 → overlap 均值
"""
import sys, io, json
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 240)

D = r"D:\2026harucpp\web\analysis\cond_features.csv"
d = pd.read_csv(D, encoding="utf-8-sig")
print(f"样本: {len(d)}\n")

print("=" * 78)
print("1. 右部件按'左缘竖度'分组 → 组内 corr(overlap, L_rv)  [交互效应检验]")
print("=" * 78)
print(f"  {'R_lv 范围':<14} {'n':>7} {'corr(overlap,L_rv)':>19} {'overlap均值':>12}")
for lo, hi in [(0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.01)]:
    s = d[(d["R_lv"] >= lo) & (d["R_lv"] < hi)]
    if len(s) < 50 or s["L_rv"].std() < 1e-6:
        continue
    print(f"  [{lo:.1f}, {hi:.1f})      {len(s):>7} "
          f"{s['overlap'].corr(s['L_rv']):>19.3f} {s['overlap'].mean():>12.2f}")

print()
print("=" * 78)
print("2. 左部件按'右缘竖度'分组 → 组内 corr(overlap, R_lv)")
print("=" * 78)
print(f"  {'L_rv 范围':<14} {'n':>7} {'corr(overlap,R_lv)':>19} {'overlap均值':>12}")
for lo, hi in [(0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 1.01)]:
    s = d[(d["L_rv"] >= lo) & (d["L_rv"] < hi)]
    if len(s) < 50 or s["R_lv"].std() < 1e-6:
        continue
    print(f"  [{lo:.1f}, {hi:.1f})      {len(s):>7} "
          f"{s['overlap'].corr(s['R_lv']):>19.3f} {s['overlap'].mean():>12.2f}")

print()
print("=" * 78)
print("3. 二维规律表: overlap 均值 (行=左部件右缘竖度, 列=右部件左缘竖度)")
print("=" * 78)
Lb = [0, 0.15, 0.5, 1.01]
Rb = [0, 0.15, 0.5, 1.01]
Llab = ["L低(0-.15)", "L中(.15-.5)", "L高(.5-1)"]
Rlab = ["R低(0-.15)", "R中(.15-.5)", "R高(.5-1)"]
print(f"  {'':<13}" + "".join(f"{x:>22}" for x in Rlab))
for i in range(3):
    row = f"  {Llab[i]:<13}"
    for j in range(3):
        s = d[(d["L_rv"] >= Lb[i]) & (d["L_rv"] < Lb[i+1]) &
              (d["R_lv"] >= Rb[j]) & (d["R_lv"] < Rb[j+1])]
        if len(s) < 20:
            row += f"{'--':>22}"
        else:
            row += f"{s['overlap'].mean():>10.1f} (n={len(s):<5}) "
    print(row)

print()
print("  median:")
print(f"  {'':<13}" + "".join(f"{x:>22}" for x in Rlab))
for i in range(3):
    row = f"  {Llab[i]:<13}"
    for j in range(3):
        s = d[(d["L_rv"] >= Lb[i]) & (d["L_rv"] < Lb[i+1]) &
              (d["R_lv"] >= Rb[j]) & (d["R_lv"] < Rb[j+1])]
        if len(s) < 20:
            row += f"{'--':>22}"
        else:
            row += f"{s['overlap'].median():>10.1f} (n={len(s):<5}) "
    print(row)

print()
print("=" * 78)
print("4. 加 seg_ov (边缘竖笔区间真实交集) 作为自变量")
print("=" * 78)
print(f"  {'R_lv 范围':<14} {'n':>7} {'corr(ov, seg_ov)':>18}")
for lo, hi in [(0, 0.1), (0.1, 0.3), (0.3, 1.01)]:
    s = d[(d["R_lv"] >= lo) & (d["R_lv"] < hi)]
    if len(s) < 50 or s["seg_ov"].std() < 1e-6:
        continue
    print(f"  [{lo:.1f}, {hi:.1f})      {len(s):>7} {s['overlap'].corr(s['seg_ov']):>18.3f}")

print()
print("=" * 78)
print("5. 二维表: seg_ov (竖-竖交集) → overlap 均值")
print("=" * 78)
d["sbin"] = pd.cut(d["seg_ov"], [-0.001, 0.001, 0.1, 0.3, 0.6, 2],
                   labels=["0(无交集)", "0-.1", ".1-.3", ".3-.6", ">.6"])
print(f"  {'竖-竖交集':<12} {'n':>7} {'overlap均值':>12} {'std':>8} {'中位':>8}")
for b, g in d.groupby("sbin", observed=True):
    print(f"  {str(b):<12} {len(g):>7} {g['overlap'].mean():>12.2f} "
          f"{g['overlap'].std():>8.2f} {g['overlap'].median():>8.1f}")

print()
print("=" * 78)
print("6. 最干净的子集: 右部件左缘开放 (R_lv<0.1) 时, L_rv 的分档规律")
print("=" * 78)
s = d[d["R_lv"] < 0.1]
print(f"  n={len(s)}")
print(f"  {'L_rv':<14} {'n':>7} {'overlap均值':>12} {'中位':>8}")
for lo, hi in [(0, 0.05), (0.05, 0.2), (0.2, 0.5), (0.5, 0.8), (0.8, 1.01)]:
    g = s[(s["L_rv"] >= lo) & (s["L_rv"] < hi)]
    if len(g) < 20:
        continue
    print(f"  [{lo:.2f}, {hi:.2f})    {len(g):>7} {g['overlap'].mean():>12.2f} {g['overlap'].median():>8.1f}")
