import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
g = json.load(io.open(r"D:\2026harucpp\web\public\core_glyphs.json", encoding="utf-8"))
g = g.get("glyphs", g)
for nm in ("u9ea6-j", "u5c06-j", "u8fb6-j", "u9f3b-j", "u9ea6", "u4eba-j"):
    print(f"  {nm:10s} {'有' if nm in g else '无'}", (g[nm][:40] if nm in g else ""))
n_j = sum(1 for k in g if k.endswith("-j"))
n_ref = sum(1 for k, v in g.items() if v.startswith("99:"))
print(f"  -j 结尾的名字: {n_j},  数据是 99 引用的条目: {n_ref} / {len(g)}")
# 抽查: 数据以 99 引用结尾 -j 的条目, 其目标是否存在
miss = 0; tot = 0
for k, v in g.items():
    if not v.startswith("99:"):
        continue
    tgt = v.rsplit(":", 1)[-1].split("@")[0]
    tot += 1
    if tgt not in g:
        miss += 1
        if miss <= 5:
            print(f"    缺失引用: {k} → {tgt}")
print(f"  99 引用的目标缺失: {miss} / {tot}")
