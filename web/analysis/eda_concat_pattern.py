# -*- coding: utf-8 -*-
"""
EDA 10: 只看"真正的拼接型复合字"(2 个 type-99 引用且带笔画),
        统计其组字模式 — 这直接决定算法该怎么做

问题:
  Q1 引用矩形是全画布还是有分配?
  Q2 pos0 / pos1 用的变体后缀是什么? (验证 -01/-02 假说)
  Q3 若"全画布 + 位置变体"成立, 则 overlap 是变体自带的, 无需计算
"""
import sys, io, json, re
from collections import Counter, defaultdict
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
db = json.load(open(CORE, encoding="utf-8"))["glyphs"]

# 所有 CJK 标准字
names = [k for k in db if re.fullmatch(r"u[4-9][0-9a-f]{3}", k)]
print(f"CJK 基本区标准字: {len(names)}")

# 还要看扩展区, 因为扩展区更可能是"拼接型"
names_ext = [k for k in db if re.fullmatch(r"u[23][0-9a-f]{4}", k)]
print(f"CJK 扩展区标准字: {len(names_ext)}")


def parse_refs(data):
    refs, has_stroke = [], False
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
        elif p[0] in ("1", "2", "3", "4", "6", "7", "0"):
            has_stroke = True
    return refs, has_stroke


def suffix_of(rn):
    """取位置后缀: u6728-01 -> -01 ; u6728-j -> -j ; u6728 -> (无)"""
    m = re.match(r"^u[0-9a-f]+(-[a-z0-9]+(?:-[a-z]+(?:-\d+)?)?)?$", rn)
    return m.group(1) if m and m.group(1) else "(无)"


# ---- 收集所有"2 引用"的拼接型 (递归穿透 alias) ----
print("\n扫描 (穿透 alias 链找真正的 2-ref 拼接)...")
pairs = []
depth_cache = {}

for nm in names + names_ext[:200000]:
    data = db[nm]
    seen = set()
    cur = data
    hops = 0
    # 穿透单引用 alias 链
    while hops < 8:
        refs, has_stroke = parse_refs(cur)
        if len(refs) == 1 and not has_stroke:
            nxt = refs[0][4].split("@")[0]
            if nxt in db and nxt not in seen:
                seen.add(nxt)
                cur = db[nxt]
                hops += 1
                continue
        break
    refs, has_stroke = parse_refs(cur)
    if len(refs) == 2:
        refs_sorted = sorted(refs, key=lambda r: r[0])
        pairs.append((nm, refs_sorted, has_stroke))

print(f"找到 2-ref 拼接型: {len(pairs)} 字\n")

if not pairs:
    sys.exit()

# ============================================================
print("=" * 76)
print("Q1. 引用矩形的形状分布")
print("=" * 76)
shape = Counter()
rect_vals = Counter()
for nm, refs, hs in pairs:
    for (x1, y1, x2, y2, rn) in refs:
        rect_vals[(x1, y1, x2, y2)] += 1
        if (x1, y1, x2, y2) == (0, 0, 200, 200):
            shape["全画布 (0,0,200,200)"] += 1
        elif x2 - x1 <= 130:
            shape["窄 (w<=130, 真分配)"] += 1
        else:
            shape["宽但非全画布"] += 1
tot = sum(shape.values())
for k, v in shape.most_common():
    print(f"  {k:<26} {v:>6} ({v/tot*100:5.1f}%)")
print(f"\n  最常见矩形值:")
for r, c in rect_vals.most_common(8):
    print(f"    {str(r):<24} {c:>6} ({c/tot*100:5.1f}%)")

# ============================================================
print()
print("=" * 76)
print("Q2. pos0 (左/上) 与 pos1 (右/下) 的变体后缀分布 ★核心")
print("=" * 76)
s0, s1 = Counter(), Counter()
for nm, refs, hs in pairs:
    s0[suffix_of(refs[0][4])] += 1
    s1[suffix_of(refs[1][4])] += 1

print(f"  {'pos0 (左/上)':<16} {'count':>7} {'占比':>8}   |  {'pos1 (右/下)':<16} {'count':>7} {'占比':>8}")
allk = list(dict.fromkeys(list(s0.keys()) + list(s1.keys())))
allk.sort(key=lambda k: -(s0.get(k, 0) + s1.get(k, 0)))
n = len(pairs)
for k in allk[:14]:
    print(f"  {k:<16} {s0.get(k,0):>7} {s0.get(k,0)/n*100:>7.1f}%   |  "
          f"{k:<16} {s1.get(k,0):>7} {s1.get(k,0)/n*100:>7.1f}%")

# ============================================================
print()
print("=" * 76)
print("Q3. 位置变体是否与'左右顺序'一致? (-01 该在 pos0, -02 该在 pos1)")
print("=" * 76)
match = Counter()
for nm, refs, hs in pairs:
    a, b = suffix_of(refs[0][4]), suffix_of(refs[1][4])
    match[(a, b)] += 1
print(f"  {'(pos0, pos1)':<22} {'count':>7} {'占比':>8}")
for k, c in match.most_common(12):
    print(f"  {str(k):<22} {c:>7} {c/n*100:>7.1f}%")

# ============================================================
print()
print("=" * 76)
print("Q4. 抽样: 真实拼接字的完整数据")
print("=" * 76)
rng = np.random.default_rng(1)
idx = rng.choice(len(pairs), size=min(10, len(pairs)), replace=False)
for i in idx:
    nm, refs, hs = pairs[i]
    cp = int(nm[1:], 16)
    ch = chr(cp)
    print(f"\n  {nm} ({ch})  has_stroke={hs}")
    for j, (x1, y1, x2, y2, rn) in enumerate(refs):
        print(f"    pos{j}: rect=({x1},{y1},{x2},{y2})  name={rn}")
