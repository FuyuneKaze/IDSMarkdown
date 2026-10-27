# -*- coding: utf-8 -*-
"""查前端渲染: contours 的 off 分布 + 坐标范围"""
import sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


cases = ["⿱艹朋", "⿱勿心", "⿱宀丁", "⿱日木", "⿰氵工"]
res = post("/api/render", {"ids": cases})

for it in res["results"]:
    if not it.get("contours"):
        print(f"{it['ids']}: 无数据")
        continue
    cs = it["contours"]
    pts = [p for c in cs for p in c]
    off0 = [p for p in pts if p[2] == 0]
    off1 = [p for p in pts if p[2] == 1]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    no0 = [i for i, c in enumerate(cs) if not any(p[2] == 0 for p in c)]
    only1 = [i for i, c in enumerate(cs) if all(p[2] == 1 for p in c)]

    print(f"\n{it['ids']}  ({it['info']['names']})")
    print(f"   轮廓={len(cs)}  总点={len(pts)}  off0={len(off0)}  off1={len(off1)}")
    print(f"   坐标 x: [{min(xs):.1f}, {max(xs):.1f}]   y: [{min(ys):.1f}, {max(ys):.1f}]")
    print(f"   完全无 off=0 的轮廓: {len(no0)} 个 {no0[:8]}")
    print(f"   全是 off=1 的轮廓:   {len(only1)} 个 {only1[:8]}")
    # 坐标越界
    oob = [p for p in pts if p[0] < -4 or p[0] > 204 or p[1] < -4 or p[1] > 204]
    print(f"   超出 viewBox(-4~204) 的点: {len(oob)}")
    if oob:
        ox = [p[0] for p in oob]; oy = [p[1] for p in oob]
        print(f"      越界范围 x:[{min(ox):.0f},{max(ox):.0f}] y:[{min(oy):.0f},{max(oy):.0f}]")
    # 前 2 个轮廓样例
    for c in cs[:2]:
        print(f"   轮廓样例 (前 6 点): {[[round(q[0],1), round(q[1],1), int(q[2])] for q in c[:6]]}")
