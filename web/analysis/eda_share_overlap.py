# -*- coding: utf-8 -*-
"""
EDA 2: 深挖两条线
  A. 比例: "部件身份" 能解释多少? 对比 bbox比例法 / 复杂度法 / 部件表法
  B. overlap: 真正的自变量是什么? 先看"部件对固定后是否稳定"

真实 share1 = 左部件视觉宽 / (左+右)
真实 overlap = c1_str_x2 - c2_str_x1
"""
import sys, io
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"
df = pd.read_csv(CSV, encoding="utf-8-sig")

h = df[df["op"] == "⿰"].dropna(
    subset=["c1_str_x1", "c1_str_x2", "c2_str_x1", "c2_str_x2"]).copy()
h["w1"] = h["c1_str_x2"] - h["c1_str_x1"]
h["w2"] = h["c2_str_x2"] - h["c2_str_x1"]
h = h[(h["w1"] > 1) & (h["w2"] > 1)].copy()
h["share1"] = h["w1"] / (h["w1"] + h["w2"])
h["overlap"] = h["c1_str_x2"] - h["c2_str_x1"]
h = h.dropna(subset=["c1_orig_w", "c2_orig_w"])
h = h[(h["c1_orig_w"] > 0) & (h["c2_orig_w"] > 0)].copy()
h["bbox_share"] = h["c1_orig_w"] / (h["c1_orig_w"] + h["c2_orig_w"])
h["s1"] = pd.to_numeric(h["c1_strokes"], errors="coerce")
h["s2"] = pd.to_numeric(h["c2_strokes"], errors="coerce")
h = h.reset_index(drop=True)

print(f"⿰ 有效样本: {len(h)}")
print(f"share1 全局 std = {h['share1'].std():.4f}\n")

RNG = np.random.default_rng(42)
FOLD = 5
fold_id = RNG.integers(0, FOLD, len(h))


def mae(pred, truth):
    return float(np.mean(np.abs(np.asarray(pred) - np.asarray(truth))))


def cv_eval(name, fit_predict):
    """fit_predict(train_df, test_df) -> 预测数组"""
    errs = []
    for k in range(FOLD):
        tr = h[fold_id != k]
        te = h[fold_id == k]
        if len(te) == 0:
            continue
        pred = fit_predict(tr, te)
        errs.append(np.abs(np.asarray(pred) - te["share1"].values))
    allerr = np.concatenate(errs)
    print(f"  {name:<44} MAE={allerr.mean():.4f}  RMSE={np.sqrt((allerr**2).mean()):.4f}")
    return allerr.mean()


print("=" * 74)
print("A. 比例 (share1) 预测器对比 — 5-fold CV")
print("=" * 74)

# 1. 全局常数
cv_eval("① 全局常数 (mean)", lambda tr, te: np.full(len(te), tr["share1"].mean()))

# 2. bbox 比例法 (当前 kageEngine 思路)
cv_eval("② bbox 原始宽度比", lambda tr, te: te["bbox_share"].values)

# 3. 当前 kageEngine ⿰ 算法模拟: split=3+194*w1/(w1+w2), clamp[20,180]
def cur_algo(tr, te):
    w1 = te["c1_orig_w"].values.astype(float)
    w2 = te["c2_orig_w"].values.astype(float)
    w1 = np.where(w1 < 5, 5, w1)
    w2 = np.where(w2 < 5, 5, w2)
    split = 3 + 194 * w1 / (w1 + w2)
    split = np.clip(split, 20, 180)
    return (split - 3.0) / 194.0

cv_eval("③ kageEngine 当前算法 (split→share)", cur_algo)

# 4. 左部件身份表
def char1_table(tr, te):
    g = tr.groupby("c1_char")["share1"].agg(["mean", "count"])
    gmin = 3
    g = g[g["count"] >= gmin]
    glob = tr["share1"].mean()
    return te["c1_char"].map(g["mean"]).fillna(glob).values

cv_eval("④ 左部件身份表 (c1_char mean)", char1_table)

# 5. 右部件身份表 (反推: share1 = 1 - c2占比)
def char2_table(tr, te):
    tr = tr.copy()
    tr["share2"] = 1 - tr["share1"]
    g = tr.groupby("c2_char")["share2"].agg(["mean", "count"])
    g = g[g["count"] >= 3]
    glob = tr["share2"].mean()
    s2 = te["c2_char"].map(g["mean"]).fillna(glob).values
    return 1 - s2

