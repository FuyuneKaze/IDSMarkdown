# -*- coding: utf-8 -*-
"""
扒 IDS 表: 包围算符都拿什么当外框? 特别关注"复合外框"
(衣/行/鹿/麻/气/虍/尸... 这类需要把外框拆开才能把内部件塞进去的语义)
"""
import sys, io, os
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

IDS_DIR = r"D:\2026harucpp\web\public"
FILES = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]

OPS = {chr(c) for c in range(0x2FF0, 0x3000)} | {chr(0x31EF)}
ARITY3 = {"⿲", "⿳"}
SURROUND = set("⿴⿵⿶⿷⿸⿹⿺⿼⿽")


def parse(s, i=0):
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


def flat(node):
    if node is None:
        return ""
    if node[0] == "leaf":
        return node[1]
    return node[0] + "".join(flat(k) for k in node[1])


entries = []
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
print(f"IDS 条目总数: {len(entries):,}\n")

# ---- 1. 各包围算符的外框统计 ----
op_count = Counter()
outer_by_op = defaultdict(Counter)
ex_by_op = defaultdict(lambda: defaultdict(list))

for ch, ids in entries:
    node, _ = parse(ids)
    if not node or node[0] not in SURROUND:
        continue
    op, kids = node
    op_count[op] += 1
    if len(kids) != 2:
        continue
    o = flat(kids[0])
    if len(o) != 1:          # 只看单字外框
        continue
    outer_by_op[op][o] += 1
    if len(ex_by_op[op][o]) < 5:
        ex_by_op[op][o].append(ch)

print("=" * 80)
print("① 各包围算符的使用量 + 外框(单字)的多样性")
print("=" * 80)
names = {"⿴": "全包围", "⿵": "上包围", "⿶": "下包围", "⿷": "左包围",
         "⿸": "左上包围", "⿹": "右上包围", "⿺": "左下包围",
         "⿼": "右包围", "⿽": "右下包围"}
print(f"  {'算符':<4} {'名称':<9} {'总用次':>7} {'不同外框':>9}  top5 外框")
for op, c in op_count.most_common():
    oc = outer_by_op[op]
    top = " ".join(f"{k}({v})" for k, v in oc.most_common(5))
    print(f"  {op:<4} {names.get(op,'?'):<9} {c:>7} {len(oc):>9}  {top}")

# ---- 2. 关注"复合外框": 这些字当外框时, 中间没有天然空腔 ----
print()
print("=" * 80)
print("② 复合外框 (需要拆开才能塞内部件的那些)")
print("=" * 80)
COMPOUND = list("衣行鹿麻气虍尸广疒厂勹勺匕弋戈氏毋母年月日田由甲申") + \
           list("门門冂囗囬匚匸凵厂广") + list("走辶廴辵尢兀飞")
compound_set = set()
seen = set()
for op in outer_by_op:
    for o, c in outer_by_op[op].items():
        compound_set.add(o)

TARGET = list("衣行鹿麻气虍尸广疒厂勹勺走辶廴弋戈氏毋母")
print(f"  {'外框':<4} {'总用次':>7}  各算符分布 / 例子")
for o in TARGET:
    tot = 0
    detail = []
    for op in outer_by_op:
        c = outer_by_op[op].get(o, 0)
        if c:
            tot += c
            ex = "、".join(ex_by_op[op][o][:3])
            detail.append(f"{op}{c}次[{ex}]")
    if tot:
        print(f"  {o:<4} {tot:>7}  {'  '.join(detail)}")

# ---- 3. 外框多样性最高的那些字 (最可疑的"复合外框") ----
print()
print("=" * 80)
print("③ 作为外框时搭配最多不同内部件的字 top 25 (越靠前越像'通用容器')")
print("=" * 80)
agg = Counter()
for op in outer_by_op:
    for o, c in outer_by_op[op].items():
        agg[o] += c
print(f"  {'外框':<4} {'用次':>6}  例")
for o, c in agg.most_common(25):
    exs = []
    for op in outer_by_op:
        if outer_by_op[op].get(o):
            exs += ex_by_op[op][o][:2]
    print(f"  {o:<4} {c:>6}  {'、'.join(exs[:6])}")
