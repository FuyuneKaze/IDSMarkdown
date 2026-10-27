# -*- coding: utf-8 -*-
"""逐笔盒对照的数据源: 记录 Python 侧每种模式下每笔的盒, 供 TS 对比"""
import sys, io, json, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity              # noqa: E402
import stroke_outer                                # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


out = {}
for nm in ("u4eba-06", "u9b3c-05"):
    flat = q(glyph_extend.return_bone, nm)
    st = ids_anal.stroke_list(flat)
    rows = []
    for s in st:
        rec = {"stro": s, "n_verts": len(q(stroke_outer.stroke_point, s)[0])}
        for tag, split, shr in (("split_0", True, False), ("split_1", True, True),
                                ("single_0", False, False), ("single_1", False, True)):
            if split:
                bs = q(cavity.part_boxes, s, shrink=shr, split=True)
            else:
                with contextlib.redirect_stdout(buf):
                    b = stroke_outer.strokic_boundary(s, shr)
                bs = [(b.x1, b.y1, b.x2, b.y2)] if b.x2 > b.x1 and b.y2 > b.y1 else []
            rec[tag] = [[round(float(v), 3) for v in bb] for bb in bs]
        rows.append(rec)
    out[nm] = {"strokes": st, "rows": rows}

p = r"D:\2026harucpp\web\analysis\boxes_py.json"
io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("写出", p)
r = out["u4eba-06"]["rows"][0]
print("例: 人 第一笔 n_verts =", r["n_verts"])
for tag in ("split_0", "split_1", "single_0", "single_1"):
    print("   ", tag, r[tag])
r = out["u9b3c-05"]["rows"][3]
print("例: 鬼 第四笔 n_verts =", r["n_verts"], r["stro"][:44])
for tag in ("split_0", "split_1", "single_0", "single_1"):
    print("   ", tag, r[tag])
