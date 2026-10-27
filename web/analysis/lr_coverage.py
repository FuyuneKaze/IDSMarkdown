# -*- coding: utf-8 -*-
"""覆盖率优化: 阈值 / 繁简归类 对覆盖率与精度的影响"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

d = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_data.csv", encoding="utf-8-sig")
share = d["share_L"].values
print(f"字对: {len(d)}\n")

print("=" * 74)
print("阈值对覆盖率/精度的影响 (字符级表)")
print("=" * 74)
print(f"  {'MIN_N':>6} {'左表':>5} {'右表':>5} {'覆盖%':>7} {'表内MAE':>9} {'表外MAE(bbox兜底)':>18}")
for mn in [1, 3, 5, 8, 15, 30]:
    tL = {ch: s["Lw"].mean() for ch, s in d.groupby("c1") if len(s) >= mn}
    tR = {ch: s["Rw"].mean() for ch, s in d.groupby("c2") if len(s) >= mn}
    cov = d["c1"].isin(tL) & d["c2"].isin(tR)
    if cov.sum() > 0:
        sub = d[cov]
        sL = sub["c1"].map(tL).values
        sR = sub["c2"].map(tR).values
        p = sL / (sL + sR)
        mae_in = np.abs(p - sub["share_L"].values).mean()
    else:
        mae_in = np.nan
    if (~cov).sum() > 0:
        o = d[~cov]
        bw = o["L0w"].values
        p2 = bw / (bw + o["R0w"].values)
        mae_out = np.abs(p2 - o["share_L"].values).mean()
    else:
        mae_out = np.nan
    print(f"  {mn:>6} {len(tL):>5} {len(tR):>5} {cov.mean()*100:>6.1f}% {mae_in:>9.4f} {mae_out:>18.4f}")

print()
print("=" * 74)
print("为什么低? 检查'覆盖失败'的构成 (MIN_N=3)")
print("=" * 74)
tL = {ch: s["Lw"].mean() for ch, s in d.groupby("c1") if len(s) >= 3}
tR = {ch: s["Rw"].mean() for ch, s in d.groupby("c2") if len(s) >= 3}
inL = d["c1"].isin(tL)
inR = d["c2"].isin(tR)
print(f"  左部件缺失: {(~inL).sum()}  ({(~inL).mean()*100:.1f}%)")
print(f"  右部件缺失: {(~inR).sum()}  ({(~inR).mean()*100:.1f}%)")
print(f"  两者都缺:   {((~inL) & (~inR)).sum()}")
print(f"  仅左缺:     {((~inL) & inR).sum()}")
print(f"  仅右缺:     {(inL & (~inR)).sum()}")

print(f"\n  缺右部件的 top (说明是长尾生僻部件):")
for ch, c in d.loc[~inR, "c2"].value_counts().head(10).items():
    print(f"    {ch}: {c}")
print(f"  缺左部件的 top:")
for ch, c in d.loc[~inL, "c1"].value_counts().head(10).items():
    print(f"    {ch}: {c}")

print()
print("=" * 74)
print("长尾分析: 字对按 左部件频次 分布")
print("=" * 74)
vc = d["c1"].value_counts()
print(f"  左部件总数: {len(vc)}")
print(f"  频次>=30: {(vc>=30).sum()} 个, 覆盖字对 {vc[vc>=30].sum()} ({vc[vc>=30].sum()/len(d)*100:.1f}%)")
print(f"  频次>=3:  {(vc>=3).sum()} 个, 覆盖字对 {vc[vc>=3].sum()} ({vc[vc>=3].sum()/len(d)*100:.1f}%)")
print(f"  频次==1:  {(vc==1).sum()} 个")
