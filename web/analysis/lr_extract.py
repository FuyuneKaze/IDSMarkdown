# -*- coding: utf-8 -*-
"""
左右比例 — 干净数据管道 (v1)

修正前面所有错误:
  1. 数据源 = core_glyphs.json 原始字形 (不用任何中间产物)
  2. 用 ids_lv1.txt 的 ⿰XY 确定"谁是左/谁是右" (不再用矩形 x1 排序 — 那是错的)
  3. 比例 = 部件笔画在最终画布上的实际视觉宽度占比

输出: lr_data.csv
  char c1 c2 | L_bbox(L_w,L_h) R_bbox | share_L
  + 部件特征: 笔画数、墨量、原始bbox、宽高比
"""
import sys, io, json, time
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
IDS = r"D:\2026harucpp\web\public\ids_lv1.txt"
OUT = r"D:\2026harucpp\web\analysis\lr_data.csv"

OPS = set(chr(c) for c in range(0x2FF0, 0x3000)) | {chr(0x31EF)}

t0 = time.time()
db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
print(f"core_glyphs: {len(db)} ({time.time()-t0:.1f}s)")


def parse(data):
    refs, nstroke = [], 0
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
        elif p[0] in ("1", "2", "3", "4", "6", "7"):
            nstroke += 1
    return refs, nstroke


def resolve(name, max_hops=10):
    """穿透 alias 链"""
    chain = [name]
    data = db.get(name)
    if data is None:
        return None, [], 0
    for _ in range(max_hops):
        refs, ns = parse(data)
        if len(refs) == 1 and ns == 0:
            nxt = refs[0][4].split("@")[0]
            if nxt in db and nxt != name:
                chain.append(nxt)
                data = db[nxt]
                name = nxt
                continue
        break
    refs, ns = parse(data)
    return data, refs, ns


# ---------- 笔画展开 + 统计 ----------
def collect(data, rect=(0.0, 0.0, 200.0, 200.0), visited=None, depth=0):
    """展开到叶子笔画, 返回 [(pts,), ...] 在 rect 坐标系"""
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


def stats(strokes):
    """返回 (bbox, 笔画数, 墨量=线段总长, 控制点数)"""
    if not strokes:
        return None
    xs = [x for pts in strokes for x, _ in pts]
    ys = [y for pts in strokes for _, y in pts]
    ink = 0.0
    npts = 0
    for pts in strokes:
        npts += len(pts)
        for i in range(len(pts) - 1):
            ink += np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
    return ((min(xs), min(ys), max(xs), max(ys)), len(strokes), ink, npts)


