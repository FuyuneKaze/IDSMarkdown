import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import central_box as cb
from glyph_extend import return_bone
from stroke_outer import strokic_boundary
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    bones = return_bone("u53e3")
boxes = []
for s in bones.split("$"):
    s = s.strip()
    if not s or s.split(":")[0] not in cb.STROKE_KINDS:
        continue
    with contextlib.redirect_stdout(buf):
        b = strokic_boundary(s, False)
    boxes.append((b.x1, b.y1, b.x2, b.y2))
ink = (min(b[0] for b in boxes), min(b[1] for b in boxes),
       max(b[2] for b in boxes), max(b[3] for b in boxes))
print("口  ink_box =", tuple(round(v,1) for v in ink))
segs = cb.segments_of(bones)
cx, cy = cb.axis_mean(segs,0), cb.axis_mean(segs,1)
print(f"  center = ({cx:.1f},{cy:.1f})  段数 {len(segs)}")
for q in (None, 0.5, 0.3, 0.1, 0.0):
    cb.QUANTILE = None if q is None else q
    f = cb.central_box(bones, ink_box=ink)
    print(f"  QUANTILE={str(q):5s} → {tuple(round(v,1) for v in f)}  "
          f"宽 {f[2]-f[0]:6.1f}")
# 直接看单侧分位
for q in (0.0, 0.25, 0.5, 1.0):
    v = cb.side_quantile(segs, 0, -1, cx, q)
    print(f"  x 左侧 q={q:.2f} → {v if v is None else round(v,1)}")
cb.QUANTILE = None
