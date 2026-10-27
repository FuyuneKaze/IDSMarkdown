# -*- coding: utf-8 -*-
"""
验证「接缝拉伸」已与 kage-bundle.js 的 KAGE 语义对齐

对照对象:
  actual   = 修好后的 glyph_extend.unfold 的实际输出 (已落位到引用矩形)
  expected = 按 kage-bundle.js getEachStrokesOfBuhin + stretch 复刻的模型

99 行: 99:sx:sy:x1:y1:x2:y2:name:sx2:sy2
  KAGE: 缝 = (sx2,sy2)+100, 目标 = (sx,sy)+100 (sx>100 先折成 sx-200, 否则缝归中心)
"""
import sys, io, contextlib, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend  # noqa: E402

_buf = io.StringIO()


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(_buf):
        return fn(*a, **kw)


def points_of(strokes):
    pts = []
    for s in strokes:
        p = s.split(":")
        if p[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        for i in range(3, len(p) - 1, 2):
            pts.append((float(p[i]), float(p[i + 1])))
    return pts


def box_of(strokes):
    pts = points_of(strokes)
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def rect_map(strokes, rect):
    x1, y1, x2, y2 = [int(v) for v in rect]
    w, h = x2 - x1, y2 - y1
    out = []
    for s in strokes:
        p = s.split(":")
        if p[0] in ("1", "2", "3", "4", "6", "7"):
            for i in range(3, len(p) - 1, 2):
                x, y = float(p[i]), float(p[i + 1])
                p[i], p[i + 1] = str((x / 200) * w + x1), str((y / 200) * h + y1)
        out.append(":".join(p))
    return out


def kage_model(child_strokes, rect, sx, sy, sx2, sy2):
    """kage-bundle.js 的期望结果: 先拉伸(子件坐标), 再落位到 rect"""
    if sx != 0 or sy != 0:
        if sx > 100:
            sx -= 200
        else:
            sx2 = 0
            sy2 = 0
    if sx == 0 and sy == 0:
        return rect_map(child_strokes, rect)

    bx1, by1, bx2, by2 = box_of(child_strokes)

    # 注意 st() 内部自己会 +100, 所以这里传的是「偏移」而不是绝对坐标
    def st(dp, sp, p, lo, hi):
        if p < sp + 100:
            p1, p3, p2, p4 = lo, lo, sp + 100, dp + 100
        else:
            p1, p3, p2, p4 = sp + 100, dp + 100, hi, hi
        return p3 if p2 == p1 else (p - p1) * (p4 - p3) / (p2 - p1) + p3

    out = []
    for s in child_strokes:
        p = s.split(":")
        if p[0] in ("1", "2", "3", "4", "6", "7"):
            for i in range(3, len(p) - 1, 2):
                x, y = float(p[i]), float(p[i + 1])
                p[i] = str(st(sx, sx2, x, bx1, bx2))
                p[i + 1] = str(st(sy, sy2, y, by1, by2))
        out.append(":".join(p))
    return rect_map(out, rect)


def check(parent, ref, child_strokes, verbose=False):
    x1, y1, x2, y2 = ref[3:7]
    sx, sy, sx2, sy2 = int(ref[1]), int(ref[2]), int(ref[9]), int(ref[10])
    rect = (x1, y1, x2, y2)
    act = quiet(glyph_extend.unfold, ref[7],
                ((x1, y1, x2, y2), (ref[1], ref[2]), (ref[9], ref[10])))
    exp = kage_model(list(child_strokes), rect, sx, sy, sx2, sy2)
    pa, pe = points_of(act), points_of(exp)
    if len(pa) != len(pe):
        return (parent, ref[7], rect, (sx, sy, sx2, sy2), None, None, "点数不符")
    dev = max((max(abs(a[0] - b[0]), abs(a[1] - b[1])) for a, b in zip(pa, pe)),
              default=0.0)
    nx1, ny1, nx2, ny2 = float(x1), float(y1), float(x2), float(y2)
    out = sum(1 for (x, y) in pa
              if not (nx1 - .5 <= x <= nx2 + .5 and ny1 - .5 <= y <= ny2 + .5))
    return (parent, ref[7], rect, (sx, sy, sx2, sy2), dev, out, None)


# ---------- 1. 扫库: 有多少字形带接缝 ----------
print("扫库统计 (dbs 一行一表: name | ??? | data) ...", flush=True)
total, with_stretch, parents = 0, 0, []
seen_parents = set()
len_hist = {}
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    total += 1
    data = cols[2].strip()
    hot = None
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] != "99":
            continue
        len_hist[len(p)] = len_hist.get(len(p), 0) + 1
        if len(p) >= 11 and (p[1] != "0" or p[2] != "0"):
            hot = p
            break
    if hot:
        with_stretch += 1
        nm = cols[0].strip()
        if nm not in seen_parents and len(parents) < 24:
            seen_parents.add(nm)
            parents.append((nm, hot))
print(f"  条目 {total}, 其中含非零接缝的 99 引用: {with_stretch} "
      f"({with_stretch / max(total,1) * 100:.2f}%)")
print(f"  99 行字段数分布: {dict(sorted(len_hist.items()))}")
print("  (字段数 9/10 的行: Python 的 unfold 取 Lp[9]/Lp[10] 会 IndexError;"
      " 字段数 8 的会被补成 11)")

# ---------- 2. 逐例对拍 ----------
print("\n逐例对拍 (修好的 unfold vs KAGE 模型):")
worst, bad, checked = 0.0, 0, 0
# 你点名的两个: 直接取库里的原始 99 行, 免得手抄错字段
known = []
for nm in ("u5ffd-02", "u9f3b-j"):
    data = quiet(glyph_extend.get_data, nm)
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 11 and (p[1] != "0" or p[2] != "0"):
            known.append((nm, p))
            break
for parent, ref in known + parents:
    child_strokes = quiet(glyph_extend.unfold, ref[7],
                          (("0", "0", "200", "200"), (0, 0), (0, 0)))
    if not child_strokes:
        continue
    r = check(parent, ref, child_strokes)
    checked += 1
    if r[6] or r[4] is None or r[4] > 1e-6 or r[5] != 0:
        bad += 1
        print(f"  x {parent} → {ref[7]} rect={r[2]} 缝/目标={r[3]} "
              f"偏差={r[4]} 越界={r[5]} {r[6] or ''}")
    else:
        worst = max(worst, r[4])
        if checked <= 6 or parent in ("u5ffd-02", "u9f3b-j"):
            print(f"  v {parent} → {ref[7]} rect={r[2]} "
                  f"sx={r[3][0]} sy={r[3][1]} sx2={r[3][2]} sy2={r[3][3]}  "
                  f"偏差={r[4]:.3g} 越界=0")
print(f"\n对拍 {checked} 例, 不一致 {bad}, 最大偏差 {worst:.3g}")
