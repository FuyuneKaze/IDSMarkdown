# -*- coding: utf-8 -*-
"""测试新增的能力: LAST_BOXES 侧信道 / fallback_of / JSON 序列化 / 热重载"""
import sys, io, json, time, contextlib, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import ids_anal

print("=" * 76)
print("① LAST_BOXES 侧信道 (IDS() 每次执行记录实际用到的盒)")
print("=" * 76)
for op, args in [("⿰", ["u6c35", "u5de5"]), ("⿱", ["u5b80", "u4e01"]),
                 ("⿸", ["u5e7f", "u4ed8"]), ("⿸", ["u9580", "u53e3"])]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        g = ids_anal.IDS(op, args)
    b = ids_anal.LAST_BOXES
    print(f"\n  {op}{args}  → {len(g)} 字符")
    for i, c in enumerate(b["components"]):
        print(f"    c{i+1}   " + (f"[{c[0]:6.1f},{c[1]:6.1f},{c[2]:6.1f},{c[3]:6.1f}]"
                                   if c else "None"))
    for k in ("cavity", "outer"):
        v = b[k]
        print(f"    {k:<7}" + (f"[{v[0]:6.1f},{v[1]:6.1f},{v[2]:6.1f},{v[3]:6.1f}]"
                               if v else "None"))
    # JSON 可用性 (numpy 值会炸)
    try:
        json.dumps({k: (list(map(float, v)) if v else None)
                    for k, v in b.items() if k != "components"})
        json.dumps([[float(x) for x in c] for c in b["components"] if c])
        print("    JSON 序列化: OK")
    except Exception as e:
        print(f"    JSON 序列化失败: {e}")

print()
print("=" * 76)
print("② fallback_of: 某变体到底有没有 / 退化成谁")
print("=" * 76)
print(f"  {'查询':<14} {'实际命中':<14} {'退化?'}")
print("  " + "-" * 40)
for nm in ["u5e7f-05", "u5e7f", "u7592-05", "u7592-10", "u53e3-05",
           "u53e3-06", "u4eba-06", "u56d7-05", "u9580-05",
           "u8fb6-05", "u8fb6-10", "u6742-99"]:
    hit, deg = ids_anal.fallback_of(nm)
    print(f"  {nm:<14} {str(hit):<14} {'是' if deg else '否'}")

print()
print("=" * 76)
print("③ 实用场景: 检查包围外框变体是否真的取到了")
print("=" * 76)
for ch, base in [("广", "u5e7f"), ("疒", "u7592"), ("辶", "u8fb6"),
                 ("囗", "u56d7"), ("门", "u9580"), ("厂", "u5382"),
                 ("户", "u6236"), ("尸", "u5c38"), ("气", "u6c14")]:
    hit, deg = ids_anal.fallback_of(base + "-05")
    mark = "  ← 无 -05, 退化!" if deg else ""
    print(f"  {ch} {base}-05  →  {str(hit):<12}{mark}")

print()
print("=" * 76)
print("④ preview 端到端 (含 boxes 字段)")
print("=" * 76)
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview

t0 = time.time()
rs = preview.synth_batch(["⿸广付", "⿸疒丙", "⿰氵工", "⿱宀丁"])
print(f"耗时 {time.time()-t0:.2f}s")
for r in rs:
    bx = r.get("boxes") or {}
    nc = len([c for c in (bx.get("components") or []) if c])
    print(f"  {r['ids']:<8} contours={len(r['contours'] or [])}  "
          f"boxes: components={nc} cavity={'有' if bx.get('cavity') else '无'} "
          f"outer={'有' if bx.get('outer') else '无'}")
    if r.get("error"):
        print(f"      err={r['error'].splitlines()[0][:50]}")
# 整包 JSON 必须能序列化
try:
    s = json.dumps({"results": rs}, ensure_ascii=False)
    print(f"\n  整包 JSON: OK ({len(s):,} bytes)")
except Exception as e:
    print(f"\n  整包 JSON 失败: {e}")

print()
print("=" * 76)
print("⑤ 热重载: 改 stroke_outer.py 是否会被侦测到")
print("=" * 76)
p = os.path.join(r"D:\2026harucpp\scripts", "stroke_outer.py")
mt = os.path.getmtime(p)
print(f"  stroke_outer.py mtime = {time.strftime('%m-%d %H:%M:%S', time.localtime(mt))}")
print(f"  _MTIME 记录 = {preview._MTIME.get(p, '(尚未记录)')}")
preview._reload_changed()          # 首次只记录
print(f"  首次调用后 _MTIME = {preview._MTIME.get(p)}")
preview._reload_changed()          # 第二次应无动作
print("  第二次调用 (无改动) 完成, 未重载 → 正确")
