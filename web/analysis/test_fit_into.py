# -*- coding: utf-8 -*-
"""验证新的 fit_into (按轴选基准) 效果"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import ids_anal as A


def strokes(g):
    return [s.strip() for s in g.split("$")
            if s.strip().split(":")[0] in ("1", "2", "3", "4", "6", "7")]


def ink(g):
    xs, ys = [], []
    for s in strokes(g):
        p = s.split(":")
        xs += [float(v) for v in p[3::2]]
        ys += [float(v) for v in p[4::2]]
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def mapped(inkb, target):
    x1, y1, x2, y2 = [float(v) for v in target]
    W, H = x2 - x1, y2 - y1
    mx = lambda x: x1 + (x / 200.0) * W
    my = lambda y: y1 + (y / 200.0) * H
    return (mx(inkb[0]), my(inkb[1]), mx(inkb[2]), my(inkb[3]))


def run(label, cbase, ibase, real=None):
    cjk1 = A.glyph_extend.return_bone(cbase + "-05")
    cjk2 = A.glyph_extend.return_bone(ibase + "-06")
    if not cjk1 or not cjk2:
        print(f"  {label}: return_bone 空 (cjk1={bool(cjk1)} cjk2={bool(cjk2)})")
        return
    cav, outer = A.enclosure_cavity(cjk1)
    ibb = A.union_boxes(A.glyph_boxes(cjk2))
    if not cav or not ibb:
        print(f"  {label}: 无空腔/无盒")
        return
    t = A.fit_into(ibb, cav)
    im = ink(cjk2)
    m = mapped(im, t)
    tf = [float(v) for v in t]
    print(f"\n  {label}   容器={cbase}-05  内部={ibase}-06")
    print(f"    空腔     {cav[2]-cav[0]:5.0f} x {cav[3]-cav[1]:5.0f}"
          f"   [{cav[0]:.0f},{cav[1]:.0f},{cav[2]:.0f},{cav[3]:.0f}]")
    print(f"    内部件盒 [{ibb[0]:6.1f},{ibb[1]:6.1f},{ibb[2]:6.1f},{ibb[3]:6.1f}]"
          f"  → trans 目标 [{tf[0]:.1f},{tf[1]:.1f},{tf[2]:.1f},{tf[3]:.1f}]")
    print(f"    映射后墨迹 {m[2]-m[0]:5.0f} x {m[3]-m[1]:5.0f}"
          f"   [{m[0]:.0f},{m[1]:.0f},{m[2]:.0f},{m[3]:.0f}]")
    if real:
        print(f"    设计者真实 {real[2]-real[0]:5.0f} x {real[3]-real[1]:5.0f}"
              f"   {real}")
    # 墨迹是否落在空腔内
    inside = (m[0] >= cav[0] - 1 and m[1] >= cav[1] - 1 and
              m[2] <= cav[2] + 1 and m[3] <= cav[3] + 1)
    print(f"    墨迹在空腔内: {'是' if inside else '否(溢出)'}")


print("=" * 82)
print("新 fit_into: 按轴选基准 (部件包围盒普遍不满幅 → 实际走 0-200 基准)")
print("=" * 82)
run("府 ⿸广付", "u5e7f", "u4ed8", (43.5, 46.3, 187.4, 185.7))
run("病 ⿸疒丙", "u7592", "u4e19", (60.2, 67.8, 181.8, 183.4))
run("問 ⿵門口", "u9580", "u53e3", (70.8, 107.9, 131.2, 152.1))
run("囚 ⿴囗人", "u56d7", "u4eba", (45.4, 43.3, 152.0, 158.8))
run("点 ⿸广丶", "u5e7f", "u4e36", None)

print()
print("=" * 82)
print("端到端: IDS() 调用是否正常")
print("=" * 82)
for label, op, args in [("府", "⿸", ["u5e7f", "u4ed8"]),
                        ("病", "⿸", ["u7592", "u4e19"]),
                        ("点", "⿸", ["u5e7f", "u4e36"]),
                        ("囗人(⿸假)", "⿸", ["u56d7", "u4eba"])]:
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            g = A.IDS(op, args)
        segs = len(g.split("$")) if g else 0
        print(f"  {label:<10} {op}{args}  →  {len(g) if g else 0} 字符, {segs} 段")
    except Exception as e:
        print(f"  {label:<10} 异常 {type(e).__name__}: {e}")
