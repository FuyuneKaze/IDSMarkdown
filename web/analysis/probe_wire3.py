import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(float(v) for v in t)
CASES = [("⿴","u56d7","u4eba"),("⿴","u56d7","u4e36"),("⿴","u56d7","u4e42"),
         ("⿴","u65e5","u4e00"),("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),
         ("⿸","u9e7f","u4e36"),("⿴","u9b3c","u53e3"),("⿸","u7592","u7ca4")]
print("用例              cavity                    ibb                    target(use_bbox=True)   放大率")
for op, cont, inner in CASES:
    with contextlib.redirect_stdout(buf):
        ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    cav = b["cavity"]; ibb = b["components"][1] if len(b["components"]) > 1 else None
    if not cav or not ibb:
        print(f"{op}{cont}+{inner:6s} 缺 cav/ibb"); continue
    tgt = ids_anal.fit_into(ibb, cav, use_bbox=True)
    mag = (cav[2]-cav[0])/(ibb[2]-ibb[0]) if ibb[2] > ibb[0] else 0
    print(f"{op}{cont}+{inner:6s} {f1(cav):>26s} {f1(ibb):>24s} {f1(tgt):>26s} {mag:6.2f}x")
