# -*- coding: utf-8 -*-
"""诊断 ⿱艹朋 / ⿰𠀀木 为什么异常"""
import sys, io, traceback, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend
INDEX = {}
for line in glyph_extend.dbs:
    if not line.startswith(" u"):
        continue
    c = line.split(" | ")
    if len(c) >= 3:
        INDEX[c[0].strip()] = c[2].strip()
glyph_extend.get_data = lambda t, d=None, **kw: INDEX.get(t, "")

import ids_anal
from kage_contour import ch_uni

for ids, op, parts, sfx in [
    ("⿱艹朋", "⿱", ["艹", "朋"], ["-03", "-04"]),
    ("⿰𠀀木", "⿰", ["𠀀", "木"], ["-01", "-02"]),
]:
    names = [ch_uni(p) for p in parts]
    print("=" * 66)
    print(f"{ids}   op={op}  names={names}")
    for n, s in zip(names, sfx):
        d = INDEX.get(n + s, "")
        d2 = INDEX.get(n, "")
        print(f"   {n}{s:<4}: {'有' if d else '【缺失】':<6} len={len(d):<5} | "
              f"{n}(无后缀): {'有' if d2 else '缺失'} len={len(d2)}")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            g = ids_anal.IDS(op, names)
        print(f"   → OK  {len(g or '')} chars")
    except Exception:
        print("   → 异常:")
        for ln in traceback.format_exc().splitlines()[-7:]:
            print("      " + ln)

print("=" * 66)
print("检查 ids_anal.IDS 实现了哪些操作符:")
import inspect
src = inspect.getsource(ids_anal.IDS)
for ln in src.splitlines():
    if "case" in ln:
        print("   " + ln.strip())
