# -*- coding: utf-8 -*-
"""
EDA 7: 最终量化评估 + 排除 confound

confound 风险: 左部件右缘是横笔时, 横笔本身"伸出"部件边界,
导致 c1_str_x2 偏大 → overlap 偏大。这样规律可能只是几何效应,
而非设计者"有意让横/点边缘贴近"。

检验: 控制左部件视觉宽度 L_w 后的偏相关, 若 L_rv 效应消失则说明是几何效应。
评估: 用 L_rv / seg_ov 预测 overlap 的 MAE(5-fold) vs 常数基线。
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 240)

CSV = r"D:\2026harucpp\web\analysis\cond_features.csv"
d = pd.read_csv(CSV, encoding="utf-8-sig")

# 补上左部件视觉宽度 (来自 composition_v3)
src = pd.read_csv(r"D:\2026harucpp\scripts\output\composition_v3.csv", encoding="utf-8-sig")
src = src[src["op"] == "⿰"].copy()
src = src.dropna(subset=["c1_str_x1", "c1_str_x2"])
src["L_w"] = src["c1_str_x2"] - src["c1_str_x1"]
src["R_w"] = src["c2_str_x2"] - src["c2_str_x1"]

d = d.merge(src[["char", "L_w", "R_w"]].drop_duplicates("char"), on="char", how="left")
d = d.dropna(subset=["L_w", "R_w"])
d = d[(d["L_w"] > 1) & (d["R_w"] > 1)].reset_index(drop=True)
print(f"样本: {len(d)}\n")


def pcorr(a, b, c):
    rab, rac, rbc = a.corr(b), a.corr(c), b.corr(c)
    den = np.sqrt((1 - rac**2) * (1 - rbc**2))
    return (rab - rac * rbc) / den if den > 1e-12 else np.nan


print("=" * 78)
print("1. 偏相关 (排除几何 confound)")
print("=" * 78)
ov, lrv, rlv, lw, rw = d["overlap"], d["L_rv"], d["R_lv"], d["L_w"], d["R_w"]
print(f"  corr(overlap, L_rv)            = {ov.corr(lrv):+.3f}")
print(f"  corr(overlap, L_w)             = {ov.corr(lw):+.3f}")
print(f"  corr(L_rv, L_w)                = {lrv.corr(lw):+.3f}   <- 自变量间相关")
print(f"  corr(overlap, L_rv | L_w)      = {pcorr(ov, lrv, lw):+.3f}   <- 控制宽度后")
print(f"  corr(overlap, L_w  | L_rv)     = {pcorr(ov, lw, lrv):+.3f}")
print()
print(f"  corr(overlap, R_lv | L_rv)     = {pcorr(ov, rlv, lrv):+.3f}")
print(f"  corr(overlap, R_w  | L_rv)     = {pcorr(ov, rw, lrv):+.3f}")

print()
print("=" * 78)
print("2. 预测精度 (5-fold CV, MAE)")
print("=" * 78)
rng = np.random.default_rng(7)
fold = rng.integers(0, 5, len(d))


def cv(name, build):
    errs = []
    for k in range(5):
        tr, te = d[fold != k], d[fold == k]
        if len(te) == 0:
            continue
        pred = build(tr, te)
        errs.append(np.abs(np.asarray(pred) - te["overlap"].values))
    e = np.concatenate(errs)
    print(f"  {name:<40} MAE={e.mean():6.2f}  RMSE={np.sqrt((e**2).mean()):6.2f}")
    return e.mean()


print(f"  overlap 全局 std = {d['overlap'].std():.2f}\n")

cv("① 常数 (全局均值)", lambda tr, te: np.full(len(te), tr["overlap"].mean()))


def by_lrv(tr, te):
    """按 L_rv 分 10 档的查表"""
    bins = np.quantile(tr["L_rv"], np.linspace(0, 1, 11))
    bins[0], bins[-1] = -1, 2
    trb = pd.cut(tr["L_rv"], bins)
    tbl = tr.groupby(trb, observed=True)["overlap"].mean()
    teb = pd.cut(te["L_rv"], bins)
    return teb.map(tbl).fillna(tr["overlap"].mean()).values


cv("② L_rv 十分位查表", by_lrv)


def by_seg(tr, te):
    bins = np.quantile(tr["seg_ov"], np.linspace(0, 1, 11))
    bins[0], bins[-1] = -1, 5
    trb = pd.cut(tr["seg_ov"], bins)
    tbl = tr.groupby(trb, observed=True)["overlap"].mean()
    teb = pd.cut(te["seg_ov"], bins)
    return teb.map(tbl).fillna(tr["overlap"].mean()).values


cv("③ seg_ov 十分位查表", by_seg)


def lin_lrv(tr, te):
    b = np.polyfit(tr["L_rv"], tr["overlap"], 1)
    return np.polyval(b, te["L_rv"])


cv("④ linear(L_rv)", lin_lrv)


def lin_both(tr, te):
    X = np.column_stack([np.ones(len(tr)), tr["L_rv"], tr["R_lv"], tr["L_w"], tr["R_w"]])
    b, *_ = np.linalg.lstsq(X, tr["overlap"].values, rcond=None)
    Xt = np.column_stack([np.ones(len(te)), te["L_rv"], te["R_lv"], te["L_w"], te["R_w"]])
    return Xt @ b


cv("⑤ linear(L_rv, R_lv, L_w, R_w)", lin_both)


def lrv_plus_char(tr, te):
    """L_rv 分档表 + 左部件均值修正"""
    base = by_lrv(tr, te)
    gm = tr.groupby("c1")["overlap"].mean()
    glob = tr["overlap"].mean()
    adj = (te["c1"].map(gm).fillna(glob).values - glob) * 0.5
    return base + adj


cv("⑥ L_rv 查表 + 左部件身份修正(0.5)", lrv_plus_char)


def char_only(tr, te):
    gm = tr.groupby("c1")["overlap"].mean()
    glob = tr["overlap"].mean()
    return te["c1"].map(gm).fillna(glob).values


cv("⑦ 仅左部件身份 (对照)", char_only)

print()
print("=" * 78)
print("3. 最终一维规律表 (可直接落地)")
print("=" * 78)
print(f"  {'L_rv 区间':<16} {'n':>7} {'overlap均值':>12} {'中位':>8} {'建议公式值':>12}")
for lo, hi in [(0, 0.05), (0.05, 0.2), (0.2, 0.5), (0.5, 0.8), (0.8, 1.01)]:
    g = d[(d["L_rv"] >= lo) & (d["L_rv"] < hi)]
    if len(g) < 20:
        continue
    print(f"  [{lo:.2f}, {hi:.2f})      {len(g):>7} {g['overlap'].mean():>12.2f} "
          f"{g['overlap'].median():>8.1f} {round(g['overlap'].mean()):>12.0f}")

# 线性拟合系数
b = np.polyfit(d["L_rv"], d["overlap"], 1)
print(f"\n  线性拟合: overlap ≈ {b[1]:+.2f} {b[0]:+.2f} * L_rv")
print(f"  (L_rv=0 → {b[1]:+.1f}px 重叠;  L_rv=1 → {b[0]+b[1]:+.1f}px)")

# 分档建议表
print(f"\n  分段建议 (5档):")
qs = [0, 0.05, 0.2, 0.5, 0.8, 1.01]
vals = []
for i in range(5):
    g = d[(d["L_rv"] >= qs[i]) & (d["L_rv"] < qs[i + 1])]
    vals.append(round(g["overlap"].mean()) if len(g) > 0 else 0)
print(f"    {vals}")
