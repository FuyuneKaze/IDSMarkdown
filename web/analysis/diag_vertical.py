# -*- coding: utf-8 -*-
"""
诊断: ⿱ 为什么一个都合不成

怀疑点1: 我的索引加了 startswith(" u") 过滤, 而 glyph_extend.get_data 原版没有
怀疑点2: -03/-04 变体本身普遍缺失
"""
import sys, io, time
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

t0 = time.time()
import glyph_extend
print(f"[0] import: {time.time()-t0:.2f}s   dbs={len(glyph_extend.dbs):,}")

# ---- 1. 行前缀分布 ----
print("\n[1] dump 行的前 2 字符分布:")
pref = Counter(l[:2] for l in glyph_extend.dbs)
for p, c in pref.most_common(10):
    print(f"    {p!r:<8} {c:>10,}")

# ---- 2. 全量索引 (完全复刻原版 get_data 的匹配规则: 不看过滤, 最后一个胜出) ----
t0 = time.time()
FULL = {}
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    FULL[cols[0].strip()] = cols[2].strip()
print(f"\n[2] 全量索引(无过滤): {len(FULL):,}  ({time.time()-t0:.2f}s)")

# 我的过滤索引
FILT = {}
for line in glyph_extend.dbs:
    if not line.startswith(" u"):
        continue
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    FILT[cols[0].strip()] = cols[2].strip()
print(f"    我的过滤索引:     {len(FILT):,}")

only_full = set(FULL) - set(FILT)
print(f"    只在全量索引里 (我漏掉的): {len(only_full):,}")
if only_full:
    print(f"      举例: {sorted(only_full)[:12]}")

# ---- 3. 关键: ⿱ 用的 -03/-04 变体到底有没有 ----
print("\n[3] ⿱ 需要的 -03(上) / -04(下) 变体:")
tests = [("艹", "u8279"), ("朋", "u670b"), ("宀", "u5b80"), ("丁", "u4e01"),
         ("日", "u65e5"), ("木", "u6728"), ("口", "u53e3"), ("立", "u7acb"),
         ("亠", "u4ea0"), ("八", "u516b")]
print(f"    {'字':<4} {'名':<9} {'-03':<8} {'-04':<8} {'-01':<8} {'-02':<8} {'本体':<6}")
for ch, nm in tests:
    row = []
    for sfx in ["-03", "-04", "-01", "-02", ""]:
        k = nm + sfx
        ln = len(FULL.get(k, ""))
        row.append(f"{'有' if ln else '无'}({ln})" if ln else "无")
    print(f"    {ch:<4} {nm:<9} {row[0]:<8} {row[1]:<8} {row[2]:<8} {row[3]:<8} {row[4]:<6}")

# ---- 4. 统计: 有多少 uXXXX 有 -03 / -04 ----
import re
cjk = [k for k in FULL if re.fullmatch(r"u[2-9][0-9a-f]{3,5}", k)]
print(f"\n[4] CJK 标准字 {len(cjk):,} 个, 其中有:")
for sfx in ["-01", "-02", "-03", "-04"]:
    n = sum(1 for k in cjk if (k + sfx) in FULL)
    print(f"    {sfx} 变体: {n:>7,}  ({n/len(cjk)*100:.1f}%)")

# ---- 5. 直接用原版逻辑跑 ⿱ ----
print("\n[5] 用原版逻辑(不带我的索引)跑 ⿱:")
glyph_extend.dbs = glyph_extend.dbs  # 保持原样
import ids_anal
from kage_contour import ch_uni

for op, chs in [("⿱", ["艹", "朋"]), ("⿱", ["宀", "丁"]), ("⿱", ["日", "木"]),
                ("⿰", ["氵", "工"])]:
    names = [ch_uni(c) for c in chs]
    tag = op + "".join(chs)
    try:
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            g = ids_anal.IDS(op, names)
        print(f"    {tag:<8} → {'OK ' + str(len(g)) + ' chars' if g else '【空】'}")
    except Exception as e:
        print(f"    {tag:<8} → 异常 {type(e).__name__}: {e}")
