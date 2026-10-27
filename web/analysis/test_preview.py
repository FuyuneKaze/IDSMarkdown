# -*- coding: utf-8 -*-
"""测试 preview.synth_batch —— 不启动 HTTP, 直接调合成"""
import sys, io, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\web\preview")

t0 = time.time()
import preview
print(f"--- import preview (含建索引): {time.time()-t0:.1f}s ---\n")

cases = [
    "⿰忄忽",     # 你的例子
    "⿰氵工",
    "⿰木木",
    "⿰口木",
    "⿱艹朋",
    "⿰亻尔",
    "⿰日月",
    "⿰扌土",
    "⿰糹工",
    "⿲木木木",   # 三元
    "⿰",         # 部件不足 → 应报错
    "木木",       # 无操作符 → 应报错
    "⿰𠀀木",    # 生僻部件 → 可能无变体
]

t0 = time.time()
rs = preview.synth_batch(cases)
total = time.time() - t0
print(f"批量 {len(cases)} 个: {total*1000:.0f}ms  (每个 {total/len(cases)*1000:.0f}ms)\n")
print(f"{'IDS':<10} {'结果':<10} {'轮廓':>5} {'点数':>6}  说明")
print("-" * 72)
for r in rs:
    ok = r["contours"] is not None
    n = r["info"]["n_contours"] if r["info"] else ""
    p = r["info"]["n_points"] if r["info"] else ""
    note = ""
    if r.get("names"):
        note = "+".join(r["names"])
    if r.get("error"):
        note = r["error"].split("\n")[0][:46]
    print(f"{r['ids']:<10} {'OK' if ok else 'FAIL':<10} {str(n):>5} {str(p):>6}  {note}")
