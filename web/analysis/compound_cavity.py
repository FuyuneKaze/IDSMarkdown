# -*- coding: utf-8 -*-
"""
决定性验证: 复合容器的 -05 变体里, 空腔是否真的存在、位置是否吻合设计者的放置

方法: 把 -05 变体展平成笔画 → 每笔画 bbox → 外框当墙 → 求极大空矩形
      再对比真实字里设计者把内部件放在哪
"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())


def fast_get(targets, datas=None, **kw):
    best, bd = -1, ""
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(targets[i:j])
            if h is not None and h[0] > best:
                best, bd = h[0], h[1]
    return bd


glyph_extend.get_data = fast_get

from stroke_outer import strokic_boundary  # noqa: E402


def raw(name):
    h = IDX.get(name)
    return h[1] if h else fast_get(name)


def flatten(name):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return glyph_extend.return_bone(name)


def stroke_boxes(data):
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
            out.append((round(b.x1, 2), round(b.y1, 2), round(b.x2, 2), round(b.y2, 2)))
    return out


def maximal_empty_rects(box, rects):
    X1, Y1, X2, Y2 = box
    Ls = sorted({X1} | {min(max(r[2], X1), X2) for r in rects})
    Rs = sorted({X2} | {min(max(r[0], X1), X2) for r in rects})
    uniq = {}
    for L in Ls:
        for R in Rs:
            if R <= L:
                continue
            bl = sorted((max(r[1], Y1), min(r[3], Y2))
                        for r in rects if r[0] < R and r[2] > L and r[1] < Y2 and r[3] > Y1)
            gaps, cur = [], Y1
            for b0, b1 in bl:
                if b0 > cur:
                    gaps.append((cur, b0))
                if b1 > cur:
                    cur = b1
            if cur < Y2:
                gaps.append((cur, Y2))
            for g0, g1 in gaps:
                uniq[(round(L, 2), round(g0, 2), round(R, 2), round(g1, 2))] = (L, g0, R, g1)
    return list(uniq.values())


def desmos(r):
    x1, y1, x2, y2 = r
    return (f"[({x1:.1f},{y1:.1f}),({x2:.1f},{y1:.1f}),"
            f"({x2:.1f},{y2:.1f}),({x1:.1f},{y2:.1f})]")


# (标签, 容器变体, 真实字里内部件占的矩形)
CASES = [
    ("衣-05  用于 ⿴衣X", "u8863-05", (7, 40, 192, 120), "衮 的公"),
    ("行-05  用于 ⿴行X", "u884c-05", (55, 0, 145, 200), "衙 的吾"),
    ("鹿-11  用于 ⿸鹿X", "u9e7f-11", (20, 45, 200, 200), "塵 的土"),
    ("麻-05  用于 ⿸麻X", "u9ebb-05-var-003", (25, -5, 200, 200), "摩 的手"),
    ("气-05  用于 ⿹气X", "u6c14-05", None, "氕 的丿(在内)"),
    ("虍-10  用于 ⿸虍X", "u864d-10", (42, 90, 185, 145), "慮 的田"),
]

print("=" * 86)
print("复合容器的 -05 变体: 展平后各笔画 bbox")
print("=" * 86)

for label, name, inner, note in CASES:
    d = raw(name)
    print(f"\n{'─'*86}")
    print(f"{label}   ({name})")
    print(f"{'─'*86}")
    if not d:
        print("  字形不存在")
        continue
    if len(d) <= 240:
        print(f"  原始数据: {d}")
    fl = flatten(name)
    if not fl:
        print("  展平失败 (可能只有引用无笔画)")
        continue
    boxes = stroke_boxes(fl)
    if not boxes:
        print("  无可用笔画框")
        continue
    X1 = min(b[0] for b in boxes); Y1 = min(b[1] for b in boxes)
    X2 = max(b[2] for b in boxes); Y2 = max(b[3] for b in boxes)
    outer = (X1, Y1, X2, Y2)
    print(f"  笔画 {len(boxes)} 个   外框 {desmos(outer)}")
    for b in boxes[:8]:
        print(f"      {desmos(b)}")
    if len(boxes) > 8:
        print(f"      ... 另 {len(boxes)-8} 个")

    cands = maximal_empty_rects(outer, boxes)
    cands.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)
    print(f"  极大空矩形 {len(cands)} 个, 前 3:")
    for k, r in enumerate(cands[:3]):
        w, h = r[2] - r[0], r[3] - r[1]
        print(f"    #{k+1} {w:.0f}x{h:.0f} 面积={w*h:.0f}   {desmos(r)}")
    if inner:
        iw, ih = inner[2] - inner[0], inner[3] - inner[1]
        print(f"  [真实] {note} 占 {desmos(inner)}  {iw}x{ih} 面积={iw*ih}")
