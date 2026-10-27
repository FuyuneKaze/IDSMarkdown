# -*- coding: utf-8 -*-
"""
半包围内接盒原型 —— 外框当墙 + 笔画 bbox 当障碍

关键点:
  1. 外包围盒 = 四面"墙", 于是半包围变成封闭问题, 不用补虚拟墙
  2. 障碍全是轴对齐矩形 → 极大空矩形可精确枚举, 无需栅格/单调栈
     候选左边界 ∈ {外框左沿} ∪ {各障碍右沿}
     候选右边界 ∈ {外框右沿} ∪ {各障碍左沿}
     固定 [L,R] 竖条后, y 方向的"最大空隙"就是该条带的最优高度
     O(n^3), n=笔画数(5~10) → 微秒级

输出 Desmos 点列表, 格式与 [(x,y),(x,y),...] 一致, 可直接 polygon() 用
"""
import sys, io, time, contextlib
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

# ---------- 建索引 (复刻 preview 的子串 fallback 语义) ----------
IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())


def _fast_get(targets, datas=None):
    best, bd = -1, ""
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(targets[i:j])
            if h is not None and h[0] > best:
                best, bd = h[0], h[1]
    return bd


glyph_extend.get_data = _fast_get
from stroke_outer import strokic_boundary  # noqa: E402


def flatten(name):
    """展开 alias/type-99, 得到纯笔画串"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return glyph_extend.return_bone(name)


def stroke_boxes(data):
    """每个笔画 → stroke_outer.Bbox"""
    out = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        try:
            b = strokic_boundary(seg)
        except Exception:
            continue
        if b.x2 > b.x1 and b.y2 > b.y1:
            out.append((b.x1, b.y1, b.x2, b.y2))
    return out


# ============================================================
# 精确算法: 矩形障碍下的极大空矩形
# ============================================================
def maximal_empty_rects(box, rects):
    X1, Y1, X2, Y2 = box
    Ls = sorted({X1} | {min(max(r[2], X1), X2) for r in rects})
    Rs = sorted({X2} | {min(max(r[0], X1), X2) for r in rects})
    uniq = {}
    for L in Ls:
        for R in Rs:
            if R <= L:
                continue
            blocked = []
            for r in rects:
                if r[0] < R and r[2] > L:          # 在 x 上与竖条相交
                    b0, b1 = max(r[1], Y1), min(r[3], Y2)
                    if b1 > b0:
                        blocked.append((b0, b1))
            blocked.sort()
            gaps, cur = [], Y1
            for b0, b1 in blocked:
                if b0 > cur:
                    gaps.append((cur, b0))          # y 方向空隙
                if b1 > cur:
                    cur = b1
            if cur < Y2:
                gaps.append((cur, Y2))
            for g0, g1 in gaps:
                uniq[(round(L, 3), round(g0, 3), round(R, 3), round(g1, 3))] = (L, g0, R, g1)
    return list(uniq.values())


# ============================================================
# 对照: 栅格 + 单调栈 (你觉得慢的那个)
# ============================================================
def grid_max_rect(box, rects, N=200):
    X1, Y1, X2, Y2 = box
    sx, sy = (X2 - X1) / N, (Y2 - Y1) / N
    blocked = bytearray(N * N)
    for (a, b, c, d) in rects:
        i0 = max(0, int((a - X1) / sx)); i1 = min(N, int((c - X1) / sx) + 1)
        j0 = max(0, int((b - Y1) / sy)); j1 = min(N, int((d - Y1) / sy) + 1)
        for j in range(j0, j1):
            base = j * N
            for i in range(i0, i1):
                blocked[base + i] = 1
    heights = [0] * N
    best = None
    for j in range(N):
        base = j * N
        for i in range(N):
            heights[i] = 0 if blocked[base + i] else heights[i] + 1
        stack = []
        for i in range(N + 1):
            h = heights[i] if i < N else 0
            start = i
            while stack and stack[-1][1] >= h:
                x0, hh = stack.pop()
                if hh > 0:
                    area = (i - x0) * hh
                    if best is None or area > best[0]:
                        best = (area, x0, j - hh + 1, i, j + 1, hh)
                start = x0
            stack.append((start, h))
    if not best:
        return None
    _, i0, j0, i1, j1, _ = best
    return (X1 + i0 * sx, Y1 + j0 * sy, X1 + i1 * sx, Y1 + j1 * sy)


def desmos(r):
    x1, y1, x2, y2 = r
    return (f"[({x1:.2f},{y1:.2f}),({x2:.2f},{y1:.2f}),"
            f"({x2:.2f},{y2:.2f}),({x1:.2f},{y2:.2f})]")


# ============================================================
# 测试: 各包围外框
# ============================================================
TESTS = [
    ("广 ⿸左上", "u5e7f"), ("辶 ⿺左下", "u8fb6"),
    ("勹 ⿹右上", "u52f9"), ("囗 ⿴全包", "u56d7"),
    ("匚 ⿷左包", "u531a"), ("冂 ⿵上包", "u5182"),
    ("厂 ⿸左上", "u5382"), ("疒 ⿸左上", "u7592"),
]

print("=" * 82)
print("各包围外框: 笔画框 → 外框(墙) → 极大空矩形")
print("=" * 82)

t_exact = t_grid = 0.0
results = {}

for label, base in TESTS:
    # 找可用变体 (包围外框优先 -05)
    name = None
    for sfx in ("-05", "-10", "-11", "-15", "-j", ""):
        if base + sfx in IDX:
            name = base + sfx
            break
    if name is None:
        print(f"\n{label}  ({base}): 无可用字形")
        continue

    data = flatten(name)
    boxes = stroke_boxes(data)
    if not boxes:
        print(f"\n{label}  ({name}): 无直绘笔画 (数据={data[:60]})")
        continue

    X1 = min(b[0] for b in boxes); Y1 = min(b[1] for b in boxes)
    X2 = max(b[2] for b in boxes); Y2 = max(b[3] for b in boxes)
    outer = (X1, Y1, X2, Y2)

    t0 = time.perf_counter()
    cands = maximal_empty_rects(outer, boxes)
    t_exact += time.perf_counter() - t0

    t0 = time.perf_counter()
    g = grid_max_rect(outer, boxes, 200)
    t_grid += time.perf_counter() - t0

    cands.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)
    results[label] = (name, outer, boxes, cands, g)

    print(f"\n{'─'*82}")
    print(f"{label}   {name}   笔画 {len(boxes)} 个")
    print(f"{'─'*82}")
    print(f"  外框(墙) {desmos(outer)}")
    print(f"  候选极大空矩形 {len(cands)} 个, 前 3:")
    for k, r in enumerate(cands[:3]):
        w, h = r[2] - r[0], r[3] - r[1]
        print(f"   #{k+1} 面积={w*h:7.0f}  {w:.0f}x{h:.0f}  "
              f"比例={max(w,h)/max(min(w,h),1e-6):.2f}")
        print(f"       {desmos(r)}")
    if g:
        gw, gh = g[2] - g[0], g[3] - g[1]
        print(f"  [对照] 栅格+单调栈最大: 面积={gw*gh:.0f} {gw:.0f}x{gh:.0f}")
        print(f"       {desmos(g)}")

print()
print("=" * 82)
print(f"耗时: 精确枚举 {t_exact*1000:.2f}ms / {len(results)} 个   "
      f"栅格200+单调栈 {t_grid*1000:.2f}ms")
print("=" * 82)
