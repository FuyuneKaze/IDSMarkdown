# -*- coding: utf-8 -*-
"""看 fallback 后实际用的字形数据 (u670b-j / u52ff-jn) 有何特殊"""
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for ln, line in enumerate(glyph_extend.dbs):
    c = line.split(" | ")
    if len(c) >= 3:
        IDX[c[0].strip()] = c[2].strip()


def dump(name, indent="  "):
    d = IDX.get(name)
    if d is None:
        print(f"{indent}{name}: 【不存在】")
        return
    segs = d.split("$")
    kinds = {}
    for s in segs:
        k = s.split(":")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{indent}{name}: len={len(d)}  段数={len(segs)}  类型={kinds}")
    if len(d) < 300:
        print(f"{indent}   {d}")


print("=== ⿱艹朋 实际用到的字形链 ===")
print("  上: u8279-03 (存在)")
dump("u8279-03", "     ")
print("  下: u670b-04 (不存在) → fallback:")
for n in ["u670b-04", "u670b", "u670b-j"]:
    dump(n, "     ")

print("\n=== ⿱勿心 实际用到的字形链 ===")
print("  上: u52ff-03 (不存在) → fallback:")
for n in ["u52ff-03", "u52ff", "u52ff-jn"]:
    dump(n, "     ")
print("  下: u5fc3-04 (存在)")
dump("u5fc3-04", "     ")
for n in ["u5fc3-09"]:
    dump(n, "     ")

print("\n=== 对照: ⿱日木 (能正常显示) ===")
for n in ["u65e5-03", "u6728-04"]:
    dump(n, "     ")

print("\n=== 对照: ⿱宀丁 (能正常显示) ===")
for n in ["u5b80-03", "u4e01-04", "u4e01", "u4e01-j"]:
    dump(n, "     ")