# ---------- 读 ⿰XY ----------
pairs = []
with open(IDS, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        ch = parts[0]
        for ids in parts[1:]:
            if len(ids) == 3 and ids[0] == "⿰" and ids[1] not in OPS and ids[2] not in OPS:
                pairs.append((ch, ids[1], ids[2]))
                break
print(f"⿰XY 候选: {len(pairs)}")


def ref_for(refs, ch):
    """按字符码点匹配 ref (变体名以 u<hex> 开头)"""
    hexs = f"u{ord(ch):x}"
    for r in refs:
        nm = r[4]
        if nm == hexs or nm.startswith(hexs + "-") or nm.startswith(hexs + "@"):
            return r
    return None


rows = []
skip = {"no_char": 0, "not_2ref": 0, "no_match": 0, "no_stats": 0}
for ch, c1, c2 in pairs:
    nm = f"u{ord(ch):x}"
    if nm not in db:
        skip["no_char"] += 1
        continue
    data, refs, ns = resolve(nm)
    if len(refs) != 2:
        skip["not_2ref"] += 1
        continue
    rl = ref_for(refs, c1)
    rr = ref_for(refs, c2)
    if rl is None or rr is None or rl is rr:
        skip["no_match"] += 1
        continue

    # 左部件: 用它的矩形映射, 得到最终画布坐标
    sl = stats(collect(db.get(rl[4].split("@")[0], ""), (rl[0], rl[1], rl[2], rl[3])))
    sr = stats(collect(db.get(rr[4].split("@")[0], ""), (rr[0], rr[1], rr[2], rr[3])))
    if sl is None or sr is None:
        skip["no_stats"] += 1
        continue
    bl, nl, inkl, ptl = sl
    br, nr, inkr, ptr = sr

    # 部件"自身"的数据 (未映射, 200 空间) — 作为特征
    sl0 = stats(collect(db.get(rl[4].split("@")[0], "")))
    sr0 = stats(collect(db.get(rr[4].split("@")[0], "")))
    if sl0 is None or sr0 is None:
        skip["no_stats"] += 1
        continue
    b0l, n0l, ink0l, pt0l = sl0
    b0r, n0r, ink0r, pt0r = sr0

    wl, wr = bl[2] - bl[0], br[2] - br[0]
    if wl <= 0 or wr <= 0:
        continue

    rows.append({
        "char": ch, "c1": c1, "c2": c2,
        "Lvar": rl[4], "Rvar": rr[4],
        # 最终视觉
        "Lx1": bl[0], "Lx2": bl[2], "Lw": wl, "Lh": bl[3] - bl[1],
        "Rx1": br[0], "Rx2": br[2], "Rw": wr, "Rh": br[3] - br[1],
        "share_L": wl / (wl + wr),
        # 左部件自身特征 (200 空间, 未映射)
        "L0x1": b0l[0], "L0x2": b0l[2], "L0w": b0l[2] - b0l[0], "L0h": b0l[3] - b0l[1],
        "L0ink": ink0l, "L0strokes": n0l, "L0pts": pt0l,
        # 右部件自身特征
        "R0w": b0r[2] - b0r[0], "R0h": b0r[3] - b0r[1],
        "R0ink": ink0r, "R0strokes": n0r, "R0pts": pt0r,
        # 参考: 左变体右边界 (200 空间) — "左占多宽"的直接表达
        "L0x2": b0l[2],
    })

import pandas as pd
d = pd.DataFrame(rows)
d.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"有效: {len(d)}   跳过: {skip}")
print(f"输出: {OUT}  ({time.time()-t0:.1f}s)\n")

print("=" * 78)
print("比例分布 share_L = 左视觉宽/(左+右)")
print("=" * 78)
s = d["share_L"]
print(f"  n={len(s)} mean={s.mean():.3f} std={s.std():.3f} median={s.median():.3f}")
print("  分位: " + "  ".join(f"p{q}={np.percentile(s,q):.3f}" for q in [1, 5, 25, 50, 75, 95, 99]))

print(f"\n  左部件自身右边界 L0x2 / 200 (即'左占多宽'的直接表达):")
x = d["L0x2"] / 200.0
print(f"  mean={x.mean():.3f} std={x.std():.3f}")
print(f"  corr(share_L, L0x2/200) = {s.corr(x):+.3f}")

print()
print("=" * 78)
print("典型左部件的 share_L (固定左部件, 看是否稳定)")
print("=" * 78)
print(f"  {'部件':<5} {'n':>5} {'mean':>7} {'std':>7} {'min':>7} {'max':>7}   {'L0w':>6} {'L0ink':>8} {'L0strk':>7}")
for ch in ["亻", "氵", "扌", "口", "木", "土", "日", "月", "女", "糹", "纟", "讠", "钅", "石", "王", "火"]:
    g = d[d["c1"] == ch]
    if len(g) < 10:
        continue
    print(f"  {ch:<5} {len(g):>5} {g['share_L'].mean():>7.3f} {g['share_L'].std():>7.3f} "
          f"{g['share_L'].min():>7.3f} {g['share_L'].max():>7.3f}   "
          f"{g['L0w'].mean():>6.1f} {g['L0ink'].mean():>8.1f} {g['L0strokes'].mean():>7.1f}")
