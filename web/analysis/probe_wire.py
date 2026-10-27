import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import traceback
try:
    import ids_anal
    out = ids_anal.IDS("⿴", ["u56d7", "u4eba"])
    print("OK", len(out))
except Exception:
    traceback.print_exc()
