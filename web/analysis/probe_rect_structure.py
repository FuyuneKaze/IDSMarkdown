# -*- coding: utf-8 -*-
"""
探查 2: 直接看真实字形数据, 确认"左右比例"该怎么定义

不看任何中间产物, 只从 core_glyphs.json 读原始 KAGE 数据。
"""
import sys, io, json, re
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
IDS = r"D:\2026harucpp\web\public\ids_lv1.txt"

db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
print(f"core_glyphs: {len(db)}\n")

OPS = set(chr(c) for c in range(0x2FF0, 0x3000)) | {chr(0x31EF)}


def parse(data):
    refs, strokes = [], []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
        elif p[0] in ("1", "2", "3", "4", "6", "7"):
            strokes.append(seg)
    return refs, strokes


def resolve(name, max_hops=10):
    """穿透 alias 链, 返回 (最终data, refs, strokes, 链)"""
    chain = [name]
    data = db.get(name)
    if data is None:
        return None, [], [], chain
    for _ in range(max_hops):
        refs, strokes = parse(data)
        if len(refs) == 1 and not strokes:
            nxt = refs[0][4].split("@")[0]
            if nxt in db and nxt != name:
                chain.append(nxt)
                data = db[nxt]
                name = nxt
                continue
        break
    refs, strokes = parse(data)
    return data, refs, strokes, chain


# ---- 取几个典型 ⿰ 字 ----
targets = ["什", "仁", "仅", "明", "江", "好", "村", "休", "时", "们",
           "朋", "林", "妈", "红", "铁", "银", "验", "期", "张嘴"[:1] or "张"]

print("=" * 92)
print("典型 ⿰ 字的原始数据 (穿透 alias 后)")
print("=" * 92)
for ch in targets:
    cp = ord(ch)
    nm = f"u{cp:x}"
    if nm not in db:
        print(f"\n{ch} ({nm}): 不在库中")
        continue
    data, refs, strokes, chain = resolve(nm)
    print(f"\n{ch} ({nm})  alias链: {' → '.join(chain)}")
    if len(refs) == 0:
        print(f"  !! 无 type-99 引用 (直绘笔画 {len(strokes)} 段)")
        continue
    refs_sorted = sorted(refs, key=lambda r: r[0])
    for i, (x1, y1, x2, y2, rn) in enumerate(refs_sorted):
        print(f"  部件{i}: rect=({x1},{y1},{x2},{y2})  宽={x2-x1:<4} 高={y2-y1:<4} name={rn}")
    if len(refs_sorted) == 2:
        a, b = refs_sorted
        wa, wb = a[2] - a[0], b[2] - b[0]
        print(f"  → 矩形宽比 = {wa}/{wa+wb} = {wa/(wa+wb):.3f}")
        print(f"  → 矩形 x 范围: 左[{a[0]},{a[2]}] 右[{b[0]},{b[2]}]  "
              f"{'分离' if a[2] <= b[0] else '重叠'}")

# ============================================================
print()
print("=" * 92)
print("统计: 从 ids 取 ⿰XY, 看矩形结构模式")
print("=" * 92)

pairs = []
with open(IDS, encoding="utf-8") as f:
    for line in f:
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        ch = parts[0]
        for ids in parts[1:]:
            if len(ids) == 3 and ids[0] == "⿰" and ids[1] not in OPS and ids[2] not in OPS:
                pairs.append((ch, ids[1], ids[2]))
print(f"⿰XY 候选: {len(pairs)}")

n_ok = 0
n_alias_fail = 0
n_refs2 = 0
n_other = 0
rect_pattern = []
separation = []

for ch, c1, c2 in pairs[:6000]:
    nm = f"u{ord(ch):x}"
    if nm not in db:
        n_alias_fail += 1
        continue
    data, refs, strokes, chain = resolve(nm)
    if len(refs) != 2:
        n_other += 1
        continue
    n_refs2 += 1
    a, b = sorted(refs, key=lambda r: r[0])
    wa, wb = a[2] - a[0], b[2] - b[0]
    wsum = wa + wb
    if wsum <= 0:
        continue
    n_ok += 1
    rect_pattern.append((wa / wsum, a, b))
    separation.append(a[2] - b[0])

print(f"  成功 2-ref: {n_ok}   非2ref: {n_other}   缺字: {n_alias_fail}")
if rect_pattern:
    rs = np.array([p[0] for p in rect_pattern])
    sp = np.array(separation)
    print(f"\n  矩形宽比 (左/(左+右)): mean={rs.mean():.3f} std={rs.std():.3f}")
    print("   分位: " + "  ".join(f"p{q}={np.percentile(rs,q):.3f}" for q in [5, 25, 50, 75, 95]))
    print(f"\n  左矩形右边界 - 右矩形左边界 (a.x2 - b.x1):")
    print(f"   mean={sp.mean():.1f} std={sp.std():.1f}")
    print(f"   >0 (两矩形重叠) 占比: {(sp > 0).mean()*100:.1f}%")
    print(f"   <0 (两矩形分离) 占比: {(sp < 0).mean()*100:.1f}%")
    print("   分位: " + "  ".join(f"p{q}={np.percentile(sp,q):.0f}" for q in [5, 25, 50, 75, 95]))

    print(f"\n  最常见的 (左矩形, 右矩形) 组合:")
    from collections import Counter
    combo = Counter()
    for r, a, b in rect_pattern:
        combo[((a[0], a[2]), (b[0], b[2]))] += 1
    for k, c in combo.most_common(12):
        print(f"    {str(k):<34} {c:>5}")
