# -*- coding: utf-8 -*-
"""
验证 preview 的 get_data 替换层能正确处理新签名 (mode / order)

原版 get_data 每次是 250 万行线性扫描 (~3s), 所以对照样本必须少,
只挑能触发语义分支的用例。
"""
import sys, io, time, random, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")

import glyph_extend
ORIG = glyph_extend.get_data
# 浅拷贝: preview 导入时会 clear() 掉 glyph_extend.dbs (同一个 list 对象),
# 另存一份指针列表才能保住原版对照的数据 (字符串共享, 省内存)
LINES = list(glyph_extend.dbs)
print(f"dump 行数 {len(LINES):,}")

import preview                     # 此处会把 get_data 换成索引版
FAST = preview._fast_get_data
print(f"preview 已替换 get_data; 索引 {len(preview._INDEX):,}\n")


def t_orig(fn, *a, **kw):
    t0 = time.time()
    v = fn(*a, **kw)
    return v, time.time() - t0


print("=" * 82)
print("① mode='single'  索引版 vs 原版")
print("=" * 82)
# 覆盖: 存在 / 缺后缀退化 / 完全不存在
CASES = ["u5e7f-05", "u7592-05", "u4eba-06", "u53e3-06",
         "u8fb6-05", "u4e00", "zzzznope", "u670b-04"]
bad = 0
for t in CASES:
    a, dt = t_orig(ORIG, t, LINES, mode="single")
    b = FAST(t, None, mode="single")
    ok = a == b
    bad += 0 if ok else 1
    print(f"  {t:<12} {'一致' if ok else '不一致!'}  "
          f"orig={len(a):>4}字符({dt:.1f}s)  fast={len(b):>4}字符")
    if not ok:
        print(f"      orig={a[:50]!r}\n      fast={b[:50]!r}")
print(f"  → 不一致 {bad}/{len(CASES)}")

print()
print("=" * 82)
print("② mode='candidate'  索引版 vs 原版 (含 order)")
print("=" * 82)
CAND = [("u4eba-06", ["-ww", "-05", "-04", "-03", "-02"]),
        ("u5e7f-05", ["-05", "-10"]),
        ("u53e3-06", ["-05"])]
bad2 = 0
for t, od in CAND:
    a, dt = t_orig(ORIG, t, LINES, mode="candidate", order=od)
    b = FAST(t, None, mode="candidate", order=od)
    ok = a == b
    bad2 += 0 if ok else 1
    def brief(v):
        if isinstance(v, tuple):
            return tuple((x[:22] + "…" if isinstance(x, str) and len(x) > 22 else x)
                         for x in v)
        return v
    print(f"  {t:<12} order={od}")
    print(f"    {'一致' if ok else '不一致!'}  ({dt:.1f}s)  {brief(a)}")
    if not ok:
        print(f"      fast={brief(b)}")
print(f"  → 不一致 {bad2}/{len(CAND)}")

print()
print("=" * 82)
print("③ return_bone(parts_mode='candidate') 端到端")
print("=" * 82)
order = ["-ww", "-05", "-04", "-03", "-02"]
for nm in ["u4eba-06", "u5e7f-05", "u7592-05"]:
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            r = glyph_extend.return_bone(nm, parts_mode="candidate", order=order)
        print(f"  {nm:<12} → {len(r)} 字符, {len(r.split('$')) if r else 0} 段")
    except Exception as e:
        print(f"  {nm:<12} 异常 {type(e).__name__}: {e}")

print()
print("=" * 82)
print("④ preview 端到端")
print("=" * 82)
t0 = time.time()
rs = preview.synth_batch(["⿸广付", "⿸疒丙", "⿰氵工", "⿱宀丁"])
print(f"  耗时 {time.time()-t0:.2f}s")
for r in rs:
    ok = "OK" if r.get("contours") else "FAIL"
    n = r["info"]["n_contours"] if r.get("info") else ""
    print(f"  {r['ids']:<8} {ok:<6} {n}")
    if r.get("error"):
        print(f"      {r['error'].splitlines()[0][:72]}")
