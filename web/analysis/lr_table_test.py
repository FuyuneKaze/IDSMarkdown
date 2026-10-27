# -*- coding: utf-8 -*-
"""
决定性验证: 左旁宽度是"约定属性(可查表)" 还是 "随对手变化"?

V1 固定左部件, 看它的实际宽度 Lw 是否稳定 (关键!)
V2 固定右部件, 看 Rw 是否稳定
V3 对比预测方案: 常数 / Sw模型 / 查表
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

d = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_data.csv", encoding="utf-8-sig")
print(f"字对: {len(d)}\n")

# 注意: Lw/Rw 是"映射到矩形后"的宽度. 单独看变体自身宽度 L0w 更纯粹.
d["Lfac"] = d["Lw"] / d["L0w"].replace(0, np.nan)   # 矩形缩放因子

print("=" * 82)
print("V1. 固定左部件 → 它的实际宽度 Lw 稳定吗? ★决定性")
print("=" * 82)
print(f"  {'部件':<5} {'n':>5} {'L0w均值':>8} {'L0w_std':>8} {'Lw均值':>8} {'Lw_std':>8} "
      f"{'缩放因子':>9} {'share_std':>9}")
g = d.groupby("c1")
recs = []
for ch, s in g:
    if len(s) < 40:
        continue
    recs.append((ch, len(s), s["L0w"].mean(), s["L0w"].std(), s["Lw"].mean(), s["Lw"].std(),
                 s["Lfac"].mean(), s["share_L"].std()))
recs.sort(key=lambda x: x[1], reverse=True)
for r in recs[:20]:
    print(f"  {r[0]:<5} {r[1]:>5} {r[2]:>8.1f} {r[3]:>8.2f} {r[4]:>8.1f} {r[5]:>8.2f} "
          f"{r[6]:>9.3f} {r[7]:>9.4f}")

L0w_stds = np.array([r[3] for r in recs])
Lw_stds = np.array([r[5] for r in recs])
print(f"\n  L0w (变体自身宽) 组内 std: 均值={L0w_stds.mean():.2f} 中位={np.median(L0w_stds):.2f}")
print(f"  Lw  (映射后宽)   组内 std: 均值={Lw_stds.mean():.2f} 中位={np.median(Lw_stds):.2f}")
print(f"  → L0w 近乎恒定说明它是变体的固定属性")

print()
print("=" * 82)
print("V2. 固定右部件 → Rw 稳定吗?")
print("=" * 82)
g2 = d.groupby("c2")
recs2 = []
for ch, s in g2:
    if len(s) < 40:
        continue
    recs2.append((ch, len(s), s["R0w"].mean(), s["R0w"].std(), s["Rw"].mean(), s["Rw"].std()))
recs2.sort(key=lambda x: x[1], reverse=True)
print(f"  {'部件':<5} {'n':>5} {'R0w均值':>8} {'R0w_std':>8} {'Rw均值':>8} {'Rw_std':>8}")
for r in recs2[:16]:
    print(f"  {r[0]:<5} {r[1]:>5} {r[2]:>8.1f} {r[3]:>8.2f} {r[4]:>8.1f} {r[5]:>8.2f}")
if recs2:
    a1 = np.array([r[3] for r in recs2])
    a2 = np.array([r[5] for r in recs2])
    print(f"\n  R0w 组内 std: 均值={a1.mean():.2f}   Rw 组内 std: 均值={a2.mean():.2f}")

print()
print("=" * 82)
print("V3. 预测方案对比 (share_L, MAE)")
print("=" * 82)
share = d["share_L"].values

# 方案 0: 常数
c0 = np.full(len(d), share.mean())
print(f"  ① 常数(全局均值 {share.mean():.3f})              MAE={np.abs(c0-share).mean():.4f}")

# 方案 1: 查左部件表 (用左部件平均 share)
tbl_c1 = d.groupby("c1")["share_L"].transform("mean")
print(f"  ② 查表: 左部件平均 share                 MAE={np.abs(tbl_c1.values-share).mean():.4f}")

# 方案 2: 左旁宽度表 + 右旁宽度表 → 算 share
Lw_tbl = d.groupby("c1")["Lw"].transform("mean")
Rw_tbl = d.groupby("c2")["Rw"].transform("mean")
m2 = Lw_tbl.values / (Lw_tbl.values + Rw_tbl.values)
print(f"  ③ 左宽表/(左宽表+右宽表)                 MAE={np.abs(m2-share).mean():.4f}")

# 方案 3: 用变体自身宽 L0w 表 + R0w 表
L0_tbl = d.groupby("c1")["L0w"].transform("mean")
R0_tbl = d.groupby("c2")["R0w"].transform("mean")
m3 = L0_tbl.values / (L0_tbl.values + R0_tbl.values)
print(f"  ④ 变体宽表/(变体宽表+变体宽表)            MAE={np.abs(m3-share).mean():.4f}")

# 方案 4: 真实值(同一变体, 即完全查表到变体级)
m4 = d["L0w"].values / (d["L0w"].values + d["R0w"].values)
print(f"  ⑤ 变体实际宽比 (不做矩形缩放)            MAE={np.abs(m4-share).mean():.4f}")

# 方案 5: Sw 模型
a = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_by_component.csv", encoding="utf-8-sig")
swmap = dict(zip(a["ch"], a["Sw"]))
swL = d["c1"].map(swmap)
swR = d["c2"].map(swmap)
ok = swL.notna() & swR.notna()
m5 = np.full(len(d), np.nan)
m5[ok.values] = (swL[ok] / (swL[ok] + swR[ok])).values
print(f"  ⑥ Sw 独立宽比 (仅 {ok.sum()} 样本可算)      "
      f"MAE={np.abs(m5[ok.values]-share[ok.values]).mean():.4f}")

print()
print("=" * 82)
print("V4. 变体级查表: 同一变体在不同字里宽度是否相同?")
print("=" * 82)
gv = d.groupby("Lvar")
rows = []
for v, s in gv:
    if len(s) < 30:
        continue
    rows.append((v, len(s), s["L0w"].mean(), s["L0w"].std(), s["Lw"].mean(), s["Lw"].std()))
rows.sort(key=lambda x: -x[1])
print(f"  {'变体':<18} {'n':>5} {'L0w':>7} {'std':>6} {'Lw':>7} {'std':>6}")
for r in rows[:18]:
    print(f"  {r[0]:<18} {r[1]:>5} {r[2]:>7.1f} {r[3]:>6.2f} {r[4]:>7.1f} {r[5]:>6.2f}")
if rows:
    print(f"\n  L0w std 均值 = {np.mean([r[3] for r in rows]):.2f}  (0 = 完全固定)")
    print(f"  Lw  std 均值 = {np.mean([r[5] for r in rows]):.2f}")
