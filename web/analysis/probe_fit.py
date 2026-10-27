import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
f1 = lambda t: "None" if not t else "(%6.1f,%6.1f)-(%6.1f,%6.1f)" % tuple(t)
CASES = [("⿴","u56d7","u4eba"),("⿴","u56fd","u7389"),("⿴","u53e3","u4e42"),
         ("⿴","u65e5","u4e00"),("⿸","u5382","u4eba"),("⿺","u8fb6","u5bf8"),
         ("⿸","u9e7f","u4e36"),("⿵","u5182","u4e42")]
print(f"{'用例':14s} {'cavity':>30s} {'basis(内部件)':>30s} {'目标矩形':>30s}")
for op, cont, inner in CASES:
    with contextlib.redirect_stdout(buf):
        out = ids_anal.IDS(op, [cont, inner])
    b = ids_anal.LAST_BOXES
    # 复算 target 便于展示
    ibb = b["components"][1] if len(b["components"]) > 1 else None
    tgt = ids_anal.fit_into(ibb, b["cavity"], b["basis"]) if ibb and b["cavity"] else None
    print(f"{op}{cont}+{inner:8s} {f1(b['cavity']):>30s} {f1(b['basis']):>30s} {f1(tgt):>30s}")
