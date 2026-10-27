# -*- coding: utf-8 -*-
"""
EDA 12 (终局验证): 关键悖论 — overlap 到底需不需要"预测"?

假说: 位置信息烘在变体里 → 同一变体在不同字中应被赋予"一致的矩形",
      则 overlap 是变体的确定属性, 组字只需"查表 + 铺开", 无需任何统计预测。

验证:
  V1 变体的矩形一致性: 每个变体名的矩形是固定的吗?
  V2 "全画布铺开"策略的 overlap 误差
  V3 若用"变体最常见矩形"(查表) 而非真实矩形, 误差多大?
"""
import sys, io, json, re
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
db = json.load(open(CORE, encoding="utf-8"))["glyphs"]

# ---- 收集所有 2-ref 拼接字 (穿透 alias) ----
def parse_refs(data):
    refs, hs = [], False
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
        elif p[0] in ("1", "2", "3", "4", "6", "7", "0"):
            hs = True
    return refs, hs


names = [k for k in db if re.fullmatch(r"u[4-9][0-9a-f]{3}", k)]
names += [k for k in db if re.fullmatch(r"u[23][0-9a-f]{4}", k)]
print(f"扫描 {len(names)} 个标准字 ...")

pairs = []
for nm in names:
    cur, seen, hops = db[nm], set(), 0
    while hops < 8:
        refs, hs = parse_refs(cur)
        if len(refs) == 1 and not hs:
            nxt = refs[0][4].split("@")[0]
            if nxt in db and nxt not in seen:
                seen.add(nxt); cur = db[nxt]; hops += 1; continue
        break
    refs, hs = parse_refs(cur)
    if len(refs) == 2:
        pairs.append(sorted(refs, key=lambda r: r[0]))
print(f"2-ref 拼接字: {len(pairs)}\n")

# ============================================================
print("=" * 78)
print("V1. 变体的矩形一致性 — 同一变体在不同字里矩形是否相同? ★关键")
print("=" * 78)
vrect = defaultdict(Counter)
for refs in pairs:
    for (x1, y1, x2, y2, rn) in refs:
        vrect[rn][(x1, y1, x2, y2)] += 1

stats = []
for rn, c in vrect.items():
    tot = sum(c.values())
    if tot < 10:
        continue
    top, topn = c.most_common(1)[0]
    stats.append((rn, tot, len(c), topn / tot, top))
stats.sort(key=lambda x: -x[1])
print(f"  （n>=10 的变体: {len(stats)} 个）")
print(f"  {'变体名':<26} {'出现':>6} {'唯一矩形数':>10} {'众数占比':>9}  众数矩形")
for rn, tot, nuniq, ratio, top in stats[:24]:
    print(f"  {rn:<26} {tot:>6} {nuniq:>10} {ratio*100:>8.1f}%  {top}")

if stats:
    r = np.array([s[3] for s in stats])
    u = np.array([s[2] for s in stats])
    print(f"\n  众数占比: 均值={r.mean()*100:.1f}% 中位={np.median(r)*100:.1f}%")
    print(f"  ==1 (矩形完全固定) 的变体占比: {(u == 1).mean()*100:.1f}%")
    print(f"  众数占比 >90% 的变体占比: {(r > 0.9).mean()*100:.1f}%")

# ============================================================
print()
print("=" * 78)
print("V2. '全画布铺开'策略 vs 真实矩形")
print("=" * 78)


def collect_strokes(data, db, rect=(0, 0, 200, 200), visited=None, depth=0):
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
                for k, pts in collect_strokes(db[name], db, (bx1, by1, bx2, by2), visited, depth + 1):
                    out.append((k, [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
        elif p[0] in ("1", "2", "3", "4", "6", "7"):
            pts = []
            for i in range(3, len(p) - 1, 2):
                try:
                    pts.append((int(p[i]), int(p[i + 1])))
                except ValueError:
                    pass
            if pts:
                out.append((p[0], [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
    return out


def bbox_of(strokes):
    if not strokes:
        return None
    xs = [x for _, pts in strokes for x, _ in pts]
    ys = [y for _, pts in strokes for _, y in pts]
    return (min(xs), min(ys), max(xs), max(ys))


rng = np.random.default_rng(3)
sample = [pairs[i] for i in rng.choice(len(pairs), size=min(3000, len(pairs)), replace=False)]

bbcache = {}
def variant_bbox(rn):
    if rn in bbcache:
        return bbcache[rn]
    data = db.get(rn) or db.get(rn.split("@")[0])
    b = bbox_of(collect_strokes(data, db)) if data else None
    bbcache[rn] = b
    return b


res_full, res_real, res_tbl = [], [], []
tbl = {rn: c.most_common(1)[0][0] for rn, c in vrect.items()}

for refs in sample:
    (ax1, ay1, ax2, ay2, an), (bx1, by1, bx2, by2, bn) = refs
    ba, bb = variant_bbox(an), variant_bbox(bn)
    if ba is None or bb is None:
        continue

    def mapped(b, rx1, ry1, rx2, ry2):
        return (rx1 + b[0] / 200 * (rx2 - rx1), ry1 + b[1] / 200 * (ry2 - ry1),
                rx1 + b[2] / 200 * (rx2 - rx1), ry1 + b[3] / 200 * (ry2 - ry1))

    # 真实矩形
    ma = mapped(ba, ax1, ay1, ax2, ay2)
    mb = mapped(bb, bx1, by1, bx2, by2)
    res_real.append(ma[2] - mb[0])

    # 全画布铺开
    ma2 = mapped(ba, 0, 0, 200, 200)
    mb2 = mapped(bb, 0, 0, 200, 200)
    res_full.append(ma2[2] - mb2[0])

    # 查表: 用变体的最常见矩形
    ta = tbl.get(an, (0, 0, 200, 200))
    tb = tbl.get(bn, (0, 0, 200, 200))
    ma3 = mapped(ba, ta[0], ta[1], ta[2], ta[3])
    mb3 = mapped(bb, tb[0], tb[1], tb[2], tb[3])
    res_tbl.append(ma3[2] - mb3[0])

r_real = np.array(res_real)
print(f"  样本: {len(r_real)}")
print(f"  真实矩形   : mean={r_real.mean():7.2f} std={r_real.std():6.2f}")
print(f"  全画布铺开 : mean={np.mean(res_full):7.2f} std={np.std(res_full):6.2f}  "
      f"MAE vs 真实={np.abs(np.array(res_full)-r_real).mean():.2f}")
print(f"  查表矩形   : mean={np.mean(res_tbl):7.2f} std={np.std(res_tbl):6.2f}  "
      f"MAE vs 真实={np.abs(np.array(res_tbl)-r_real).mean():.2f}")
print(f"\n  相关: corr(真实, 全画布)={np.corrcoef(r_real, res_full)[0,1]:+.3f}")
print(f"        corr(真实, 查表)  ={np.corrcoef(r_real, res_tbl)[0,1]:+.3f}")
