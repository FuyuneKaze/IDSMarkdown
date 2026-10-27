# -*- coding: utf-8 -*-
"""验证 ids_anal 新增的 case "⿸" """
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import ids_anal
from kage_contour import extract_one

CASES = [
    ("府", "u5e7f", "u4ed8"),   # ⿸广付
    ("病", "u7592", "u4e19"),   # ⿸疒丙
    ("房", "u6236", "u65b9"),   # ⿸户方
    ("厄", "u5382", "u353e"),   # ⿸厂㔾
]

for label, cbase, ibase in CASES:
    print("=" * 70)
    print(f"{label}   ⿸{cbase} {ibase}")
    print("=" * 70)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            g = ids_anal.IDS("⿸", [cbase, ibase])
    except Exception as e:
        print(f"  异常: {type(e).__name__}: {e}")
        print("  IDS() 输出尾部:")
        for ln in buf.getvalue().splitlines()[-6:]:
            print("    " + ln)
        continue
    print("  IDS() 输出:")
    for ln in buf.getvalue().splitlines():
        print("    " + ln)
    if not g:
        print("  → 返回空")
        continue
    print(f"  → {len(g)} 字符, {len(g.split('$'))} 段")
    try:
        r = extract_one("_t", g)
        cs = r.get("contours", [])
        print(f"  → 轮廓 {len(cs)} 个, 点 {sum(len(c) for c in cs)}")
        if r.get("error"):
            print(f"  轮廓错误: {r['error']}")
        else:
            pts = [p for c in cs for p in c]
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            print(f"  → 墨迹范围 x[{min(xs):.0f},{max(xs):.0f}] "
                  f"y[{min(ys):.0f},{max(ys):.0f}]")
    except Exception as e:
        print(f"  轮廓提取异常: {type(e).__name__}: {e}")
    print()
