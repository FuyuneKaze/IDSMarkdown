# -*- coding: utf-8 -*-
"""生僻后缀到底被谁引用: 给出 "引用方 → 被引用名" 的真实配对

顺便看每个后缀条目的 data 长什么样 (笔画数 / 引用数)。
"""
import sys, io, re
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend

PAT = re.compile(r"^(u[0-9a-f]+)(?:-(\d+))?$")
KINDS = ("1", "2", "3", "4", "6", "7")
RARE = ("07", "08", "09", "10", "11", "14", "15", "24")

# 第一遍: 收集生僻后缀的条目 (名字 → data)
rare = defaultdict(dict)
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = PAT.match(cols[0].strip())
    if not m or m.group(2) not in RARE:
        continue
    rare[m.group(2)][cols[0].strip()] = cols[2].strip()

all_rare = {}
for suf, d in rare.items():
    for nm, data in d.items():
        all_rare[nm] = (suf, data)

# 第二遍: 谁引用了它们
refs = defaultdict(list)
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3 or "99:" not in cols[2]:
        continue
    who = cols[0].strip()
    for seg in cols[2].split("$"):
        if not seg.startswith("99:"):
            continue
        tgt = seg.rsplit(":", 1)[-1].split("@")[0]
        if tgt in all_rare:
            refs[tgt].append(who)

print("=== 生僻后缀: 条目形态 + 谁在引用它 ===")
for suf in RARE:
    items = rare.get(suf, {})
    if not items:
        print(f"\n-{suf}: 无")
        continue
    # 挑"被引用最多"的两个例子
    ranked = sorted(items, key=lambda nm: -len(refs.get(nm, [])))
    print(f"\n-{suf}  共 {len(items)} 条, 被引用总数 "
          f"{sum(len(refs.get(nm, [])) for nm in items)}")
    for nm in ranked[:3]:
        data = items[nm]
        ns = sum(1 for s in data.split("$") if s.split(":")[0] in KINDS)
        nr = sum(1 for s in data.split("$") if s.split(":")[0] == "99")
        who = refs.get(nm, [])
        print(f"   {nm:14s} 笔画{ns:2d} 引用{nr:2d}  被引 {len(who):4d} 次  "
              f"例: {', '.join(who[:4]) if who else '(无)'}")
        print(f"        data: {data[:100]}")
