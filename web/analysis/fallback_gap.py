# -*- coding: utf-8 -*-
"""
fallback 缺口统计: 被当作包围外框的字里, 有多少存在 -05 变体?

-05 是 positionChain 里包围外框的首选。若不存在, 现在会 fallback 到更后面的后缀
(10/11/15) 或最终落到本体 —— 而本体往往没有预制开口。
"""
import sys, io, os
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())

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


def flat(n):
    if n is None:
        return ""
    if n[0] == "leaf":
        return n[1]
    return n[0] + "".join(flat(k) for k in n[1])


outer_use = Counter()
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
                node, _ = parse(ids)
                if not node or node[0] not in SURROUND:
                    continue
                if len(node[1]) != 2:
                    continue
                o = flat(node[1][0])
                if len(o) == 1:
                    outer_use[o] += 1

print(f"被用作包围外框的不同字: {len(outer_use)}")
print(f"总使用次数: {sum(outer_use.values())}\n")

SUF = ["-05", "-10", "-11", "-15", "-06", "-j", "-02", "-01"]
stat = Counter()
no_any = []
detail = []

for ch, cnt in outer_use.items():
    base = f"u{ord(ch):x}"
    have = [s for s in SUF if base + s in IDX]
    if not have:
        no_any.append((ch, cnt))
        stat["连本体都没有"] += cnt
        continue
    if "-05" in have:
        stat["有 -05 (首选可用)"] += cnt
    elif any(s in have for s in ("-10", "-11", "-15")):
        stat["无-05 但有 -10/-11/-15"] += cnt
    else:
        stat["无-05, 只有 -j/-01/-02/本体"] += cnt
    detail.append((ch, cnt, have))

tot = sum(outer_use.values())
print("=" * 76)
print("按使用次数统计 (fallback 落到哪一档)")
print("=" * 76)
for k in ["有 -05 (首选可用)", "无-05 但有 -10/-11/-15", "无-05, 只有 -j/-01/-02/本体", "连本体都没有"]:
    v = stat.get(k, 0)
    print(f"  {k:<28} {v:>7}  ({v/max(tot,1)*100:5.1f}%)")

print()
print("=" * 76)
print("使用次数最多的外框, 及其可用后缀 (前 30)")
print("=" * 76)
detail.sort(key=lambda x: -x[1])
print(f"  {'字':<4} {'用次':>6}  可用后缀")
for ch, cnt, have in detail[:30]:
    flag = "" if "-05" in have else "   ← 无 -05"
    print(f"  {ch:<4} {cnt:>6}  {' '.join(have)}{flag}")

print()
print("=" * 76)
print("无 -05 且用次高的外框 (最需要 fallback 策略的)")
print("=" * 76)
n5 = [(ch, cnt, have) for ch, cnt, have in detail if "-05" not in have]
n5.sort(key=lambda x: -x[1])
for ch, cnt, have in n5[:25]:
    print(f"  {ch:<4} {cnt:>6}  {' '.join(have)}")

if no_any:
    print(f"\n连本体都不在 KAGE 库里的外框 ({len(no_any)} 个):")
    for ch, cnt in sorted(no_any, key=lambda x: -x[1])[:15]:
        print(f"  {ch} ({cnt}次)")
