# -*- coding: utf-8 -*-
"""
数值验证 fill-rule: 栅格采样对比 evenodd vs nonzero 的填充面积

预期 (轮廓方向一致时):
  nonzero 填充 = 轮廓并集
  evenodd 填充 = 并集 - 笔画重叠区   → 笔画越多, 差得越多
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


def crossings(x, y, poly):
    """射线法: 返回穿越次数"""
    n = len(poly)
    c = 0
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                c += 1
    return c


def winding(x, y, poly):
    """绕数"""
    n = len(poly)
    wn = 0
    for i in range(n):
        x1, y1 = poly[i][0], poly[i][1]
        x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if y1 <= y:
            if y2 > y and (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1) > 0:
                wn += 1
        else:
            if y2 <= y and (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1) < 0:
                wn -= 1
    return wn


cases = ["⿱艹朋", "⿱勿心", "⿱日木", "⿰木木", "⿱宀丁", "⿰氵工"]
res = post("/api/render", {"ids": cases})

STEP = 2.0   # 采样步长 (200/2 = 100x100 = 1 万点)
print(f"栅格步长 {STEP} → 每格 {int(200/STEP)**2} 个采样点\n")
print(f"{'IDS':<8} {'轮廓':>4} {'nonzero填充':>11} {'evenodd填充':>11} "
      f"{'差值':>9} {'差异%':>7}")
print("-" * 62)

for it in res["results"]:
    if not it.get("contours"):
        print(f"{it['ids']}: 无数据")
        continue
    cs = it["contours"]
    fn = fe = tot = 0
    y = STEP / 2
    while y < 200:
        x = STEP / 2
        while x < 200:
            tot += 1
            w = 0
            cr = 0
            for c in cs:
                w += winding(x, y, c)
                cr += crossings(x, y, c)
            if w != 0:
                fn += 1
            if cr % 2 == 1:
                fe += 1
            x += STEP
        y += STEP
    cell = STEP * STEP
    an = fn * cell
    ae = fe * cell
    diff = an - ae
    pct = (diff / an * 100) if an else 0
    print(f"{it['ids']:<8} {len(cs):>4} {an:>11.0f} {ae:>11.0f} "
          f"{diff:>9.0f} {pct:>6.1f}%")

print("-" * 62)
print("(单位: 200x200 空间下的面积; 画布满面积 = 40000)")
print("nonzero = 正确(并集)   evenodd = 被挖空, 差值即丢掉的笔画重叠区")
