import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend
buf = io.StringIO()
for ch in "龜𢧟𥣨𦥮𪚦𫡆":
    name = "u%x" % ord(ch)
    with contextlib.redirect_stdout(buf):
        d = glyph_extend.get_data(name)
    print(f"  {ch}  U+{ord(ch):05X}  {name:9s} {'有' if d else '× 库里没有'}  {d[:60]}")
