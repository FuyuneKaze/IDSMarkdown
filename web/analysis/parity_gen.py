# -*- coding: utf-8 -*-
"""生成 TS↔Python 对拍用例: 同一份笔画输入, 记录 Python 侧的 surround 全部中间量

只做"算法对拍", 不涉及名字解析 —— 笔画串直接写进 JSON, TS 侧用同一份输入。
"""
import sys, io, json, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal, cavity, central_box  # noqa: E402
import stroke_outer                                 # noqa: E402

buf = io.StringIO()


def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)


def union(boxes):
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


CASES = [
    ("⿴", "u56d7", "u4eba"), ("⿴", "u53e3", "u4e42"), ("⿴", "u65e5", "u4e00"),
    ("⿴", "u7530", "u4e42"), ("⿴", "u9b3c", "u53e3"), ("⿴", "u8001", "u53e3"),
    ("⿵", "u5182", "u4eba"), ("⿶", "u51f5", "u4eba"), ("⿷", "u533a", "u4eba"),
    ("⿸", "u5382", "u4eba"), ("⿸", "u5382", "u4e36"), ("⿸", "u7592", "u7ca4"),
    ("⿸", "u9e7f", "u4e36"), ("⿹", "u5f13", "u4eba"), ("⿺", "u8fb6", "u4eba"),
    ("⿺", "u8fb6", "u5bf8"), ("⿼", "u53c9", "u4e36"), ("⿽", "u5341", "u4e36"),
    ("⿴", "u56d7", "u4e36"), ("⿴", "u56d7", "u4e00"), ("⿴", "u56d7", "u4e28"),
]

out = []
for op, c, i in CASES:
    cname, iname = c + "-05", i + "-06"
    cjk1 = q(glyph_extend.return_bone, cname)
    cjk2 = q(glyph_extend.return_bone, iname)
    if not cjk1 or not cjk2:
        continue
    cst = ids_anal.stroke_list(cjk1)
    ist = ids_anal.stroke_list(cjk2)

    # ---- Python 侧 surround 的实际算法 ----
    pts2 = [q(stroke_outer.stroke_point, s) for s in ist]
    ibb1 = union([b for b in (q(ids_anal.strokic_box, s, True, p)
                             for s, p in zip(ist, pts2)) if b])
    cb_raw, cb_ctr = q(central_box.return_segement, None, 15, 1, True,
                       [p[0] for p in pts2])
    ibb2 = ids_anal.box_map(list(cb_raw),
                            [(cb_raw[0] + cb_raw[2]) / 2, (cb_raw[1] + cb_raw[3]) / 2], 2)
    alpha = ids_anal.stronummap(2 * len(ist) - 2)
    basis = ids_anal.list_Int(ibb1, ibb2, alpha)

    faces, outer = q(cavity.faces, cjk1, 0.75, 5.0, True)
    cands = q(cavity.rank_faces, faces, op)
    candidates = [[float(v) for v in f["box"]] for f in cands]
    cav = None
    if cands:
        best = max(cands, key=lambda f: (f["ins"][2] - f["ins"][0]) * (f["ins"][3] - f["ins"][1]))
        cav = [float(v) for v in best["ins"]]
    if cav is None and faces:
        big = max(faces, key=lambda f: f["area"])
        cav = [float(v) for v in (cavity.inscribed(big["rects"]) or big["box"])]
    if cav is None:
        e, _o = q(ids_anal.enclosure_cavity, cjk1)
        cav = [float(v) for v in e] if e else None

    target = None
    if cav and basis:
        t = q(ids_anal.fit_into, basis, cav, 10, 190.0, True)
        target = [float(v) for v in t] if t else None

    out.append({
        "op": op, "cname": cname, "iname": iname,
        "cstrokes": cst, "istrokes": ist,
        "outer": [float(v) for v in outer] if outer else None,
        "candidates": candidates,
        "cavity": cav,
        "ibb1": [float(v) for v in ibb1] if ibb1 else None,
        "cb_raw": [float(v) for v in cb_raw] if cb_raw else None,
        "cb_center": [float(v) for v in cb_ctr] if cb_ctr else None,
        "ibb2": [float(v) for v in ibb2] if ibb2 else None,
        "basis": [float(v) for v in basis] if basis else None,
        "alpha": alpha,
        "target": target,
    })

p = r"D:\2026harucpp\web\analysis\parity_cases.json"
io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print(f"写出 {len(out)} 个用例 → {p}")
for r in out[:3]:
    print("  ", r["op"], r["cname"], "cav", r["cavity"], "target", r["target"])

