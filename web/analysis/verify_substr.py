# -*- coding: utf-8 -*-
"""
验证: 用"子串枚举 + 取行号最大"能否精确复刻原版 get_data 的语义

原版:
    for line in datas:
        cols = line.split(' | ')
        if len(cols) < 3: continue
        name = cols[0].strip()
        if name in targets:          # 子串包含
            data = cols[2].strip()   # 反复覆盖 → 最后一个匹配胜出
"""
import sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend
DB = glyph_extend.dbs
print(f"dbs = {len(DB):,} 行")

# ---- 索引: name -> (行号, data), 全量不过滤 ----
t0 = time.time()
IDX = {}
for ln, line in enumerate(DB):
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    IDX[cols[0].strip()] = (ln, cols[2].strip())
print(f"全量索引 {len(IDX):,} 条 ({time.time()-t0:.2f}s)")


def fast(targets):
    """子串枚举 + 行号最大"""
    best = -1
    bd = ""
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(targets[i:j])
            if h is not None and h[0] > best:
                best = h[0]
                bd = h[1]
    return bd


def orig(targets, datas):
    """原版逐字复刻"""
    data = ""
    for line in datas:
        cols = line.split(" | ")
        if len(cols) < 3:
            continue
        name = cols[0].strip()
        if name in targets:
            data = cols[2].strip()
    return data


tests = ["u670b-04", "u8279-03", "u6728-02", "u53e3-01", "u5fc4-01",
         "u670b", "u4e00", "u20000-01", "u670b-99", "u65e5-04",
         "u5b80-03", "u4e01-04", "notexistatall", "u516b-04"]

print(f"\n{'查询':<14} {'fast':>6} {'orig':>6}  {'耗时(orig)':>10}  结果")
print("-" * 62)
bad = 0
t_fast = 0.0
for t in tests:
    t0 = time.time()
    a = fast(t)
    t_fast += time.time() - t0
    t0 = time.time()
    b = orig(t, DB)
    dt = time.time() - t0
    same = a == b
    if not same:
        bad += 1
    print(f"{t:<14} {len(a):>6} {len(b):>6}  {dt:>9.2f}s  "
          f"{'一致' if same else '!!不一致'}")

print("-" * 62)
print(f"不一致: {bad}/{len(tests)}")
print(f"fast 总耗时 {t_fast*1000:.2f}ms   平均 {t_fast/len(tests)*1000:.3f}ms/次")
print(f"orig 平均 {(lambda: 0)() if False else '见上表'}")

# 抽样更大的对比 (只对比 fast 的耗时, orig 太慢)
import random
random.seed(0)
names = [k for k in IDX if k.startswith("u") and len(k) == 5]
sample = random.sample(names, 200)
t0 = time.time()
for n in sample:
    fast(n + "-04")
print(f"\n200 次 fast('uXXXX-04'): {(time.time()-t0)*1000:.1f}ms")
