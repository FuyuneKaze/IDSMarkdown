# -*- coding: utf-8 -*-
"""
看 GlyphWiki 实际怎么画这些"复合容器"包围字 —— 拆件还是 stretch?
哀(⿴衣口) 衮 衍(⿴行氵) 衙 衡 街 塵(⿸鹿土) 摩(⿸麻手) 氕(⿹气丿) 慮(⿸虍思)
"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend

IDX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _c = _line.split(" | ")
    if len(_c) >= 3:
        IDX[_c[0].strip()] = (_ln, _c[2].strip())


def fast_get(targets, datas=None, **kw):
    best, bd = -1, ""
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            h = IDX.get(targets[i:j])
            if h is not None and h[0] > best:
                best, bd = h[0], h[1]
    return bd


glyph_extend.get_data = fast_get


def refs(data):
    out = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                x1, y1, x2, y2 = int(p[3]), int(p[4]), int(p[5]), int(p[6])
                sx = int(p[1]); sy = int(p[2])
                sx2 = int(p[9]) if len(p) > 9 else 0
                sy2 = int(p[10]) if len(p) > 10 else 0
                out.append((p[7], (x1, y1, x2, y2), (sx, sy, sx2, sy2)))
            except ValueError:
                pass
    return out


def n_strokes(data):
    return sum(1 for s in data.split("$")
               if s.strip().split(":")[0] in ("1", "2", "3", "4", "6", "7"))


def show(name, indent="  ", depth=0, maxd=2, seen=None):
    if seen is None:
        seen = set()
    hit = IDX.get(name)
    if hit is not None:
        d = hit[1]
    else:
        d = fast_get(name)          # 子串 fallback
    if not d:
        print(f"{indent}{name}: 不存在")
        return
    rs = refs(d)
    ns = n_strokes(d)
    tag = f"直绘{ns}笔" if ns else ""
    if not rs:
        print(f"{indent}{name}: {tag}  data={d[:70]}")
        return
    print(f"{indent}{name}: {len(rs)}个引用 {tag}")
    for (rn, rect, st) in rs:
        sxt = ""
        if st != (0, 0, 0, 0):
            sxt = f"  stretch D=({st[0]},{st[1]}) S=({st[2]},{st[3]})"
        print(f"{indent}  → rect={rect}  {rn}{sxt}")
        if depth < maxd and rn not in seen:
            seen.add(rn)
            show(rn, indent + "      ", depth + 1, maxd, seen)


CASES = [
    ("哀", "u54c0"), ("衮", "u886e"), ("衍", "u884d"), ("衙", "u8859"),
    ("衡", "u8861"), ("街", "u8857"), ("塵", "u5875"), ("摩", "u6469"),
    ("氕", "u6c15"), ("慮", "u616e"),
]

for label, name in CASES:
    print("=" * 84)
    print(f"{label}  ({name})")
    print("=" * 84)
    show(name)
    print()

# 看几个候选"部件"是否单独存在
print("=" * 84)
print("相关部件字形是否存在")
print("=" * 84)
for label, nm in [("亠", "u4ea0"), ("彳", "u5f73"), ("亍", "u4e8d"),
                  ("衣", "u8863"), ("𧘇", None), ("鹿", "u9e7f"),
                  ("麻", "u9ebb"), ("广", "u5e7f"), ("林", "u6797"),
                  ("气", "u6c14"), ("虍", "u864d"), ("口", "u53e3")]:
    if nm is None:
        continue
    have = [s for s in ("", "-j", "-01", "-02", "-05", "-10")
            if nm + s in IDX]
    print(f"  {label:<3} {nm:<8} 可用: {' '.join(have) if have else '无'}")
