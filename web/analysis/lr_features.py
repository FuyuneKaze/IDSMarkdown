# -*- coding: utf-8 -*-
"""
左右比例 — 特征寻优 (干净数据)

方法: 按"左部件"聚合 (每个部件一个样本点), 测各特征与 share_L 的关系。
     另测关键假设: 是否与"部件独立成字时的宽度"的压缩比有关。
"""
import sys, io, json
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
d = pd.read_csv(r"D:\2026harucpp\web\analysis\lr_data.csv", encoding="utf-8-sig")
print(f"字对数: {len(d)}\n")

db = json.load(open(CORE, encoding="utf-8"))["glyphs"]


def collect(data, rect=(0.0, 0.0, 200.0, 200.0), visited=None, depth=0):
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
        p = seg.split(":")
        if p[0] == "99" and len(p) >= 8:
            name = p[7].split("@")[0]
            try:
                bx1, by1, bx2, by2 = int(p[3]), int(p[4]), int(p[5]), int(p[6])
            except ValueError:
                continue
            if name in db and name not in visited:
                visited.add(name)
                for pts in collect(db[name], (bx1, by1, bx2, by2), visited, depth + 1):
                    out.append([(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts])
        elif p[0] in ("1", "2", "3", "4", "6", "7"):
            pts = []
            for i in range(3, len(p) - 1, 2):
                try:
                    pts.append((int(p[i]), int(p[i + 1])))
                except ValueError:
                    pass
            if pts:
                out.append([(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts])
    return out


def bb_ink(strokes):
    if not strokes:
        return None
    xs = [x for pts in strokes for x, _ in pts]
    ys = [y for pts in strokes for _, y in pts]
    ink = sum(np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
              for pts in strokes for i in range(len(pts) - 1))
    return (min(xs), min(ys), max(xs), max(ys), ink)


# ---- 每个部件的"独立成字"尺寸 (标准体 u<hex> / u<hex>-j) ----
stand_cache = {}
def standalone(ch):
    if ch in stand_cache:
        return stand_cache[ch]
    cp = ord(ch)
    for nm in (f"u{cp:x}", f"u{cp:x}-j", f"u{cp:x}-k", f"u{cp:x}-v", f"u{cp:x}-g"):
        if nm in db:
            r = bb_ink(collect(db[nm]))
            if r:
                stand_cache[ch] = (r[2] - r[0], r[3] - r[1], r[4], nm)
                return stand_cache[ch]
    stand_cache[ch] = None
    return None


# ---- 按左部件聚合 ----
g = d.groupby("c1")
recs = []
for ch, sub in g:
    if len(sub) < 20:
        continue
    st = standalone(ch)
    if st is None:
        continue
    sw, sh, sink, snm = st
    if sw <= 0:
        continue
    recs.append({
        "ch": ch, "n": len(sub),
        "share": sub["share_L"].mean(),
        "share_std": sub["share_L"].std(),
        # 左变体特征
        "L0w": sub["L0w"].mean(),
        "L0h": sub["L0h"].mean(),
        "L0ink": sub["L0ink"].mean(),
        "L0strokes": sub["L0strokes"].mean(),
        "L0pts": sub["L0pts"].mean(),
        "L0x2": sub["L0x2"].mean(),
        # 独立字特征
        "Sw": sw, "Sh": sh, "Sink": sink,
        # 派生
        "ratio_w": sub["L0w"].mean() / sw,
        "ratio_ink": sub["L0ink"].mean() / max(sink, 1e-6),
        "L0_ar": sub["L0w"].mean() / max(sub["L0h"].mean(), 1e-6),
        "S_ar": sw / max(sh, 1e-6),
    })

a = pd.DataFrame(recs)
print(f"按左部件聚合: {len(a)} 个部件 (每个 n>=20)\n")
a.to_csv(r"D:\2026harucpp\web\analysis\lr_by_component.csv", index=False, encoding="utf-8-sig")

print("=" * 84)
print("1. 各特征与 share_L 的相关性 (按部件聚合, 每部件一个点)")
print("=" * 84)
feats = {
    "L0w 左变体自身宽": "L0w",
    "L0h 左变体自身高": "L0h",
    "L0ink 左变体墨量": "L0ink",
    "L0strokes 笔画数": "L0strokes",
    "L0pts 控制点数": "L0pts",
    "L0x2 左变体右边界": "L0x2",
    "Sw 独立字宽": "Sw",
    "Sh 独立字高": "Sh",
    "Sink 独立字墨量": "Sink",
    "ratio_w 宽度压缩比 L0w/Sw": "ratio_w",
    "ratio_ink 墨量比": "ratio_ink",
    "L0_ar 左变体宽高比": "L0_ar",
    "S_ar 独立字宽高比": "S_ar",
    "n 样本数": "n",
}
res = []
for label, col in feats.items():
    c = a["share"].corr(a[col])
    res.append((abs(c), c, label))
res.sort(reverse=True)
for _, c, label in res:
    bar = "█" * int(abs(c) * 40)
    print(f"  {label:<28} r={c:+.3f}  {bar}")

print()
print("=" * 84)
print("2. 关键假设: 宽度压缩比是否稳定? (左变体宽 / 独立字宽)")
print("=" * 84)
print(f"  ratio_w: mean={a['ratio_w'].mean():.3f} std={a['ratio_w'].std():.3f} "
      f"median={a['ratio_w'].median():.3f}")
print("  分位: " + "  ".join(f"p{q}={np.percentile(a['ratio_w'],q):.3f}" for q in [5, 25, 50, 75, 95]))
print(f"\n  {'部件':<5} {'n':>5} {'share':>7} {'L0w':>6} {'Sw':>6} {'压缩比':>7} {'墨量比':>7}")
for _, r in a.sort_values("share").iterrows():
    if r["n"] < 60:
        continue
    print(f"  {r['ch']:<5} {int(r['n']):>5} {r['share']:>7.3f} {r['L0w']:>6.1f} "
          f"{r['Sw']:>6.1f} {r['ratio_w']:>7.3f} {r['ratio_ink']:>7.3f}")

print()
print("=" * 84)
print("3. 用'左变体自身宽 L0w' 直接预测 share_L")
print("=" * 84)
X = a["L0w"].values
y = a["share"].values
b = np.polyfit(X, y, 1)
print(f"  线性: share = {b[1]:+.4f} {b[0]:+.5f} * L0w")
print(f"  R² = {np.corrcoef(X, y)[0,1]**2:.4f}")

# 多元: 宽 + 墨量
X2 = np.column_stack([np.ones(len(a)), a["L0w"], a["L0ink"], a["L0strokes"]])
b2, *_ = np.linalg.lstsq(X2, y, rcond=None)
pred = X2 @ b2
print(f"\n  多元 (L0w + L0ink + L0strokes):")
print(f"    share = {b2[0]:+.4f} {b2[1]:+.5f}*L0w {b2[2]:+.5f}*L0ink {b2[3]:+.5f}*L0strokes")
ss = ((y - pred) ** 2).sum()
st = ((y - y.mean()) ** 2).sum()
print(f"    R² = {1 - ss/st:.4f}")

# 用"独立字宽"预测 (假设: 越宽的部件作为左旁也占越宽)
b3 = np.polyfit(a["Sw"], y, 1)
print(f"\n  用独立字宽 Sw 预测: R² = {np.corrcoef(a['Sw'], y)[0,1]**2:.4f}")
b4 = np.polyfit(a["Sink"], y, 1)
print(f"  用独立字墨量 Sink 预测: R² = {np.corrcoef(a['Sink'], y)[0,1]**2:.4f}")
