import sys, io, json, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend, ids_anal
buf = io.StringIO()
out = {}
for nm in ("u65e5", "u7530", "u4eba"):
    with contextlib.redirect_stdout(buf):
        flat = glyph_extend.return_bone(nm)
    out[nm] = ids_anal.stroke_list(flat)
io.open(r"D:\2026harucpp\web\analysis\smoke_strokes.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
print({k: len(v) for k, v in out.items()})
