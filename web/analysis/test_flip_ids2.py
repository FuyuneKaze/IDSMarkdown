import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
for op, arg in [("⿾", "u6b62"), ("⿿", "u4e88"), ("⿾", "u6728")]:
    with contextlib.redirect_stdout(buf):
        out = ids_anal.IDS(op, [arg])
    segs = (out or "").split("$")
    print(f"  {op}{arg}: {len(segs)} 段, 末段 = {segs[-1] if segs else '(空)'}")
from kage_contour import extract_contours
with contextlib.redirect_stdout(buf):
    out = ids_anal.IDS("⿿", ["u4e88"])
    r = extract_contours(out)
print(f"  预览轮廓: {len(r.get('contours') or [])} 个, error={r.get('error')}")

