# -*- coding: utf-8 -*-
"""Python 侧 ⿰/⿲ 的真实分解: 用了哪些字形名、每个子件被映射到哪个矩形

做法: 临时包一层 glyph_extend.trans / return_bone, 记录实际参数, 再跑 IDS。
"""
import sys, io, json, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import glyph_extend, ids_anal                      # noqa: E402

buf = io.StringIO()
real_trans = glyph_extend.trans
real_bone = glyph_extend.return_bone
log = {"names": [], "rects": []}


def spy_trans(glyph, geom, tran=(None, None)):
    t = geom[0]
    log["rects"].append([float(v) for v in t])
    return real_trans(glyph, geom, tran)


def spy_bone(*a, **kw):
    log["names"].append(a[0])
    with contextlib.redirect_stdout(buf):
        return real_bone(*a, **kw)


glyph_extend.trans = spy_trans
glyph_extend.return_bone = spy_bone
ids_anal.glyph_extend.trans = spy_trans
ids_anal.glyph_extend.return_bone = spy_bone

CASES = [("⿰", ["u9ea6", "u5c06"]), ("⿲", ["u5fc4", "u675f", "u8d1f"]),
         ("⿱", ["u4e00", "u4e28"])]
out = []
for op, args in CASES:
    log["names"].clear()
    log["rects"].clear()
    try:
        with contextlib.redirect_stdout(buf):
            ids_anal.IDS(op, args)
    except Exception as e:
        print(f"  {op}{args} 抛错: {type(e).__name__}: {e}")
        continue
    rec = {"op": op, "args": args,
           "names": list(log["names"]),
           "rects": [r for r in log["rects"]]}
    out.append(rec)
    print(f"  {op}{''.join(args)}: 取的名字 {rec['names']}")
    for r in rec["rects"]:
        print("      矩形", [round(v, 2) for v in r])

io.open(r"D:\2026harucpp\web\analysis\layout_py.json", "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
print("写出 layout_py.json")
