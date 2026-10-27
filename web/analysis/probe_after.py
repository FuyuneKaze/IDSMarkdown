import sys, io, contextlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, ids_anal
buf = io.StringIO()
CASES = [("⿴","u56d7","u4eba"),("⿴","u56d7","u4e36"),("⿴","u56d7","u4e00"),
         ("⿴","u56d7","u4e28"),("⿴","u56d7","u4e42"),("⿴","u56d7","u53b6"),
         ("⿴","u53e3","u4eba"),("⿴","u7530","u4eba"),("⿴","u65e5","u4e00"),
         ("⿵","u5182","u4eba"),("⿶","u51f5","u4eba"),("⿷","u533a","u4eba"),
         ("⿸","u5382","u4eba"),("⿹","u5f13","u4eba"),("⿺","u8fb6","u4eba"),
         ("⿻","u4e00","u4e28"),("⿸","u7592","u7ca4"),("⿴","u9b3c","u53e3"),
         ("⿸","u9e7f","u4e36"),("⿴","u8001","u53e3")]
f = lambda t: "None" if not t else "(%5.1f,%5.1f)-(%5.1f,%5.1f)" % tuple(float(v) for v in t)
ok = bad = 0
t0 = time.time()
for op, cont, inner in CASES:
    try:
        with contextlib.redirect_stdout(buf):
            ids_anal.IDS(op, [cont, inner])
        b = ids_anal.LAST_BOXES
        ibb = b["components"][1] if len(b["components"]) > 1 else None
        print(f"  OK  {op}{cont}+{inner:6s} ibb={f(ibb)}")
        ok += 1
    except Exception as e:
        print(f"  崩! {op}{cont}+{inner:6s} {type(e).__name__}: {e}")
        bad += 1
print(f"\n成功 {ok}, 失败 {bad}, 用时 {time.time()-t0:.1f}s")

# 微基准: eval vs 新解析
import random
toks = ["104","13","54.16","0","200","-5","25.675","187.5"]
N = 20000
t0 = time.time()
for _ in range(N):
    for s in toks: eval(s)
t_eval = time.time()-t0
t0 = time.time()
for _ in range(N):
    for s in toks: (float(s) if "." in s else int(s))
t_fast = time.time()-t0
print(f"\n微基准 {N}×{len(toks)} 个字段: eval {t_eval*1000:.0f} ms → int/float {t_fast*1000:.0f} ms "
      f"(快 {t_eval/t_fast:.1f}x)")
