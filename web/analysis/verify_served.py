# -*- coding: utf-8 -*-
"""确认服务返回的页面已用 nonzero"""
import sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"

with urllib.request.urlopen(BASE + "/", timeout=30) as r:
    html = r.read().decode("utf-8")
print(f"页面 {len(html):,} bytes")
print(f"  'nonzero' 出现 {html.count('nonzero')} 次")
print(f"  'evenodd' 出现 {html.count('evenodd')} 次")

# 顺便回归一次
body = json.dumps({"ids": ["⿱艹朋", "⿱勿心", "⿱日木", "⿰木木"]},
                  ensure_ascii=False).encode("utf-8")
req = urllib.request.Request(BASE + "/api/render", data=body,
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=180) as r:
    res = json.loads(r.read().decode("utf-8"))
print(f"\n回归 {len(res['results'])} 个 → {res['total_ms']}ms")
for it in res["results"]:
    print(f"  {it['ids']:<8} "
          + (f"OK {it['info']['n_contours']}轮廓" if it.get("contours") else "FAIL"))
