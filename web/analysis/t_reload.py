import sys, io, os, time, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview
try:
    preview._reload_changed()
    print("first _reload_changed(): OK")
    preview._reload_changed()
    print("second _reload_changed(): OK")
    p = os.path.join(r"D:\2026harucpp\scripts", "stroke_outer.py")
    print("tracked:", {os.path.basename(k): v for k, v in preview._MTIME.items()})
except Exception:
    traceback.print_exc()
