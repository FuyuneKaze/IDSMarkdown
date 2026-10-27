# -*- coding: utf-8 -*-
"""
量化: 用"每笔画 bbox" vs 用"真实轮廓" 算出的边界差多少

模拟你现在的做法(每笔画一个 bbox)与精确轮廓的差异,
重点看斜笔画(撇/捺/钩)所在的行。
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


def profile_exact(polys, step=1.0):
    """精确: 每 step 像素取一行, 用轮廓求交(奇偶配对)"""
    rows = []
    y = 0.0
    while y <= 200.0:
        xs = []
        for poly in polys:
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i][0], poly[i][1]
                x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
                if (y1 <= y < y2) or (y2 <= y < y1):
                    t = (y - y1) / (y2 - y1)
                    xs.append(x1 + t * (x2 - x1))
        xs.sort()
        iv = [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]
        rows.append((y, iv))
        y += step
    return rows


def profile_boxed(polys):
    """近似: 每个 contour 取 bbox, 再按矩形集合求每行的 x 覆盖"""
    boxes = []
    for poly in polys:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def coverage_at(boxes, y):
    iv = [(b[0], b[2]) for b in boxes if b[1] <= y <= b[3]]
    return merge_intervals(iv)


cases = ["⿰氵工", "⿰木木", "⿰扌土", "⿱艹朋"]
res = post("/api/render", {"ids": cases})

for it in res["results"]:
    if not it.get("contours"):
        continue
    polys = it["contours"]
    boxes = profile_boxed(polys)
    exact = profile_exact(polys, step=1.0)

    # 逐行比较：最左/最右边界
    diffs_l, diffs_r = [], []
    worst = []
    for (y, iv) in exact:
        if not iv:
            continue
        eb_l, eb_r = iv[0][0], iv[-1][1]
        biv = coverage_at(boxes, y)
        if not biv:
            continue
        bb_l, bb_r = biv[0][0], biv[-1][1]
        dl, dr = bb_l - eb_l, eb_r - bb_r      # 正 = bbox 外扩
        diffs_l.append(abs(dl))
        diffs_r.append(abs(dr))
        if abs(dl) > 3 or abs(dr) > 3:
            worst.append((y, dl, dr))

    nb = len(boxes)
    print(f"\n{it['ids']}   轮廓={len(polys)}  bbox={nb}")
    print(f"   左边界偏差: 均值={sum(diffs_l)/len(diffs_l):.2f} "
          f"最大={max(diffs_l):.2f}")
    print(f"   右边界偏差: 均值={sum(diffs_r)/len(diffs_r):.2f} "
          f"最大={max(diffs_r):.2f}")
    print(f"   偏差>3px 的行数: {len(worst)} / {len(diffs_l)} "
          f"({len(worst)/len(diffs_l)*100:.0f}%)")
    if worst:
        w = max(worst, key=lambda t: max(abs(t[1]), abs(t[2])))
        print(f"   最严重一行 y={w[0]:.0f}: 左偏{w[1]:+.1f}px 右偏{w[2]:+.1f}px")
