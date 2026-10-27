# -*- coding: utf-8 -*-
"""查 ⿸鹿: 容器 -05 变体展平后"中间消失"，以及各 99 引用能不能解析"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity              # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def walk(name, depth=0, seen=None):
    """逐层列出 99 引用, 标出解析不到的"""
    seen = seen if seen is not None else set()
    if name in seen or depth > 3:
        return
    seen.add(name)
    data = q(glyph_extend.get_data, name)
    pad = "  " * depth
    if not data:
        print(f"{pad}× {name}  ← 库里有这个字形吗: 没有 / 空")
        return
    segs = [s for s in data.split("$") if s]
    print(f"{pad}{name}: {len(segs)} 段")
    for s in segs:
        p = s.split(":")
        if p[0] == "99" and len(p) >= 8:
            tgt = p[7]
            ok = bool(q(glyph_extend.get_data, tgt.split("@")[0]))
            print(f"{pad}  99 → {tgt:22s} {'✓' if ok else '× 解析不到'}")
            walk(tgt.split("@")[0], depth + 1, seen)
        elif p[0] in ("1", "2", "3", "4", "6", "7"):
            print(f"{pad}  笔画 类型{p[0]}")


for nm in ("u9e7f-05", "u9e7f"):
    print(f"===== {nm} =====")
    walk(nm)
    flat = q(glyph_extend.return_bone, nm)
    st = [s for s in flat.split("$") if s]
    print(f"  return_bone 后: {len(st)} 段, 其中笔画 "
          f"{len([s for s in st if s.split(':')[0] in ('1','2','3','4','6','7')])}")
    boxes = q(cavity.ink_boxes, flat)
    print(f"  障碍盒 {len(boxes)} 个")
    for b in boxes:
        print(f"     ({b[0]:6.1f},{b[1]:6.1f}) - ({b[2]:6.1f},{b[3]:6.1f})")
    cands = cavity.rank_faces(q(cavity.faces, flat)[0], "⿸")
    print(f"  ⿸ 候选 {len(cands)} 个")
    for i, f in enumerate(cands):
        print(f"    [{i}] box={tuple(round(v,1) for v in f['box'])} "
              f"ins={tuple(round(v,1) for v in f['ins'])} 开口={''.join(sorted(f['open']))}")
    print()
