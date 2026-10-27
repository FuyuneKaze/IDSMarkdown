# -*- coding: utf-8 -*-
"""
包围原型 (策略B: 内部件填满空腔) —— 与 GlyphWiki 真实渲染对比

通路完全沿用 ids_anal 的既有做法:
  容器   = return_bone(外框字 + 包围后缀)      [-05/-10/-11/-15/-j/本体]
  障碍   = 每笔画 strokic_boundary 并集         [即 ids_anal.bbox]
  外框   = 障碍并集 (当墙)
  空腔   = 极大空矩形 (矩形精确枚举, O(n^3))
  内部件 = return_bone(内部字 + 内部后缀)      [-06/-j/-jn/本体]
  映射   = trans(inner, (空腔, (0,0),(0,0)))   [策略B: 填满]
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

OUTER_CHAIN = ["-05", "-10", "-11", "-15", "-j", ""]
INNER_CHAIN = ["-06", "-j", "-jn", ""]


def pick(base, chain):
    for s in chain:
        if base + s in IDX:
            return base + s
    return None


def flatten(name, rect=None):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            if rect is None:
                return glyph_extend.return_bone(name)
            g = ((str(rect[0]), str(rect[1]), str(rect[2]), str(rect[3])),
                 (0, 0), (0, 0))
            return glyph_extend.return_bone(name, g)
        except Exception:
            return ""


def strokes(data):
    return [s.strip() for s in data.split("$")
            if s.strip().split(":")[0] in ("1", "2", "3", "4", "6", "7")]


def strokic(stro):
    try:
        b = SO.strokic_boundary(stro)
        if b.x2 > b.x1 and b.y2 > b.y1:
            return (b.x1, b.y1, b.x2, b.y2)
    except Exception:
        pass
    return None


def boxes_of(data):
    return [b for b in (strokic(s) for s in strokes(data)) if b]


def union_box(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def ink_bbox(data):
    xs, ys = [], []
    for s in strokes(data):
        p = s.split(":")
        xs += [float(v) for v in p[3::2]]
        ys += [float(v) for v in p[4::2]]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


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
                        for r in rects
                        if r[0] < R and r[2] > L and r[1] < Y2 and r[3] > Y1)
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
    if r is None:
        return "None"
    x1, y1, x2, y2 = r
    return (f"[({x1:.1f},{y1:.1f}),({x2:.1f},{y1:.1f}),"
            f"({x2:.1f},{y2:.1f}),({x1:.1f},{y2:.1f})]")


def refs_of(data):
    out = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                out.append((p[7], (int(p[3]), int(p[4]), int(p[5]), int(p[6]))))
            except ValueError:
                pass
    return out


def resolve_alias(name, maxhop=10):
    """穿透"单引用且无直绘笔画"的 alias 链"""
    cur = name
    for _ in range(maxhop):
        hit = IDX.get(cur)
        d = hit[1] if hit else fast_get(cur)
        if not d:
            return "", cur
        rf = refs_of(d)
        if len(rf) == 1 and not strokes(d):
            nxt = rf[0][0].split("@")[0]
            if nxt in IDX and nxt != cur:
                cur = nxt
                continue
        return d, cur
    return "", cur


CASES = [
    ("囚", "⿴", "囗", "人"),
    ("巡", "⿺", "辶", "巛"),
    ("問", "⿵", "門", "口"),
    ("病", "⿸", "疒", "丙"),
    ("府", "⿸", "广", "付"),
    ("厄", "⿸", "厂", "㔾"),
    ("旬", "⿹", "勹", "日"),
    ("氖", "⿹", "气", "乃"),
    ("閒", "⿵", "門", "月"),
]


def build(ch, op, cch, ich):
    pdata, _ = resolve_alias(f"u{ord(ch):x}")
    if not pdata:
        return {"err": "字库无此字"}
    rf = refs_of(pdata)
    if len(rf) != 2:
        return {"err": f"顶层引用 {len(rf)} 个"}
    chex, ihex = f"u{ord(cch):x}", f"u{ord(ich):x}"
    cr = ir = None
    for nm, rect in rf:
        if nm.startswith(chex):
            cr = (nm, rect)
        elif nm.startswith(ihex):
            ir = (nm, rect)
    if cr is None or ir is None:
        cr, ir = rf[0], rf[1]

    cvar = pick(chex, OUTER_CHAIN)
    ivar = pick(ihex, INNER_CHAIN)
    if not cvar or not ivar:
        return {"err": "变体缺失"}
    ib = boxes_of(flatten(cvar))
    if not ib:
        return {"err": f"容器无笔画 {cvar}"}
    outer = union_box(ib)
    cands = maximal_empty_rects(outer, ib)
    if not cands:
        return {"err": "无空腔"}
    cands.sort(key=lambda r: (r[2] - r[0]) * (r[3] - r[1]), reverse=True)
    cav = cands[0]

    ibb = None
    ibox = boxes_of(flatten(ivar))
    if ibox:
        ibb = union_box(ibox)
    b_ink = None
    if ibb and ibb[2] > ibb[0] and ibb[3] > ibb[1]:
        sx = (cav[2] - cav[0]) / (ibb[2] - ibb[0])
        sy = (cav[3] - cav[1]) / (ibb[3] - ibb[1])
        im = ink_bbox(flatten(ivar))
        if im:
            b_ink = (cav[0] + (im[0] - ibb[0]) * sx, cav[1] + (im[1] - ibb[1]) * sy,
                     cav[0] + (im[2] - ibb[0]) * sx, cav[1] + (im[3] - ibb[1]) * sy)
    d_ink = ink_bbox(flatten(ir[0], ir[1]))
    return {"cvar": cvar, "ivar": ivar, "cav": cav, "outer": outer,
            "ir": ir, "b_ink": b_ink, "d_ink": d_ink, "cr": cr}


print("=" * 96)
print("策略B 原型  vs  GlyphWiki 真实渲染")
print("=" * 96)
print(f"  {'字':<3} {'算符':<4} {'容器变体':<11} {'内部变体':<10} "
      f"{'空腔(B给的)':<34} {'真实引用 rect'}")
print("  " + "-" * 92)
res = {}
for ch, op, cch, ich in CASES:
    r = build(ch, op, cch, ich)
    res[ch] = r
    if not r or r.get("err"):
        print(f"  {ch:<3} {op:<4} 跳过: {r.get('err') if r else '无数据'}")
        continue
    print(f"  {ch:<3} {op:<4} {r['cvar']:<11} {r['ivar']:<10} "
          f"{desmos(r['cav']):<34} {r['ir'][0]} {r['ir'][1]}")

print()
print("=" * 96)
print("细节: 空腔 / B映射后内部件墨迹 / 真实内部件墨迹")
print("=" * 96)
for ch, op, cch, ich in CASES:
    r = res.get(ch)
    if not r or r.get("err"):
        continue
    print(f"\n  {ch} ({op}{cch}{ich})   容器={r['cvar']}  内部={r['ivar']}")
    print(f"    空腔       {desmos(r['cav'])}   "
          f"{r['cav'][2]-r['cav'][0]:.0f}x{r['cav'][3]-r['cav'][1]:.0f}")
    if r["b_ink"]:
        print(f"    B 映射墨迹 {desmos(r['b_ink'])}   "
              f"{r['b_ink'][2]-r['b_ink'][0]:.0f}x{r['b_ink'][3]-r['b_ink'][1]:.0f}")
    if r["d_ink"]:
        print(f"    真实墨迹   {desmos(r['d_ink'])}   "
              f"{r['d_ink'][2]-r['d_ink'][0]:.0f}x{r['d_ink'][3]-r['d_ink'][1]:.0f}")
