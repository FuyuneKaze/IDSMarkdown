import sys, io, contextlib, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
CASES = [("⿴","u56d7","u4eba"),("⿴","u56d7","u4e36"),("⿴","u56d7","u4e00"),
         ("⿴","u56d7","u4e28"),("⿴","u56d7","u4e42"),("⿴","u56d7","u53b6"),
         ("⿴","u53e3","u4eba"),("⿴","u7530","u4eba"),("⿴","u65e5","u4e00"),
         ("⿵","u5182","u4eba"),("⿵","u5182","u4e36"),("⿶","u51f5","u4eba"),
         ("⿷","u533a","u4eba"),("⿸","u5382","u4eba"),("⿸","u5382","u4e36"),
         ("⿹","u5f13","u4eba"),("⿺","u8fb6","u4eba"),("⿺","u8fb6","u4e36"),
         ("⿻","u4e00","u4e28"),("⿸","u5c38","u4eba"),("⿸","u7592","u7ca4"),
         ("⿴","u9b3c","u53e3"),("⿴","u8001","u53e3"),("⿸","u9e7f","u4e36")]
ok = bad = 0
for op, cont, inner in CASES:
    try:
        with contextlib.redirect_stdout(buf):
            out = ids_anal.IDS(op, [cont, inner])
        b = ids_anal.LAST_BOXES
        ibb = b["components"][1] if len(b["components"]) > 1 else None
        f = lambda t: "None" if not t else "(%5.1f,%5.1f)-(%5.1f,%5.1f)" % tuple(float(v) for v in t)
        print(f"  OK  {op}{cont}+{inner:6s} ibb={f(ibb)}")
        ok += 1
    except Exception as e:
        print(f"  崩! {op}{cont}+{inner:6s} {type(e).__name__}: {e}")
        bad += 1
print(f"\n成功 {ok}, 失败 {bad}")