cv_eval("⑤ 右部件身份表 (1 - c2 mean)", char2_table)

# 6. 左右部件表融合 (加权平均)
def both_table(tr, te):
    p1 = char1_table(tr, te)
    p2 = char2_table(tr, te)
    return 0.5 * p1 + 0.5 * p2

cv_eval("⑥ 左+右部件表 融合 (50/50)", both_table)

# 7. 部件表 + bbox 残差修正
def table_plus_bbox(tr, te):
    p1 = char1_table(tr, te)
    # 用训练集估计 bbox_share 的残差系数
    trp = char1_table(tr, tr)
    resid = tr["share1"].values - trp
    beta = np.polyfit(tr["bbox_share"].values, resid, 1)
    corr = np.polyval(beta, te["bbox_share"].values)
    return p1 + corr

cv_eval("⑦ 左部件表 + bbox残差线性修正", table_plus_bbox)

# 8. 部件对表 (二元交互)
def pair_table(tr, te):
    g = tr.groupby(["c1_char", "c2_char"])["share1"].agg(["mean", "count"])
    g = g[g["count"] >= 2]
    glob = tr["share1"].mean()
    key = list(zip(te["c1_char"], te["c2_char"]))
    out = []
    p1 = char1_table(tr, te)
    for i, k in enumerate(key):
        if k in g.index:
            out.append(g.loc[k, "mean"])
        else:
            out.append(p1[i])
    return np.array(out)

cv_eval("⑧ 部件对表 (c1,c2) 兜底左部件表", pair_table)

# ============================================================
print()
print("=" * 74)
print("B. overlap 分析")
print("=" * 74)

print(f"\noverlap: mean={h['overlap'].mean():.2f} std={h['overlap'].std():.2f}")

# 按部件对分组, 看组内稳定性
g = h.groupby(["c1_char", "c2_char"])["overlap"].agg(["count", "mean", "std"])
multi = g[g["count"] >= 3]
print(f"\n部件对(n>=3)组数: {len(multi)}")
print(f"  组内 std 均值: {multi['std'].mean():.2f}")
print(f"  组内 std 中位: {multi['std'].median():.2f}")
print(f"  全体 std: {h['overlap'].std():.2f}")

# 固定左部件
gl = h.groupby("c1_char")["overlap"].agg(["count", "mean", "std"])
gl = gl[gl["count"] >= 30].sort_values("mean")
print(f"\n固定左部件 (n>=30) 的 overlap:")
print(f"  {'部件':<4} {'n':>6} {'mean':>8} {'std':>8}")
for ch, row in gl.iterrows():
    print(f"  {ch:<4} {int(row['count']):>6} {row['mean']:>8.2f} {row['std']:>8.2f}")
print(f"\n  左部件组间 mean 的 std = {gl['mean'].std():.2f}")
print(f"  左部件组内 std 的均值 = {gl['std'].mean():.2f}")

# ============================================================
print()
print("=" * 74)
print("C. overlap 与各候选变量的相关性")
print("=" * 74)
h["ov"] = h["overlap"]
cands = {
    "s1 (左笔画数)": h["s1"],
    "s2 (右笔画数)": h["s2"],
    "c1_orig_w": h["c1_orig_w"],
    "c2_orig_w": h["c2_orig_w"],
    "c1_orig_x2 (左原始右边界)": h["c1_orig_x2"],
    "c2_orig_x1 (右原始左边界)": h["c2_orig_x1"],
    "c1 右空白 (200-x2)": 200 - h["c1_orig_x2"],
    "c2 左空白 (x1)": h["c2_orig_x1"],
    "左空白+右空白": (200 - h["c1_orig_x2"]) + h["c2_orig_x1"],
    "share1": h["share1"],
    "bbox_share": h["bbox_share"],
}
for name, v in cands.items():
    v = pd.to_numeric(v, errors="coerce")
    ok = v.notna() & h["ov"].notna()
    print(f"  corr(overlap, {name:<26}) = {h.loc[ok, 'ov'].corr(v[ok]):+.3f}")
