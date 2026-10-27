# -*- coding: utf-8 -*-
"""
EDA 9: 验证 GlyphWiki 组字的真实机制

假设: 真实复合字几乎都用"位置变体 + 全画布矩形(0,0,200,200)"拼接,
      位置信息烘在变体笔画里, 而非由矩形分配表达。

若成立 → 组字的正确核心不是"算 split/overlap", 而是"选对位置变体"。
"""
import sys, io, json, re
from collections import Counter
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
print(f"core_glyphs: {len(db)}\n")

# 取 CJK 基本区的"标准字" (u4e00-u9fff), 排除变体
names = [k for k in db if re.fullmatch(r"u[4-9][0-9a-f]{3}", k)]
print(f"CJK 基本区标准字: {len(names)}")

rng = np.random.default_rng(0)
sample = [names[i] for i in rng.choice(len(names), size=min(4000, len(names)), replace=False)]

rect_counter = Counter()
suffix_counter = Counter()
n_refs_total = 0
n_alias_only = 0
n_with_strokes = 0
rects_per_glyph = Counter()
component_shapes = Counter()

for nm in sample:
    data = db[nm]
    refs = []
    has_stroke = False
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
        elif p[0] in ("1", "2", "3", "4", "6", "7", "0"):
            has_stroke = True

    if has_stroke:
        n_with_strokes += 1
    if len(refs) == 0:
        continue
    if len(refs) == 1 and not has_stroke:
        n_alias_only += 1
    rects_per_glyph[len(refs)] += 1
    n_refs_total += len(refs)

    for (x1, y1, x2, y2, rn) in refs:
        rect_counter[(x1, y1, x2, y2)] += 1
        # 变体后缀
        m = re.match(r"^u[0-9a-f]+(-[a-z0-9\-]+)?$", rn)
        suffix_counter[m.group(1) if m and m.group(1) else "(无后缀)"] += 1
        w, h = x2 - x1, y2 - y1
        # 形状分类
        if (x1, y1, x2, y2) == (0, 0, 200, 200):
            component_shapes["全画布 (0,0,200,200)"] += 1
        elif w <= 120 and h >= 160:
            component_shapes["半宽竖条 (左右布局)"] += 1
        elif h <= 120 and w >= 160:
            component_shapes["半高横条 (上下布局)"] += 1
        elif w <= 140 and h <= 140:
            component_shapes["小块 (偏居一角)"] += 1
        else:
            component_shapes["其他"] += 1

print(f"\n{'='*70}")
print("1. 每个复合字含几个 type-99 引用")
print(f"{'='*70}")
for k in sorted(rects_per_glyph)[:10]:
    print(f"  {k} 个引用: {rects_per_glyph[k]:>6} 字  ({rects_per_glyph[k]/len(sample)*100:5.1f}%)")
print(f"  纯 alias (1引用无笔画): {n_alias_only} / {len(sample)}")
print(f"  含笔画(直绘): {n_with_strokes} / {len(sample)}")

print(f"\n{'='*70}")
print("2. 部件矩形的形状分布 ★关键")
print(f"{'='*70}")
tot = sum(component_shapes.values())
for k, v in component_shapes.most_common():
    print(f"  {k:<28} {v:>7}  ({v/tot*100:5.1f}%)")

print(f"\n{'='*70}")
print("3. 最常见的具体矩形值")
print(f"{'='*70}")
for r, c in rect_counter.most_common(12):
    print(f"  {str(r):<26} {c:>7}  ({c/n_refs_total*100:5.1f}%)")

print(f"\n{'='*70}")
print("4. 引用的变体后缀分布 (看是否系统使用位置变体)")
print(f"{'='*70}")
for s, c in suffix_counter.most_common(22):
    print(f"  {s:<16} {c:>7}  ({c/n_refs_total*100:5.1f}%)")

print(f"\n  引用总数: {n_refs_total}")
