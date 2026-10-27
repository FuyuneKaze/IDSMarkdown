# -*- coding: utf-8 -*-
"""探 14 个数字后缀在库里的实际分布 + 生僻后缀用在哪

单次扫 dump, 统计每个后缀的条目数/字头数/示例, 并对 -05/-10/-11 做几何对比。
"""
import sys, io, re, contextlib
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend

buf = io.StringIO()
PAT = re.compile(r"^(u[0-9a-f]+)(?:-(.+))?$")
KNOWN = ["01", "02", "03", "04", "05", "06", "07", "08", "09",
         "10", "11", "14", "15", "24"]

cnt = Counter()                 # 后缀 → 条目数
heads = defaultdict(set)        # 后缀 → 字头集合
examples = defaultdict(list)    # 后缀 → 示例名字
suffixes_all = Counter()        # 所有出现过的后缀 (含 -j/-itaiji 等非数字)

for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = PAT.match(cols[0].strip())
    if not m:
        continue
    suf = m.group(2)
    if not suf:
        continue
    suffixes_all[suf] += 1
    if suf in KNOWN:
        cnt[suf] += 1
        heads[suf].add(m.group(1))
        if len(examples[suf]) < 6:
            examples[suf].append(cols[0].strip())

print("=== 14 个数字后缀的条目数 / 涉及字头数 ===")
print(f"{'后缀':>5s} {'条目数':>8s} {'字头数':>8s}  示例")
for s in KNOWN:
    print(f"-{s:>4s} {cnt.get(s,0):8d} {len(heads.get(s,set())):8d}  "
          + ", ".join(examples.get(s, [])[:4]))

print("\n=== 库里所有后缀 (按条目数, 前 18) ===")
for suf, n in suffixes_all.most_common(18):
    print(f"  -{suf:<14s} {n:8d}")

# ---- 几何对比: 同一字头的 -05 / -10 / -11 / -15 外框 ----
import ids_anal


def bbox_of(name):
    with contextlib.redirect_stdout(buf):
        flat = glyph_extend.return_bone(name)
        if not flat:
            return None
        b = ids_anal.bbox(flat)
    return tuple(round(float(v), 1) for v in b) if b else None


print("\n=== 包围外框的几种变体 (同字头) ===")
cand = []
for base in heads.get("05", set()):
    if base in heads.get("10", set()) or base in heads.get("11", set()) or base in heads.get("15", set()):
        cand.append(base)
cand.sort()
print(f"  同时具备 -05 和 (-10/-11/-15) 的字头: {len(cand)} 个, 前 10: {cand[:10]}")
for base in cand[:6]:
    row = []
    for s in ("05", "10", "11", "15"):
        nm = f"{base}-{s}"
        row.append(f"-{s}:{bbox_of(nm)}" if nm in heads.get(s, set()) else f"-{s}:-")
    print(f"  {base:10s} " + "  ".join(row))
