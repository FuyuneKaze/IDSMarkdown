# -*- coding: utf-8 -*-
"""
按【真实通路】测包围: 障碍 = 每笔画 strokic_boundary 的并集 (即 ids_anal.bbox 的做法)

① 量化 strokic_boundary 相对中心线的膨胀 (这才是"间距"的来源)
② 用它求包围空腔, 对比设计者真实放置
③ 量化"有效间距": 空腔边界到容器实际笔画的距离
"""
import sys, io, math, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())


def fast_get(t, datas=None, **kw):
    best, bd = -1, ""
    n = len(t)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(t[i:j])
            if h is not None and h[0] > best:
                best, bd = h[0], h[1]
    return bd


glyph_extend.get_data = fast_get
import stroke_outer as SO  # noqa: E402


def flatten(name, rect=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if rect is None:
            return glyph_extend.return_bone(name)
        g = ((str(rect[0]), str(rect[1]), str(rect[2]), str(rect[3])), (0, 0), (0, 0))
        return glyph_extend.return_bone(name, g)


def strokes(data):
    return [s.strip() for s in data.split("$")
            if s.strip().split(":")[0] in ("1", "2", "3", "4", "6", "7")]


def center_bbox(stro):
    p = stro.split(":")
    xs = [float(v) for v in p[3::2]]
    ys = [float(v) for v in p[4::2]]
    return (min(xs), min(ys), max(xs), max(ys))


def strokic(stro):
    try:
        b = SO.strokic_boundary(stro)
        if b.x2 > b.x1 and b.y2 > b.y1:
            return (b.x1, b.y1, b.x2, b.y2)
    except Exception:
        pass
    return None


def ids_anal_bbox(data):
    """完全复刻 ids_anal.bbox(): 各笔画 strokic_boundary 并集"""
    sts = strokes(data)
    if not sts:
        return None
    boxes = [strokic(s) for s in sts]
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


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


CASES = [
    ("衣-05", "u8863-05", "u516c-jn", (7, 40, 192, 120), "衮·公"),
    ("行-05", "u884c-05", "u543e-j", (55, 0, 145, 200), "衙·吾"),
    ("虍-10", "u864d-10", "u7530-j", (42, 90, 185, 145), "慮·田"),
    ("鹿-11", "u9e7f-11", "u571f-04@7", (20, 45, 200, 200), "塵·土"),
    ("麻-05", "u9ebb-05-var-003", "u624b-04", (25, -5, 200, 200), "摩·手"),
    ("囗-j", "u56d7-j", None, None, "全包围参考"),
    ("广-05", "u5e7f-05", None, None, "半包围参考"),
]

print("=" * 84)
print("① strokic_boundary 相对中心线的膨胀 (每边)")
print("=" * 84)
infl_all = []
for label, cname, iname, irect, note in CASES:
    fl = flatten(cname)
    if not fl:
        continue
    rows = []
    for s in strokes(fl):
        cb = center_bbox(s)
        sb = strokic(s)
        if not sb:
            continue
        d = (cb[0] - sb[0], cb[1] - sb[1], sb[2] - cb[2], sb[3] - cb[3])
        rows.append((d, s.split(":")[0]))
        infl_all.append(d)
    if rows:
        mx = max(max(r) for r, _ in rows)
        mn = min(min(r) for r, _ in rows)
        av = sum(sum(r) / 4 for r, _ in rows) / len(rows)
        print(f"  {label:<8} 笔画{len(rows):>3}  每边膨胀: 平均{av:5.2f}  "
              f"最小{mn:5.2f}  最大{mx:5.2f}")

print()
print("=" * 84)
print("② 用 strokic 并集求空腔 vs 设计者真实放置")
print("=" * 84)

for label, cname, iname, irect, note in CASES:
    fl = flatten(cname)
    if not fl:
        continue
    sts = strokes(fl)
    boxes = [strokic(s) for s in sts]
    boxes = [b for b in boxes if b]
    if not boxes:
        continue
    outer = ids_anal_bbox(fl)
    cands = maximal_empty_rects(outer, boxes)
    cands.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)
    cav = cands[0] if cands else None

    # 容器实际轮廓点 (用于量有效间距)
    ink = []
    for s in sts:
        try:
            for p in SO.generate_border(s):
                ink.append((float(p.x), float(p.y)))
        except Exception:
            pass

    print(f"\n{'─'*84}")
    print(f"{label}   ({note})   笔画 {len(sts)}")
    print(f"{'─'*84}")
    print(f"  外框(墙)   {desmos(outer)}")
    if cav:
        w, h = cav[2] - cav[0], cav[3] - cav[1]
        print(f"  空腔       {desmos(cav)}   {w:.0f}x{h:.0f} 面积={w*h:.0f}")
        # 有效间距: 空腔各边到容器真实墨迹的距离
        ysel = [p for p in ink if cav[1] <= p[1] <= cav[3]]
        xsel = [p for p in ink if cav[0] <= p[0] <= cav[2]]
        gl = cav[0] - max([p[0] for p in ysel if p[0] < cav[0]], default=cav[0])
        gr = min([p[0] for p in ysel if p[0] > cav[2]], default=cav[2]) - cav[2]
        gt = cav[1] - max([p[1] for p in xsel if p[1] < cav[1]], default=cav[1])
        gb = min([p[1] for p in xsel if p[1] > cav[3]], default=cav[3]) - cav[3]
        print(f"  有效间距   左{gl:5.1f}  右{gr:5.1f}  上{gt:5.1f}  下{gb:5.1f}"
              f"   (到容器真实墨迹)")
    if iname and irect:
        ifl = flatten(iname, irect)
        if ifl:
            xs, ys = [], []
            for s in strokes(ifl):
                p = s.split(":")
                xs += [float(v) for v in p[3::2]]
                ys += [float(v) for v in p[4::2]]
            if xs:
                fp = (min(xs), min(ys), max(xs), max(ys))
                print(f"  真实放置   {desmos(fp)}   "
                      f"{fp[2]-fp[0]:.0f}x{fp[3]-fp[1]:.0f}")
