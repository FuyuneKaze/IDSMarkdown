# -*- coding: utf-8 -*-
"""扫 IDS 数据库: 白式延展语法的括号/特殊算符到底用了多少"""
import io, os, re, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PUB = r"D:\2026harucpp\web\public"
files = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]

pats = {
    "[ 括号修饰": re.compile(r"\["),
    "㇯ 减法": re.compile("\u31ef"),
    "⿼ 右包围": re.compile("\u2ffc"),
    "⿾ 镜像": re.compile("\u2ffe"),
    "⿿ 旋转": re.compile("\u2fff"),
    "#( 笔画链": re.compile(r"#\("),
    "{ 唯一化": re.compile(r"\{"),
    ". 部件分隔": re.compile(r"\."),
}

tot = collections.Counter()
rows = collections.Counter()
examples = collections.defaultdict(list)
bracket_ops = collections.Counter()

for f in files:
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        print("(缺)", p)
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        rows[f] += 1
        body = line.split("\t")[-1]
        for k, pat in pats.items():
            if pat.search(body):
                tot[k] += 1
                if len(examples[k]) < 5:
                    examples[k].append(line[:100])
        for m in re.finditer(r"(.)\[", body):
            bracket_ops[m.group(1)] += 1

print("条目数:", dict(rows), " 合计", sum(rows.values()))
print()
for k in pats:
    print(f"{k:14s} {tot[k]:8d}")
    for e in examples[k][:4]:
        print("      ", e)
print()
print("括号前一个字符的分布 (前 15):", bracket_ops.most_common(15))
