# -*- coding: utf-8 -*-
"""
生成可落地的"左右宽度表" + 覆盖率验证

结论回顾:
  - 左/右旁宽度 = 变体的固有常数 (L0w std = 0.00)
  - 不存在"几何特征 → 比例"的连续函数 (Sw 模型 MAE 0.0777 > 常数 0.0720)
  - 查表 MAE 0.0208 (常数 0.0720)

本脚本产物:
  lr_table.json    { left: {char: 宽度}, right: {char: 宽度} }  (供引擎查表)
  覆盖率 & 兜底精度统计
"""
import sys, io, json
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 200)

d = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_data.csv", encoding="utf-8-sig")
print(f"字对: {len(d)}\n")

# ---------- 1. 字符级表 (用映射后宽度 Lw / Rw, 因为它含矩形缩放) ----------
MIN_N = 1          # 覆盖 100% (MIN_N=1 时 MAE 仍为 0.0208)
tbl_L, tbl_R = {}, {}
for ch, s in d.groupby("c1"):
    if len(s) >= MIN_N:
        tbl_L[ch] = round(float(s["Lw"].mean()), 2)
for ch, s in d.groupby("c2"):
    if len(s) >= MIN_N:
        tbl_R[ch] = round(float(s["Rw"].mean()), 2)

print("=" * 78)
print("1. 覆盖率")
print("=" * 78)
tot = len(d)
cov = d["c1"].isin(tbl_L) & d["c2"].isin(tbl_R)
print(f"  表条目: 左 {len(tbl_L)} 个部件, 右 {len(tbl_R)} 个部件")
print(f"  字对覆盖: {cov.sum()} / {tot} = {cov.mean()*100:.1f}%")
print(f"  未覆盖的右部件 (最常见): ")
miss = d.loc[~cov, "c2"].value_counts().head(8)
for ch, c in miss.items():
    print(f"    {ch}: {c}")

# ---------- 2. 精度: 表内 vs 表外 ----------
print()
print("=" * 78)
print("2. 精度 (share_L 的 MAE)")
print("=" * 78)
share = d["share_L"].values
gL = d.groupby("c1")["Lw"].transform("mean")
gR = d.groupby("c2")["Rw"].transform("mean")

pred_all = (gL / (gL + gR)).values
print(f"  全部字对 (含小样本部件):      MAE={np.abs(pred_all-share).mean():.4f}")

sub = d[cov].copy()
sL = sub["c1"].map(tbl_L).values
sR = sub["c2"].map(tbl_R).values
p_sub = sL / (sL + sR)
y_sub = sub["share_L"].values
print(f"  表覆盖的字对 ({len(sub)}):           MAE={np.abs(p_sub-y_sub).mean():.4f}")

# 表外: 用 bbox 比例兜底
out = d[~cov].copy()
if len(out) > 0:
    bw = out["L0w"].values
    # 兜底1: 用 bbox 宽 (变体自身宽) 比例
    p_out1 = bw / (bw + out["R0w"].values)
    print(f"  表外 ({len(out)}): bbox宽比兜底        MAE={np.abs(p_out1-out['share_L'].values).mean():.4f}")
    print(f"  表外: 常数兜底                       MAE={np.abs(out['share_L'].mean()-out['share_L'].values).mean():.4f}")

# ---------- 3. 变体级表 (更精确) ----------
print()
print("=" * 78)
print("3. 变体级表 (最精确, 需先选对变体)")
print("=" * 78)
vtL, vtR = {}, {}
for v, s in d.groupby("Lvar"):
    if len(s) >= 5:
        vtL[v] = round(float(s["Lw"].mean()), 2)
for v, s in d.groupby("Rvar"):
    if len(s) >= 5:
        vtR[v] = round(float(s["Rw"].mean()), 2)
cov2 = d["Lvar"].isin(vtL) & d["Rvar"].isin(vtR)
print(f"  变体表: 左 {len(vtL)}, 右 {len(vtR)}   覆盖 {cov2.mean()*100:.1f}%")
sub2 = d[cov2]
p2 = (sub2["Lvar"].map(vtL).values /
      (sub2["Lvar"].map(vtL).values + sub2["Rvar"].map(vtR).values))
print(f"  变体级查表 MAE = {np.abs(p2-sub2['share_L'].values).mean():.4f}")

# ---------- 4. 输出 ----------
print()
print("=" * 78)
print("4. 输出表文件")
print("=" * 78)
outj = {
    "description": "左右部件宽度表 (从 1387455 个真实字形统计; 单位: 200 空间宽度)",
    "source": "core_glyphs.json + ids_lv1.txt",
    "samples": int(tot),
    "left": tbl_L,
    "right": tbl_R,
    "left_variant": vtL,
    "right_variant": vtR,
}
p = r"D:\2026harucpp\web\analysis\lr_table.json"
json.dump(outj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"  {p}")

print(f"\n  左宽度表样例 (前 20):")
for ch, w in sorted(tbl_L.items(), key=lambda x: x[1])[:20]:
    print(f"    {ch} → {w}")
print(f"  右宽度表样例 (前 12, 按出现频次):")
for ch, c in d["c2"].value_counts().head(12).items():
    if ch in tbl_R:
        print(f"    {ch} → {tbl_R[ch]}   (n={c})")
