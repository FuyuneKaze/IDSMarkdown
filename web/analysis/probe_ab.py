import sys, io, contextlib, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview
import glyph_extend
buf = io.StringIO()

def timeit(fn, n):
    with contextlib.redirect_stdout(buf):
        fn()                      # 预热
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        return (time.perf_counter() - t0) / n

for nm in ("u9e7f-05", "u56fd", "u7ca4"):
    f = lambda: glyph_extend.return_bone(nm)
    tp_fast = timeit(f, 60)
    old = glyph_extend._num
    glyph_extend._num = eval                       # 换回 eval 做 A/B
    tp_eval = timeit(f, 60)
    glyph_extend._num = old
    print(f"  return_bone({nm:9s})  int/float {tp_fast*1000:6.2f} ms | eval {tp_eval*1000:6.2f} ms "
          f"| 提速 {tp_eval/tp_fast:4.1f}x")

# 端到端: 20 个包围用例
import ids_anal
CASES = [("⿴","u56d7","u4eba"),("⿴","u56d7","u4e36"),("⿴","u56d7","u4e00"),
         ("⿴","u56d7","u4e28"),("⿴","u56d7","u4e42"),("⿴","u53e3","u4eba"),
         ("⿴","u7530","u4eba"),("⿴","u65e5","u4e00"),("⿵","u5182","u4eba"),
         ("⿶","u51f5","u4eba"),("⿷","u533a","u4eba"),("⿸","u5382","u4eba"),
         ("⿹","u5f13","u4eba"),("⿺","u8fb6","u4eba"),("⿸","u7592","u7ca4"),
         ("⿴","u9b3c","u53e3"),("⿸","u9e7f","u4e36"),("⿴","u8001","u53e3"),
         ("⿴","u56d7","u53b6"),("⿸","u5c38","u4eba")]
def run_all():
    for op, a, b in CASES:
        with contextlib.redirect_stdout(buf):
            ids_anal.IDS(op, [a, b])
t_fast = timeit(run_all, 5) / len(CASES)
old = glyph_extend._num
glyph_extend._num = eval
t_eval = timeit(run_all, 5) / len(CASES)
glyph_extend._num = old
print(f"  端到端 单次 IDS: int/float {t_fast*1000:6.1f} ms | eval {t_eval*1000:6.1f} ms "
      f"| 提速 {t_eval/t_fast:4.1f}x")
