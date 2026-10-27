# -*- coding: utf-8 -*-
"""关键问题: 我们自己生成的引用名 (-01..-06) 在库里是否存在?

结论导向: 只有**我们生成名字**的那几处 (⿰/-01/-02, ⿱/-03/-04, 包围/-05/-06) 会受后缀
策略影响; 其它后缀 (-08/-09/-10/-11/-14/-15/-24) 是由**库里的数据自己引用**的,
我们按名精确解析就已经用上了。所以只需要关心: 硬编码的 -05/-04 会不会落空。
"""
import sys, io, re, os
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend

PAT = re.compile(r"^(u[0-9a-f]+)(?:-(.+))?$")
have = defaultdict(dict)          # 后缀 → {字头: data}
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    m = PAT.match(cols[0].strip())
    if not m:
        continue
    suf = m.group(2)
    if suf and (suf.isdigit() or suf in ("j", "jn")):
        have[suf][m.group(1)] = cols[2].strip()

PUB = r"D:\2026harucpp\web\public"
SUR = set("⿴⿵⿶⿷⿸⿹⿺⿼⿽")


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
    """拆成前两个子节点 (括号嵌套感知)"""
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


buckets = defaultdict(int)
ex = defaultdict(list)
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
            if not clean:
                continue
            # 包围
            if clean[0] in SUR:
                m = re.match(r"^(.)(\[\d+\])?\s*", clean)
                rest = clean[m.end():] if m else ""
                kids = split2(rest)
                a = first_char(kids[0]) if kids else first_char(rest)
                if not a:
                    continue
                base = "u%x" % ord(a)
                has05 = base in have["05"]
                hasden = any(base in have[s] for s in ("10", "11", "15"))
                k = ("包围", has05, hasden)
                buckets[k] += 1
                if not has05 and hasden and len(ex[k]) < 5:
                    ex[k].append(f"{char} = {clean[:6]}… 容器 {base} " +
                                 "有" + "/".join(s for s in ("10", "11", "15") if base in have[s]))
            # 上下 (看下半边 -04 vs -14/-24)
            if clean[0] in "⿱⿳":
                m = re.match(r"^(.)(\[\d+\])?\s*", clean)
                rest = clean[m.end():] if m else ""
                kids = split2(rest)
                if len(kids) < 2:
                    continue
                b = first_char(kids[-1])
                if not b:
                    continue
                base = "u%x" % ord(b)
                has04 = base in have["04"]
                hasalt = any(base in have[s] for s in ("14", "24"))
                k = ("上下", has04, hasalt)
                buckets[k] += 1
                if not has04 and hasalt and len(ex[k]) < 5:
                    ex[k].append(f"{char} = {clean[:6]}… 下半边 {base} " +
                                 "有" + "/".join(s for s in ("14", "24") if base in have[s]))

for kind in ("包围", "上下"):
    tot = sum(v for (kd, a, b), v in buckets.items() if kd == kind)
    ok = sum(v for (kd, a, b), v in buckets.items() if kd == kind and a)
    miss_alt = sum(v for (kd, a, b), v in buckets.items() if kd == kind and not a and b)
    miss_no = sum(v for (kd, a, b), v in buckets.items() if kd == kind and not a and not b)
    print(f"=== {kind} 用例 {tot} 个 ===")
    print(f"  硬编码后缀存在      : {ok:6d}  ({ok/tot*100:.1f}%)")
    print(f"  不存在, 但有生僻变体: {miss_alt:6d}  ({miss_alt/tot*100:.1f}%)  ← 可以用变体补")
    print(f"  不存在, 也没有变体  : {miss_no:6d}  ({miss_no/tot*100:.1f}%)  ← 只能退化到本体")
    for (kd, a, b), lst in sorted(ex.items()):
        if kd == kind:
            for s in lst:
                print(f"    例: {s}")
    print()

print("=== 各后缀库里存在的字头数 ===")
for s in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "14", "15", "24"):
    print(f"  -{s}: {len(have[s]):5d}", end="   ")
print()
