# -*- coding: utf-8 -*-
"""把 IDS 库里 [ ] 里的内容分类: 全包围索引 [n] / 穿越速成版 [a:b] / 矩阵版 [...]"""
import io, os, re, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PUB = r"D:\2026harucpp\web\public"
files = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]

RE_INDEX = re.compile(r"^\d+$")                       # §6.6 包围索引 [x]
RE_FAST = re.compile(r"^-?\d*:-?\d*$")                 # §6.2 速成版 [a:b] [:b] [a:] [:]
RE_MATRIX = re.compile(r"^[A-Za-z_,|]+$")              # §6.3/6.4 矩阵版 [fr,on,t]
RE_OTHER = re.compile(r".*")

cls = collections.Counter()
by_op = collections.Counter()
samples = collections.defaultdict(list)
index_cases = []
op_before = re.compile(r"([\u2ff0-\u2fff\u31ef])\[([^\]]*)\]")

for f in files:
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        head, _, body = line.partition("\t")
        for m in op_before.finditer(body):
            op, inner = m.group(1), m.group(2)
            by_op[op] += 1
            if RE_INDEX.match(inner):
                k = "① §6.6 包围索引 [n]"
            elif RE_FAST.match(inner):
                k = "② §6.2 速成版 [a:b]"
            elif RE_MATRIX.match(inner):
                k = "③ §6.3/6.4 矩阵版"
            else:
                k = "④ 其它"
            cls[k] += 1
            if len(samples[k]) < 5:
                samples[k].append(f"{head}  {body[:70]}")
            if k.startswith("①") and len(index_cases) < 40:
                index_cases.append((head, op, inner, body[:60]))

print("括号内容分类:")
for k in sorted(cls):
    print(f"  {k:22s} {cls[k]:6d}")
    for s in samples[k][:4]:
        print(f"        {s}")
print()
print("按算符分布:")
for op, n in by_op.most_common():
    print(f"  {op} U+{ord(op):04X}  {n}")
print()
print("全部「包围索引」用例 (库里就这么点, 正好当测试集):")
for head, op, inner, body in index_cases:
    print(f"  {head}  {op}[{inner}]   {body}")
