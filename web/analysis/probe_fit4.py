import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal, cavity
buf = io.StringIO()
f1 = lambda t: "None" if not t else "(%5.1f,%5.1f)-(%5.1f,%5.1f)" % tuple(float(v) for v in t)
CASES = [("⿴","u56d7","u4eba"),("⿴","u53e3","u4e42"),("⿴","u65e5","u4e00"),
         ("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),("⿸","u9e7f","u4e36"),
         ("⿴","u9b3c","u53e3"),("⿴","u7530","u4e42")]
print("基准 = 墨迹盒外扩 6.8% (alpha=0), 并受 FIT_MAX_SCALE=1.2 约束")
print(f"{'用例':14s} {'cavity':>25s} {'basis(实际用)':>25s} {'缩放比 rect/basis':>14s} {'墨迹占空腔':>9s}")
for op, cont, inner in CASES:
    with contextlib.redirect_stdout(buf):
        ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    cav, bas = b["cavity"], b["basis"]
    ibb = b["components"][1] if len(b["components"])>1 else None
    if not (cav and bas and ibb):
        print(f"{op}{cont}+{inner:8s} 腔或基准缺失"); continue
    scale = (cav[2]-cav[0])/(bas[2]-bas[0])
    occ = (ibb[2]-ibb[0])*scale/(cav[2]-cav[0])
    print(f"{op}{cont}+{inner:8s} {f1(cav):>25s} {f1(bas):>25s} {scale:13.2f}x {occ*100:8.0f}%")
