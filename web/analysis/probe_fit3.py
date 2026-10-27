import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
f1 = lambda t: "None" if not t else "(%5.1f,%5.1f)-(%5.1f,%5.1f)" % tuple(float(v) for v in t)
CASES = [("⿴","u56d7","u4eba"),("⿴","u53e3","u4e42"),("⿴","u65e5","u4e00"),
         ("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),("⿸","u9e7f","u4e36"),
         ("⿴","u9b3c","u53e3")]
print(f"{'用例':14s} {'cavity':>26s} {'basis':>26s} {'内部件盒 ibb':>26s} {'有效放大':>8s}")
for op, cont, inner in CASES:
    with contextlib.redirect_stdout(buf):
        ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    cav, bas, ibb = b["cavity"], b["basis"], (b["components"][1] if len(b["components"])>1 else None)
    mag = ""
    if cav and bas:
        mag = f"{(cav[2]-cav[0])/(bas[2]-bas[0]):.2f}x"
    print(f"{op}{cont}+{inner:8s} {f1(cav):>26s} {f1(bas):>26s} {f1(ibb):>26s} {mag:>8s}")
