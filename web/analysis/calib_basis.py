# -*- coding: utf-8 -*-
"""校准 central_box 的放大率: 设计者在真字形里到底把内部件放大了几倍?

设计者的放大率 = 真字形里内部件 99 矩形的尺寸 / 内部件墨迹盒尺寸
我们的放大率   = 内部件墨迹盒尺寸 / 基准框尺寸        (基准越小 → 放大越多)
基准 = (1-alpha)*墨迹盒 + alpha*central_box,  alpha=0 → 严格贴合(放大 1.0x)
"""
import sys, io, os, re, contextlib, statistics

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity, central_box  # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


PUB = r"D:\2026harucpp\web\public"
SUR = set("⿴⿵⿶⿷⿸⿹⿺⿼⿽")
OPCH = "".join(SUR)


def strip_notation(body):
    body = body.split("\t")[0]
    body = re.sub(r"#\([^)]*\)|\{[^}]*\}|\([^)]*\)", "", body)
    return body.replace(".", "").strip()


def refs_of(char):
    name = "u%x" % ord(char)
    for _ in range(3):
        data = q(glyph_extend.get_data, name)
        if not data:
            return []
        inner = [(s.split(":")[7].split("@")[0], tuple(float(v) for v in s.split(":")[3:7]))
                 for s in data.split("$") if s.split(":")[0] == "99" and len(s.split(":")) >= 8]
        if not inner:
            return []
        if len(inner) == 1 and inner[0][0] == name + "-j":
            name = inner[0][0]
            continue
        return inner
    return []


def first_char(node):
    for ch in node:
        if 0x2FF0 <= ord(ch) <= 0x2FFF or ord(ch) == 0x31EF or ch in ".[]0123456789:-,":
            continue
        return ch
    return ""


records = []
seen = set()
for f in ("ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"):
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        char, _, body = line.rstrip("\n").partition("\t")
        char = char.strip()
        if not char or char in seen:
            continue
        for raw in body.split(";"):
            clean = strip_notation(raw)
            if not clean or clean[0] not in SUR:
                continue
            m = re.match(r"^([%s])(\[(\d+)\])?\s*" % OPCH, clean)
            if not m:
                continue
            rest = clean[m.end():]
            op = m.group(1)
            # 取两个子节点
            kids, _ = ids_anal.split_children(rest, 0, 2) if hasattr(ids_anal, "split_children") else ([], 0)
            if not kids:
                a = first_char(rest)
                b = first_char(rest[rest.find(a) + 1:]) if a else ""
            else:
                a, b = first_char(kids[0]), first_char(kids[1])
            if not a or not b:
                continue
            refs = refs_of(char)
            if len(refs) < 2:
                continue
            cont = [r for r in refs if r[0].startswith("u%x" % ord(a))]
            inn = [r for r in refs if r[0].startswith("u%x" % ord(b))]
            if not cont or not inn:
                continue
            cname, crect = cont[0]
            iname, irect = inn[0]
            cw, ch = crect[2] - crect[0], crect[3] - crect[1]
            if cw <= 0 or ch <= 0:
                continue
            # 设计者矩形 → 容器 0-200 空间
            nw = irect[2] - irect[0]
            nh = irect[3] - irect[1]
            dscale_x = (nw / cw * 200.0) / 1.0
            # 内部件自己的墨迹盒 (0-200 空间)
            flat = q(glyph_extend.return_bone, iname)
            boxes = q(cavity.ink_boxes, flat, False, True)
            if not boxes:
                continue
            iw = max(b[2] for b in boxes) - min(b[0] for b in boxes)
            ih = max(b[3] for b in boxes) - min(b[1] for b in boxes)
            if iw <= 0 or ih <= 0:
                continue
            # 设计者放大率: 内部件内容被放进 nw 宽的格子
            dmag = (nw / cw * 200.0) / iw
            cb = q(central_box.central_box, flat)
            if not cb:
                continue
            inkbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                      max(b[2] for b in boxes), max(b[3] for b in boxes))
            records.append((char, iname, inkbox, cb, dmag))
            seen.add(char)
            break
        if len(records) >= 150:
            break
    if len(records) >= 150:
        break

print(f"样本 {len(records)} 个字 (设计者放大率 = 99矩形宽 / 内部件墨迹盒宽)\n")
med = statistics.median(r[4] for r in records)
print(f"  设计者放大率: 中位 {med:.2f}x, 均值 {statistics.mean(r[4] for r in records):.2f}x")
hi = sum(1 for r in records if r[4] > 1.0)
print(f"  其中设计者**放大**的 {hi}/{len(records)} = {hi/len(records)*100:.0f}%\n")

print(f"{'alpha':>6s} {'我们的放大率(中位)':>20s} {'与设计者中位差':>16s}")
best = None
for alpha in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0]:
    mags = []
    for _c, _n, ink, cb, _d in records:
        w = (1 - alpha) * (ink[2] - ink[0]) + alpha * (cb[2] - cb[0])
        if w > 0:
            mags.append((ink[2] - ink[0]) / w)
    m = statistics.median(mags)
    diff = abs(m - med)
    if best is None or diff < best[0]:
        best = (diff, alpha, m)
    print(f"{alpha:6.1f} {m:20.2f} {diff:16.2f}")
print(f"\n  最接近设计者中位的 alpha ≈ {best[1]}  (我们 {best[2]:.2f}x vs 设计者 {med:.2f}x)")

# 按"基准/墨迹"比例分组: 看设计者放大率是否随"穿心程度"变化
print("\n  设计者放大率 vs 内部件的'穿心程度' (基准宽/墨迹宽 越小 = 越穿心):")
groups = [("贴边框形 (ratio>0.65)", lambda r: (r[3][2] - r[3][0]) / (r[2][2] - r[2][0]) > 0.65),
          ("中间 (0.45~0.65)", lambda r: 0.45 < (r[3][2] - r[3][0]) / (r[2][2] - r[2][0]) <= 0.65),
          ("穿心交叉 (ratio<=0.45)", lambda r: (r[3][2] - r[3][0]) / (r[2][2] - r[2][0]) <= 0.45)]
for label, fn in groups:
    sub = [r for r in records if fn(r)]
    if sub:
        print(f"    {label:22s} n={len(sub):3d}  设计者放大率中位 "
              f"{statistics.median(x[4] for x in sub):.2f}x   "
              f"（纯 central_box 会给 {statistics.median((x[2][2]-x[2][0])/(x[3][2]-x[3][0]) for x in sub):.2f}x）")
