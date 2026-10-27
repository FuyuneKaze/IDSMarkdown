# -*- coding: utf-8 -*-
"""确认 preview 工具能直接跑 ⿸ (即用户在页面输入 ⿸广付 的路径)"""
import sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\web\preview")

t0 = time.time()
import preview
print(f"import preview: {time.time()-t0:.1f}s")

# 首次调用会触发 ids_anal.name_set() 建精确名字表, 单独计时
t0 = time.time()
r1 = preview.synth_batch(["⿸广付"])
print(f"首次 (含 name_set 构建): {time.time()-t0:.2f}s")

t0 = time.time()
CASES = ["⿸广付", "⿸疒丙", "⿸户方", "⿸厂㔾", "⿸广木", "⿸尸由",
         "⿰氵工", "⿱宀丁"]
rs = preview.synth_batch(CASES)
print(f"后续 {len(CASES)} 个: {time.time()-t0:.2f}s\n")

print(f"{'IDS':<9} {'结果':<6} {'轮廓':>5} {'点数':>6}  说明")
print("-" * 70)
for it in rs:
    ok = "OK" if it.get("contours") else "FAIL"
    n = it["info"]["n_contours"] if it.get("info") else ""
    p = it["info"]["n_points"] if it.get("info") else ""
    note = ""
    if it.get("error"):
        note = " / ".join(it["error"].splitlines()[:2])[:40]
    print(f"{it['ids']:<9} {ok:<6} {str(n):>5} {str(p):>6}  {note}")
