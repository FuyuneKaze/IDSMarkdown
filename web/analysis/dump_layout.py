import sys, io, json, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend, ids_anal
buf = io.StringIO()
def q(fn, *a):
    with contextlib.redirect_stdout(buf):
        return fn(*a)
out = {}
for nm in ("u9ea6", "u5c06", "u5fc4", "u675f", "u8d1f", "u8fb6", "u9f3b"):
    flat = q(glyph_extend.return_bone, nm)
    st = ids_anal.stroke_list(flat)
    b = q(ids_anal.bbox, flat)
    out[nm] = {"strokes": st, "bbox": [round(float(v),3) for v in b] if b else None}
io.open(r"D:\2026harucpp\web\analysis\layout_cases.json","w",encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
for k,v in out.items():
    print(f"  {k}: {len(v['strokes'])} 笔  bbox {v['bbox']}")
