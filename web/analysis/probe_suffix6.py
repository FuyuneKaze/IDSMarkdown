# -*- coding: utf-8 -*-
"""生僻后缀的真实用例: 哪个字、在哪个位置、引用了哪个变体

两遍扫 dump:
  ① 收生僻后缀的条目 (名字 → data)
  ② 找"引用者里名字是 uXXXX 的" (= 真实字符), 记下它引用了谁
再用 ids_lv*.txt 的 IDS 标记解释位置, 并用 99 行的矩形判断上/下/左/右/全。
最后统计 -14 的"上面有哪些部件"。
"""
import sys, io, re, os
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend

KINDS = ("1", "2", "3", "4", "6", "7")
RARE = ("07", "08", "09", "10", "11", "14", "15", "24")
NAME = re.compile(r"^(u[0-9a-f]+)(?:-(\d+))?$")

# ---------- ① 收生僻条目 ----------
rare = defaultdict(dict)
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = NAME.match(cols[0].strip())
    if m and m.group(2) in RARE:
        rare[m.group(2)][cols[0].strip()] = cols[2].strip()
rare_name = {}
for suf, d in rare.items():
    for nm in d:
        rare_name[nm] = suf

# ---------- ② 真实字符引用了谁 (带位置) ----------
CHARNAME = re.compile(r"^u[0-9a-f]{4,6}$")
hits = defaultdict(list)          # 后缀 → [(字符名, 名字, 位置)]
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3 or "99:" not in cols[2]:
        continue
    who = cols[0].strip()
    if not CHARNAME.match(who):
        continue
    for seg in cols[2].split("$"):
        if not seg.startswith("99:"):
            continue
        p = seg.split(":")
        if len(p) < 8:
            continue
        tgt = p[7].split("@")[0]
        if tgt not in rare_name:
            continue
        nx, ny = int(p[1]), int(p[2])
        rect = [int(float(v)) for v in p[3:7]]
        x1, y1, x2, y2 = rect
        pos = "全幅" if (x1 <= 5 and x2 >= 195 and y1 <= 5 and y2 >= 195) else \
              "右" if x1 >= 95 else "左" if x2 <= 105 else \
              "下" if y1 >= 95 else "上" if y2 <= 105 else "中"
        hits[rare_name[tgt]].append((who, tgt, pos))

# ---------- IDS 标记 (用来解释"上面是什么") ----------
PUB = r"D:\2026harucpp\web\public"


def strip_notation(body):
    body = body.split("\t")[0]
    body = re.sub(r"#\([^)]*\)|\{[^}]*\}|\([^)]*\)", "", body)
    return body.replace(".", "").strip()


def first_char(node):
    for ch in node:
        if 0x2FF0 <= ord(ch) <= 0x2FFF or ord(ch) == 0x31EF or ch in ".[]0123456789:-,":
            continue
        return ch
    return ""


def split2(rest):
    out, depth, cur = [], 0, ""
    for ch in rest:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        cur += ch
        if depth == 0:
            out.append(cur)
            cur = ""
    return [x for x in out if x]


ids = {}
for f in ("ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"):
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        char, _, body = line.rstrip("\n").partition("\t")
        char = char.strip()
        if not char or char in ids:
            continue
        for raw in body.split(";"):
            c = strip_notation(raw)
            if c:
                ids[char] = c
                break

print("=== 生僻后缀的真实字符用例 (字 / IDS / 位置 → 引用的变体) ===")
for suf in RARE:
    lst = hits.get(suf, [])
    print(f"\n-{suf}   被真实字符引用 {len(lst)} 处, 涉及 {len({h[0] for h in lst})} 个字")
    seen = set()
    shown = 0
    for who, tgt, pos in lst:
        ch = chr(int(who[1:], 16))
        if ch in seen:
            continue
        seen.add(ch)
        notation = ids.get(ch, "?")
        print(f"   {ch} U+{int(who[1:],16):04X}  {notation[:14]:16s} {pos:>3s} → {tgt}")
        shown += 1
        if shown >= 6:
            break

# ---------- -14 的"上面有哪些部件" ----------
print("\n=== -14 的上面部件统计 (从 ⿱ 型 IDS 取上半边) ===")
tops = Counter()
for who, tgt, pos in hits.get("14", []):
    ch = chr(int(who[1:], 16))
    notation = ids.get(ch, "")
    if not notation or notation[0] not in "⿱⿳":
        continue
    kids = split2(notation[1:])
    if len(kids) >= 2:
        top = first_char(kids[0])
        if top:
            tops[top] += 1
print(f"  能确定上半边的 {sum(tops.values())} 例, 共 {len(tops)} 种上半边部件")
for t, n in tops.most_common(20):
    print(f"    {t}  ×{n}", end="")
print()
