# -*- coding: utf-8 -*-
"""
量化: "每笔画 bbox" 作为边界函数输入, 精度够不够?
顺带给出 slab 分解的规模代价, 用于对比方案。

① 每个轮廓: 真实多边形面积 vs 外接矩形面积
② 奇偶配对健全性检查 (奇数次交点会导致区间配对错位)
③ 边界包络失真 (只统计配对可靠的行)
④ slab 分解规模 (若改用轮廓切片, 边界函数会有多少段)
"""
import sys, io, json, statistics, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def shoelace(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def poly_bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def merge_intervals(iv):
    if not iv:
        return []
    iv = sorted(iv)
    out = [list(iv[0])]
    for a, b in iv[1:]:
        if a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(m) for m in out]


def crossings(polys, y):
    xs = []
    for poly in polys:
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i][0], poly[i][1]
            x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs.append(x1 + t * (x2 - x1))
    return sorted(xs)


def slab_count(poly):
    ys = sorted({p[1] for p in poly})
    c = 0
    for k in range(len(ys) - 1):
        if crossings([poly], (ys[k] + ys[k + 1]) / 2):
            c += 1
    return c


cases = ["⿰氵工", "⿰木木", "⿰扌土", "⿱艹朋", "⿰亻尔", "⿱宀丁", "⿰日月"]
res = post("/api/render", {"ids": cases})
R = [r for r in res["results"] if r.get("contours")]

print("=" * 80)
print("① 轮廓面积 vs 其外接矩形面积   (bbox 作为边界函数的失真度)")
print("=" * 80)
print(f"  {'IDS':<9} {'轮廓':>4} {'中位比':>8} {'最大比':>8} {'>2x占比':>8} "
      f"{'slab段数':>9} {'每轮廓':>7}")
print("  " + "-" * 68)
tot_slabs = {}
for it in R:
    cs = it["contours"]
    ratios, slabs = [], 0
    for c in cs:
        a = shoelace(c)
        if a <= 0:
            continue
        x1, y1, x2, y2 = poly_bbox(c)
        ratios.append((x2 - x1) * (y2 - y1) / a)
        slabs += slab_count(c)
    if not ratios:
        continue
    over2 = sum(1 for r in ratios if r > 2) / len(ratios) * 100
    print(f"  {it['ids']:<9} {len(cs):>4} {statistics.median(ratios):>8.2f} "
          f"{max(ratios):>8.2f} {over2:>7.0f}% {slabs:>9} {slabs/len(cs):>7.1f}")
    tot_slabs[it["ids"]] = (len(cs), slabs)

print()
print("=" * 80)
print("② 奇偶配对健全性 (奇数次交点会让区间配对错位)")
print("=" * 80)
for it in R:
    cs = it["contours"]
    odd = tot = 0
    for k in range(200):
        n = len(crossings(cs, k + 0.5))
        if n:
            tot += 1
            if n % 2:
                odd += 1
    print(f"  {it['ids']:<9} 有交点的行={tot:>4}  奇数次={odd:>4} "
          f"({odd/max(tot,1)*100:>3.0f}%)  "
          f"{'配对可靠' if odd == 0 else '← 有风险'}")

print()
print("=" * 80)
print("③ 边界包络失真 (仅统计交点数偶数的行)")
print("=" * 80)
print(f"  {'IDS':<9} {'左边界均差':>10} {'左最大':>8} {'右边界均差':>10} "
      f"{'右最大':>8} {'>3px行占比':>10}")
print("  " + "-" * 68)
for it in R:
    cs = it["contours"]
    boxes = [poly_bbox(c) for c in cs]
    dl, dr, bad, tot = [], [], 0, 0
    for k in range(200):
        y = k + 0.5
        xs = crossings(cs, y)
        if len(xs) >= 2 and len(xs) % 2 == 0:
            cov = merge_intervals([(b[0], b[2]) for b in boxes
                                   if b[1] <= y <= b[3]])
            if cov:
                tot += 1
                a = abs(xs[0] - cov[0][0])
                b = abs(xs[-1] - cov[-1][1])
                dl.append(a)
                dr.append(b)
                if a > 3 or b > 3:
                    bad += 1
    if dl:
        print(f"  {it['ids']:<9} {statistics.mean(dl):>10.2f} {max(dl):>8.2f} "
              f"{statistics.mean(dr):>10.2f} {max(dr):>8.2f} "
              f"{bad/max(tot,1)*100:>9.0f}%")

print()
print("=" * 80)
print("④ 方案规模对比: bbox 段数 vs slab 段数")
print("=" * 80)
print(f"  {'IDS':<9} {'bbox段数':>9} {'slab段数':>9} {'倍数':>7}")
for it in R:
    n, s = tot_slabs[it["ids"]]
    print(f"  {it['ids']:<9} {n:>9} {s:>9} {s/max(n,1):>7.1f}x")
