# -*- coding: utf-8 -*-
"""
左右比例 — 模型检验

对比几个自然假设:
  M1 share = Sw_L / (Sw_L + Sw_R)          部件独立宽度比
  M2 share = L0w / (L0w + Rw)              变体实际宽度比 (查表上界)
  M3 用 Sw 预测 L0w, 再算 share
  M4 分段: 偏旁型(Sw小) 不压缩 / 独立字型(Sw大) 压缩
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

d = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_data.csv", encoding="utf-8-sig")
a = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_by_component.csv", encoding="utf-8-sig")
print(f"字对 {len(d)}   部件 {len(a)}\n")

share = d["share_L"].values

print("=" * 80)
print("M2 (上界): 直接用变体实际宽度算 share — 这已是'查表'结果")
print("=" * 80)
m2 = d["Lw"].values / (d["Lw"].values + d["Rw"].values)
print(f"  MAE = {np.abs(m2 - share).mean():.4f}   R² = {np.corrcoef(m2, share)[0,1]**2:.4f}")
print(f"  (说明 share_L 与 Lw/(Lw+Rw) 的差异 = 测算细节)")

print()
print("=" * 80)
print("M1: share = Sw_L / (Sw_L + Sw_R)  — 用'部件独立宽度比'直接预测")
print("=" * 80)
# 需要每个字的左右部件的独立宽度
a_map = dict(zip(a["ch"], a["Sw"]))
swL = d["c1"].map(a_map)
swR = d["c2"].map(a_map)
ok = swL.notna() & swR.notna()
print(f"  可算样本: {ok.sum()} / {len(d)}")
if ok.sum() > 100:
    m1 = (swL[ok] / (swL[ok] + swR[ok])).values
    y = share[ok.values]
    print(f"  MAE = {np.abs(m1 - y).mean():.4f}   R² = {np.corrcoef(m1, y)[0,1]**2:.4f}")
    print(f"  偏差 mean = {(m1 - y).mean():+.4f}  (正=高估左占比)")

print()
print("=" * 80)
print("M3: 用经验关系 L0w ≈ f(Sw) 预测左宽, 再算 share")
print("=" * 80)
b = np.polyfit(a["Sw"], a["L0w"], 1)
print(f"  线性 f: L0w = {b[1]:+.2f} {b[0]:+.4f}*Sw   拟合 R²={np.corrcoef(a['Sw'],a['L0w'])[0,1]**2:.4f}")
# 分段: 用中位数分两组
med = a["Sw"].median()
lo = a[a["Sw"] <= med]
hi = a[a["Sw"] > med]
b_lo = np.polyfit(lo["Sw"], lo["L0w"], 1)
b_hi = np.polyfit(hi["Sw"], hi["L0w"], 1)
print(f"  分段 (切点 Sw={med:.0f}):")
print(f"    Sw<={med:.0f}: L0w = {b_lo[1]:+.2f} {b_lo[0]:+.4f}*Sw  (n={len(lo)})")
print(f"    Sw> {med:.0f}: L0w = {b_hi[1]:+.2f} {b_hi[0]:+.4f}*Sw  (n={len(hi)})")
r2_lo = np.corrcoef(lo["Sw"], lo["L0w"])[0, 1] ** 2
r2_hi = np.corrcoef(hi["Sw"], hi["L0w"])[0, 1] ** 2
print(f"    分段 R²: {r2_lo:.4f} (低组) / {r2_hi:.4f} (高组)")

print()
print("=" * 80)
print("压缩比分析: L0w/Sw 的分布 (找是否存在自然分界)")
print("=" * 80)
r = a["ratio_w"]
print("  直方图 (0.05 桶):")
bins = np.arange(0.25, 1.06, 0.05)
hist, edges = np.histogram(r, bins=bins)
for i, h in enumerate(hist):
    if h == 0:
        continue
    bar = "█" * h
    print(f"    [{edges[i]:.2f},{edges[i+1]:.2f})  {h:>3}  {bar}")

print()
print("=" * 80)
print("按'压缩比'排序看部件, 找类别结构")
print("=" * 80)
a2 = a[a["n"] >= 60].sort_values("ratio_w")
print(f"  {'部件':<5} {'n':>5} {'Sw':>6} {'L0w':>6} {'压缩比':>7} {'share':>7}")
prev = None
for _, row in a2.iterrows():
    print(f"  {row['ch']:<5} {int(row['n']):>5} {row['Sw']:>6.1f} {row['L0w']:>6.1f} "
          f"{row['ratio_w']:>7.3f} {row['share']:>7.3f}")

print()
print("=" * 80)
print("关键检验: L0w 是否有'上限'? (作为左旁最多占多宽)")
print("=" * 80)
print(f"  L0w: mean={a['L0w'].mean():.1f} std={a['L0w'].std():.1f} "
      f"min={a['L0w'].min():.1f} max={a['L0w'].max():.1f}")
print("  分位: " + "  ".join(f"p{q}={np.percentile(a['L0w'],q):.1f}" for q in [5, 25, 50, 75, 95]))
print(f"  L0w 与 Sw 的相关: {a['L0w'].corr(a['Sw']):+.3f}")
print(f"  L0w 与 share 的相关: {a['L0w'].corr(a['share']):+.3f}")
print(f"  Sw  与 share 的相关: {a['Sw'].corr(a['share']):+.3f}")

# Sw 大的部件里 L0w 的上限
big = a[a["Sw"] > 150]
print(f"\n  Sw>150 的部件 (n={len(big)}): L0w mean={big['L0w'].mean():.1f} "
      f"max={big['L0w'].max():.1f} std={big['L0w'].std():.1f}")
print(f"  → 独立字型部件作左旁, L0w 收敛到 {big['L0w'].mean():.0f} 左右")
