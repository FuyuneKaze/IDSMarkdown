# -*- coding: utf-8 -*-
"""
查: return_bone(base+"-06") 的退化到底落到哪个字形?

get_data 是"name in targets"的子串匹配, 取文件里最后一个命中的。
所以查询 "u4eba-06" 时, 候选子串有 u4eba-06 / u4eba-0 / u4eba / u4eb / u4e / u4 / u /
4eba-06 ... 谁在文件里最后出现, 就返回谁的数据。
"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

# ---- 精确名字索引 (只看名字与行号) ----
IDX = {}
for ln, line in enumerate(glyph_extend.dbs):
    p = line.find(" | ")
    if p > 0:
        IDX[line[:p].strip()] = ln
print(f"字形名 {len(IDX):,} 个\n")


def resolve(targets):
    """复刻 get_data: 枚举所有子串, 取行号最大的命中"""
    best, bd = -1, None
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            sub = targets[i:j]
            h = IDX.get(sub)
            if h is not None and h > best:
                best, bd = h, sub
    return bd


def flatten(name):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return glyph_extend.return_bone(name)


BASES = [("人", "u4eba"), ("口", "u53e3"), ("丙", "u4e19"),
         ("付", "u4ed8"), ("日", "u65e5"), ("乃", "u4e43"),
         ("丶", "u4e36"), ("木", "u6728")]

print("=" * 84)
print("① 各后缀是否存在 + 查询 '-06' 时 get_data 实际命中谁")
print("=" * 84)
print(f"  {'部件':<4} {'-06存在':>8} {'-j存在':>8} {'本体存在':>9}   "
      f"{'查 -06 命中':<14} {'查 -j 命中':<14}")
print("  " + "-" * 80)
for ch, base in BASES:
    e06 = (base + "-06") in IDX
    ej = (base + "-j") in IDX
    eb = base in IDX
    r06 = resolve(base + "-06")
    rj = resolve(base + "-j")
    print(f"  {ch:<4} {str(e06):>8} {str(ej):>8} {str(eb):>9}   "
          f"{str(r06):<14} {str(rj):<14}")

print()
print("=" * 84)
print("② 查 '-06' 命中的字形 vs 查本体命中的字形, 是否同一个")
print("=" * 84)
for ch, base in BASES:
    r06 = resolve(base + "-06")
    rb = resolve(base)
    same = "同一" if r06 == rb else "不同!"
    print(f"  {ch:<4}  -06→{str(r06):<14}  本体→{str(rb):<14}  {same}")

print()
print("=" * 84)
print("③ 各查询方式得到的笔画盒对比 (暴露差异)")
print("=" * 84)
import stroke_outer as SO


def boxes(g):
    out = []
    for s in g.split("$"):
        s = s.strip()
        if s and s.split(":")[0] in ("1", "2", "3", "4", "6", "7"):
            try:
                b = SO.strokic_boundary(s)
                if b.x2 > b.x1 and b.y2 > b.y1:
                    out.append((b.x1, b.y1, b.x2, b.y2))
            except Exception:
                pass
    return out


def union(bs):
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs)) if bs else None


for ch, base in BASES:
    print(f"\n  {ch} ({base})")
    for tag in ["-06", "-j", ""]:
        g = flatten(base + tag)
        bs = boxes(g)
        u = union(bs)
        if u:
            print(f"    base{tag:<5} 笔画{len(bs):>3}  盒 "
                  f"[{u[0]:6.1f},{u[1]:6.1f},{u[2]:6.1f},{u[3]:6.1f}]")
        else:
            print(f"    base{tag:<5} 无笔画 (len={len(g)})")
