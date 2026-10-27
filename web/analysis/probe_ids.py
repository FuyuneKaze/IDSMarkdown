# -*- coding: utf-8 -*-
"""探查: ids 文件格式 + 定位 ⿰XY 两部件结构的字"""
import sys, io, re
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IDS = r"D:\2026harucpp\web\public\ids_lv1.txt"

print("=== 前 8 行原始 ===")
with open(IDS, encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 8:
            break
        print(f"  {i}: {line.rstrip()!r}")

# 统计结构
print("\n=== 解析 ===")
n_lines = 0
n_tab1 = 0
op_counter = Counter()
simple_binary = 0
examples = []

OPS = set(chr(c) for c in range(0x2FF0, 0x3000)) | {chr(0x31EF)}

with open(IDS, encoding="utf-8") as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        n_lines += 1
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        n_tab1 += 1
        ch = parts[0]
        for ids in parts[1:]:
            if not ids:
                continue
            op_counter[ids[0]] += 1
            # 简单的 ⿰XY (恰好3字符: 操作符+两部件)
            if len(ids) == 3 and ids[0] == "⿰":
                a, b = ids[1], ids[2]
                if a not in OPS and b not in OPS:
                    simple_binary += 1
                    if len(examples) < 15:
                        examples.append((ch, ids))

print(f"  总行数: {n_lines}   含 tab 的行: {n_tab1}")
print(f"  ⿰XY 简单两部件(3字符): {simple_binary}")
print(f"\n  操作符分布 (前 10):")
for op, c in op_counter.most_common(10):
    name = {0x2FF0: "⿰左右", 0x2FF1: "⿱上下", 0x2FF2: "⿲左中右", 0x2FF3: "⿳上中下",
            0x2FF4: "⿴全包", 0x2FF5: "⿵上包", 0x2FF6: "⿶下包", 0x2FF7: "⿷左包",
            0x2FF8: "⿸左上", 0x2FF9: "⿹右上", 0x2FFA: "⿺左下", 0x2FFB: "⿻重叠"}.get(ord(op), "")
    print(f"    {op} U+{ord(op):04X} {name:<10} {c}")

print(f"\n  ⿰XY 示例:")
for ch, ids in examples:
    print(f"    {ch}  {ids}  (U+{ord(ch):04X})")
