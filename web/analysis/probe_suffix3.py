# -*- coding: utf-8 -*-
"""全库 99 引用里的后缀统计: 哪些后缀真的被"用"了 (渲染数据层面)

与 IDS 标记层面的统计不同: 这里数的是 dump 里 $ 分隔的 99 行末尾的引用名。
"""
import sys, io, re
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend

REF = re.compile(r"u[0-9a-f]+-(\d+)")
NAME = re.compile(r"^(u[0-9a-f]+)(?:-(.+))?$")

ref_cnt = Counter()               # 被引用的后缀 → 次数
ref_ex = defaultdict(list)        # 后缀 → 示例 (引用方 → 被引用名)
self_cnt = Counter()              # 条目自身的后缀 → 条目数
consume_cnt = Counter()           # 每个条目 data 里的 99 行数

for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = NAME.match(cols[0].strip())
    if m and m.group(2) and m.group(2).isdigit():
        self_cnt[m.group(2)] += 1
    data = cols[2]
    if "99:" not in data:
        continue
    for seg in data.split("$"):
        if not seg.startswith("99:"):
            continue
        consume_cnt[cols[0].strip()] += 1
        r = REF.search(seg)
        if not r:
            continue
        suf = r.group(1)
        ref_cnt[suf] += 1
        if len(ref_ex[suf]) < 4:
            ref_ex[suf].append((cols[0].strip(), seg.rsplit(":", 1)[-1]))

print("=== 99 引用里, 被引用名带数字后缀的次数 (全库) ===")
tot_refs = sum(ref_cnt.values())
print(f"  带数字后缀的引用合计 {tot_refs} 次")
for suf, n in ref_cnt.most_common():
    print(f"  -{suf:<4s} {n:7d}   例: " +
          ", ".join(f"{a}→{b}" for a, b in ref_ex[suf][:3]))

print("\n=== 各后缀: 条目数 vs 被引用次数 ===")
print(f"{'后缀':>5s} {'条目数':>7s} {'被引用':>8s}  比例")
for suf in sorted(set(list(self_cnt) + list(ref_cnt)), key=lambda s: -ref_cnt.get(s, 0))[:16]:
    a, b = self_cnt.get(suf, 0), ref_cnt.get(suf, 0)
    print(f"-{suf:>4s} {a:7d} {b:8d}  {b/a if a else 0:6.2f}")

print(f"\n  含 99 引用的条目数: {len(consume_cnt)}")
