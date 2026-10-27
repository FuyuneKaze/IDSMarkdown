# -*- coding: utf-8 -*-
"""生僻后缀实际能用在哪: -10/-11/-15 (密度外框) 与 -14/-24 (下半边) 的覆盖情况"""
import sys, io, re, os, contextlib
from collections import defaultdict, Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend, stroke_outer

buf = io.StringIO()
PAT = re.compile(r"^(u[0-9a-f]+)(?:-(.+))?$")
RARE = {"05", "10", "11", "15", "14", "24", "08", "09", "04", "06"}

have = {}                        # 后缀 → {字头: data}
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = PAT.match(cols[0].strip())
    if m and m.group(2) in RARE:
        have.setdefault(m.group(2), {})[m.group(1)] = cols[2].strip()

print("=== 各后缀覆盖的字头数 ===")
for s in ("04", "05", "06", "08", "09", "10", "11", "14", "15", "24"):
    print(f"  -{s}: {len(have.get(s, {})):5d} 个")

# ---- 真实用例: 库里所有包围结构, 容器是否另有密度变体 ----
def union(boxes):
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def direct_bbox(data):
    boxes = []
    for s in data.split("$"):
        if s.split(":")[0] in ("1", "2", "3", "4", "6", "7"):
            with contextlib.redirect_stdout(buf):
                b = stroke_outer.strokic_boundary(s, False)
            if b.x2 > b.x1 and b.y2 > b.y1:
                boxes.append((b.x1, b.y1, b.x2, b.y2))
    return union(boxes)


PUB = r"D:\2026harucpp\web\public"
SUR = set("⿴⿵⿶⿷⿸⿹⿺⿼⿽")
OPCH = "".join(SUR)


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


tot = alt10 = alt11 = alt15 = 0
ex = []
for f in ("ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"):
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        char, _, body = line.rstrip("\n").partition("\t")
        char = char.strip()
        if not char:
            continue
        for raw in body.split(";"):
            clean = strip_notation(raw)
            if not clean or clean[0] not in SUR:
                continue
            m = re.match(r"^([%s])(\[(\d+)\])?\s*" % OPCH, clean)
            if not m:
                continue
            rest = clean[m.end():]
            a = first_char(rest)
            if not a:
                continue
            base = "u%x" % ord(a)
            tot += 1
            got = []
            if base in have.get("10", {}):
                alt10 += 1
                got.append("10")
            if base in have.get("11", {}):
                alt11 += 1
                got.append("11")
            if base in have.get("15", {}):
                alt15 += 1
                got.append("15")
            if got and len(ex) < 8:
                ex.append((char, m.group(1), a, base, got))

print(f"\n=== 库里 {tot} 个包围结构用例中, 容器另有密度变体的 ===")
print(f"  有 -10 (内容密): {alt10}   有 -11 (内容疏): {alt11}   有 -15 (少见): {alt15}")
for char, op, a, base, got in ex:
    print(f"  {char} = {op}{a}…   容器 {base} 另有 -{'/-'.join(got)}")

# ---- 几何: 同字头的 -05 vs -10 vs -11 ----
print("\n=== 同一字头的 -05 / -10 / -11 直接笔画外框 ===")
shown = 0
for base, d05 in have.get("05", {}).items():
    others = [s for s in ("10", "11") if base in have.get(s, {})]
    if not others:
        continue
    b05 = direct_bbox(d05)
    if not b05:
        continue
    print(f"  {base}  -05 盒{tuple(round(v,1) for v in b05)}  "
          f"笔画{sum(1 for s in d05.split('$') if s.split(':')[0] in ('1','2','3','4','6','7'))} "
          f"引用{sum(1 for s in d05.split('$') if s.split(':')[0]=='99')}")
    for s in others:
        b = direct_bbox(have[s][base])
        print(f"        -{s} 盒{tuple(round(v,1) for v in b) if b else None}  "
              f"笔画{sum(1 for x in have[s][base].split('$') if x.split(':')[0] in ('1','2','3','4','6','7'))} "
              f"引用{sum(1 for x in have[s][base].split('$') if x.split(':')[0]=='99')}  "
              f"前80字: {have[s][base][:80]}")
    shown += 1
    if shown >= 4:
        break
