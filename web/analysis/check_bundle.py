import json, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
p = r"D:\2026harucpp\web\public\core_glyphs.json"
d = json.load(io.open(p, encoding="utf-8"))
g = d.get("glyphs", d)
print("bundle 字形数:", len(g))
for nm in ("u9ea6-01", "u5c06-02", "u5fc4-01", "u675f-01", "u8d1f-02", "u4e00-03", "u4e28-04",
           "u9ea6", "u5c06", "u5fc4", "u8fb6-05", "u9f3b-06"):
    print(f"  {nm:12s} {'有' if nm in g else '无'}")
import collections
c = collections.Counter()
for k in g:
    if "-" in k:
        suf = k.rsplit("-", 1)[-1]
        if suf.isdigit():
            c[suf] += 1
print("  数字后缀分布(前 8):", c.most_common(8))
