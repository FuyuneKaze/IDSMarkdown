import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend, ids_anal
buf = io.StringIO()
def q(fn, *a, **kw):
    with contextlib.redirect_stdout(buf):
        return fn(*a, **kw)

print("① 精确优先是否修好 鹿-05 (期望 3+10 = 13 笔, 与编辑器一致)")
for nm in ("u9e7f-05", "u2ff1-cdp-88b4-u6bd4", "u9e7f"):
    flat = q(glyph_extend.return_bone, nm)
    st = [s for s in flat.split("$") if s.split(":")[0] in ("1","2","3","4","6","7")]
    print(f"   {nm:24s} {len(st):3d} 笔")
print()
print("② 第一轮叶子查找必须保持原样 (子串退化)")
for nm in ("u5b80-03", "u4e01-04", "u5ffd-02"):
    flat = q(glyph_extend.return_bone, nm)
    st = [s for s in flat.split("$") if s.split(":")[0] in ("1","2","3","4","6","7")]
    print(f"   {nm:24s} {len(st):3d} 笔")
print()
print("③ ⿸鹿 现在什么样")
with contextlib.redirect_stdout(buf):
    out = ids_anal.IDS("⿸", ["u9e7f", "u4eba"])
b = ids_anal.LAST_BOXES
fmt = lambda t: "None" if not t else "[%6.1f,%6.1f,%6.1f,%6.1f]" % tuple(t)
print(f"   容器笔画 {len(out.split('$'))} 段  外框 {fmt(b['outer'])}")
print(f"   候选 {len(b['candidates'])}: " + "  ".join(f"[{i}]{fmt(c)}" for i,c in enumerate(b["candidates"])))
print(f"   选中腔 {fmt(b['cavity'])}")
