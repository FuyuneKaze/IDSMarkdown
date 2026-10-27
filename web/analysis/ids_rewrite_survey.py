# -*- coding: utf-8 -*-
"""
统计: 你提的六条重写规则, 在 IDS 库里各能匹配多少字?

模式 (LHS):  外层算符( 第一个操作数是某个复合 ) 第二个操作数
"""
import sys, io
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IDS_DIR = r"D:\2026harucpp\web\public"
FILES = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]
OPS = {chr(c) for c in range(0x2FF0, 0x3000)} | {chr(0x31EF)}
ARITY3 = {"⿲", "⿳"}


def parse(s, i=0):
    """→ (node, next) ; node = ('leaf', ch) | (op, [kids])"""
    if i >= len(s):
        return None, i
    ch = s[i]
    if ch not in OPS:
        return ("leaf", ch), i + 1
    ar = 3 if ch in ARITY3 else 2
    i += 1
    kids = []
    for _ in range(ar):
        n, i = parse(s, i)
        if n is None:
            return None, i
        kids.append(n)
    return (ch, kids), i


def flat(n):
    if n is None:
        return ""
    if n[0] == "leaf":
        return n[1]
    return n[0] + "".join(flat(k) for k in n[1])


# 六条规则: (规则号, 外层算符, 第一个操作数应有的算符, 说明)
RULES = [
    (1, "⿸", "⿰", "⿸xy → ⿰a⿱by"),
    (2, "⿸", "⿱", "⿸xy → ⿱a⿰by"),
    (3, "⿵", "⿰", "⿵xy → ⿲ayb"),
    (4, "⿵", "⿲", "⿵xy → ⿱c⿲ayb"),
    (5, "⿴", "⿰", "⿴xy → ⿲ayb"),
    (6, "⿴", "⿸", "⿴xy → ⿱⿸ayb"),
]

entries = []
import os
for fn in FILES:
    p = os.path.join(IDS_DIR, fn)
    if not os.path.exists(p):
        continue
    with open(p, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            for ids in parts[1:]:
                if ids:
                    entries.append((parts[0], ids))
print(f"IDS 条目 {len(entries):,}\n")

hits = defaultdict(list)
for ch, ids in entries:
    node, _ = parse(ids)
    if not node or node[0] == "leaf":
        continue
    op, kids = node
    if len(kids) != 2:
        continue
    inner = kids[0]
    if inner[0] == "leaf":
        continue
    for rno, rop, iop, desc in RULES:
        if op == rop and inner[0] == iop:
            hits[rno].append((ch, ids, inner))

print("=" * 80)
print("各规则的匹配量")
print("=" * 80)
print(f"  {'#':<3} {'规则':<22} {'匹配字数':>8}   例")
print("  " + "-" * 74)
for rno, rop, iop, desc in RULES:
    lst = hits.get(rno, [])
    ex = "、".join(c for c, _, _ in lst[:8])
    print(f"  {rno:<3} {desc:<22} {len(lst):>8}   {ex}")

print()
print("=" * 80)
print("各规则的前几个例子 (含拆解)")
print("=" * 80)
for rno, rop, iop, desc in RULES:
    lst = hits.get(rno, [])
    if not lst:
        print(f"\n  规则{rno} ({desc}): 无匹配")
        continue
    print(f"\n  规则{rno}  {desc}")
    for ch, ids, inner in lst[:6]:
        a = flat(inner[1][0])
        b = flat(inner[1][1])
        y = flat(inner)  # 占位
        # 第二个操作数
        node, _ = parse(ids)
        second = flat(node[1][1])
        print(f"    {ch} (U+{ord(ch):04X})  {ids}   → x={flat(inner)} = {inner[0]}{a}{b}, "
              f"y={second}")

print()
print("=" * 80)
print("补充: 外层算符 × 第一个操作数算符 的完整共现矩阵 (只用单字操作数)")
print("=" * 80)
mat = Counter()
for ch, ids in entries:
    node, _ = parse(ids)
    if not node or node[0] == "leaf" or len(node[1]) != 2:
        continue
    op, kids = node
    k0, k1 = kids
    if k0[0] == "leaf" and k1[0] == "leaf":
        mat[(op, "单字")] += 1
    elif k0[0] != "leaf":
        mat[(op, k0[0])] += 1
outer_ops = ["⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"]
inner_ops = ["单字", "⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"]
print("  " + "外\\内".ljust(6) + "".join(f"{i:>7}" for i in inner_ops))
for o in outer_ops:
    row = f"  {o:<6}"
    for i in inner_ops:
        v = mat.get((o, i), 0)
        row += f"{v:>7}" if v else f"{'.':>7}"
    print(row)
