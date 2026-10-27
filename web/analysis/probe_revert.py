import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
f1 = lambda t: "None" if not t else "(%5.1f,%5.1f)-(%5.1f,%5.1f)" % tuple(float(v) for v in t)
print("用例              cavity                    ibb(内部件盒)             target")
for op, cont, inner in (("⿴","u56d7","u4eba"),("⿴","u65e5","u4e00"),
                        ("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),
                        ("⿸","u9e7f","u4e36"),("⿴","u9b3c","u53e3")):
    with contextlib.redirect_stdout(buf):
        ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    ibb = b["components"][1] if len(b["components"]) > 1 else None
    tgt = ids_anal.fit_into(ibb, b["cavity"]) if ibb and b["cavity"] else None
    print(f"{op}{cont}+{inner:6s} {f1(b['cavity']):>26s} {f1(ibb):>24s} {f1(tgt):>24s}")
