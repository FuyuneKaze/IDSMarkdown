# -*- coding: utf-8 -*-
"""
验证填充规则问题

kage_contour.js 输出的是"每个笔画独立的轮廓多边形"(Polygons.array)。
前端把它们合并到一个 path 并用 fill-rule=evenodd →
  一个点若被偶数个轮廓覆盖, 就不填充 → 笔画重叠处被挖空!

检查轮廓绕向 (signed area), 判断 nonzero 是否正确。
"""
import sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def signed_area(poly):
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        s += x1 * y2 - x2 * y1
    return s / 2.0


def bbox_overlap(a, b):
    ax1 = min(p[0] for p in a); ax2 = max(p[0] for p in a)
    ay1 = min(p[1] for p in a); ay2 = max(p[1] for p in a)
    bx1 = min(p[0] for p in b); bx2 = max(p[0] for p in b)
    by1 = min(p[1] for p in b); by2 = max(p[1] for p in b)
    ix = min(ax2, bx2) - max(ax1, bx1)
    iy = min(ay2, by2) - max(ay1, by1)
    return ix > 0 and iy > 0


cases = ["⿱艹朋", "⿱勿心", "⿱宀丁", "⿱日木", "⿰氵工", "⿰木木", "⿰日月"]
res = post("/api/render", {"ids": cases})

for it in res["results"]:
    if not it.get("contours"):
        print(f"{it['ids']}: 无数据")
        continue
    cs = it["contours"]
    areas = [signed_area(c) for c in cs]
    pos = sum(1 for a in areas if a > 0)
    neg = sum(1 for a in areas if a < 0)
    zero = sum(1 for a in areas if a == 0)

    # 计算有多少轮廓对在 bbox 上重叠
    n = len(cs)
    pairs = 0
    ov = 0
    for i in range(n):
        for j in range(i + 1, n):
            pairs += 1
            if bbox_overlap(cs[i], cs[j]):
                ov += 1

    total_area = sum(abs(a) for a in areas)
    print(f"\n{it['ids']}")
    print(f"   轮廓={n}  bbox 重叠的轮廓对={ov}/{pairs} "
          f"({ov/pairs*100:.0f}%)")
    print(f"   绕向: 正={pos} 负={neg} 零={zero}   "
          f"→ {'方向一致' if pos == 0 or neg == 0 else '方向混杂(有孔洞)'}")
    print(f"   轮廓面积总和={total_area:.0f}  (画布 200x200=40000)")
    print(f"   → evenodd 会把重叠区挖空: 重叠对占比 {ov/pairs*100:.0f}%")
