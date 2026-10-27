import sys, io, contextlib, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
try:
    with contextlib.redirect_stdout(buf):
        ids_anal.IDS("⿴", ["u56d7", "u4eba"])
except Exception:
    traceback.print_exc()
