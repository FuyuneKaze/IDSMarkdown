import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    for nm in ("u9e7f-05", "u2ff1-cdp-88b4-u6bd4", "u9e7f"):
        d = glyph_extend.get_data(nm)
        print(f"--- {nm} ---")
        for seg in d.split("$"):
            p = seg.split(":")
            if p[0] == "99" and len(p) >= 8:
                print(f"   99 rect={p[3:7]} → {p[7]}   拉伸列={p[9:11] if len(p) >= 11 else '(无)'}")
            elif p[0] in ("1","2","3","4","6","7"):
                print(f"   笔{p[0]}  {p[3:]}")
print(buf.getvalue())
