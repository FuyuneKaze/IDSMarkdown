# -*- coding: utf-8 -*-
"""验证核心链路: ids_anal.IDS → kage_contour.extract_one"""
import sys, io, time, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

t0 = time.time()
import glyph_extend
print(f"[1] import glyph_extend: {time.time()-t0:.1f}s   dbs={len(glyph_extend.dbs):,} 行")

t0 = time.time()
INDEX = {}
for line in glyph_extend.dbs:
    if not line.startswith(" u"):
        continue
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    INDEX[cols[0].strip()] = cols[2].strip()
print(f"[2] 建索引: {time.time()-t0:.1f}s   {len(INDEX):,} 个字形")

glyph_extend.get_data = lambda t, d=None, **kw: INDEX.get(t, "")
print(f"[3] 已替换 get_data  (原 get_data 是线性扫描)")

# 验证 patch 生效: 单独调一次
t0 = time.time()
d = glyph_extend.get_data("u5fc4")
print(f"[4] 查 u5fc4: {time.time()-t0*1000:.1f}ms  len={len(d)}")

import ids_anal
from kage_contour import extract_one, ch_uni
print(f"[5] import ids_anal OK")

# ---- 测你的例子 ----
t0 = time.time()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    glyph = ids_anal.IDS("⿰", [ch_uni("忄"), ch_uni("忽")])
dt = time.time() - t0
print(f"[6] ids_anal.IDS('⿰',[u5fc4,u5ffd]): {dt:.3f}s  -> {len(glyph or '')} chars")
if glyph:
    print(f"    glyph 前缀: {glyph[:150]}")
else:
    print("    !! 返回空")
    print("    IDS() stdout:", buf.getvalue()[-400:])

if glyph:
    t0 = time.time()
    r = extract_one("test", glyph)
    print(f"[7] extract_one: {time.time()-t0:.3f}s")
    print(f"    keys={list(r.keys())}  error={r.get('error')}")
    cs = r.get("contours", [])
    print(f"    contours={len(cs)}  总点数={sum(len(c) for c in cs)}")
    if cs:
        print(f"    首个轮廓前 4 点: {cs[0][:4]}")
