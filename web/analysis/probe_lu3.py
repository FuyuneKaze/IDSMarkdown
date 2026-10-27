import sys, io, contextlib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview, glyph_extend
IDX = preview._INDEX          # name -> (行号, data)

def show(nm):
    hit = IDX.get(nm)
    if not hit:
        print(f"  {nm:24s} × 库里没有这条 (精确名)")
        return
    ln, data = hit
    segs = [s for s in data.split("$") if s]
    st = [s for s in segs if s.split(":")[0] in ("1","2","3","4","6","7")]
    refs = [(s.split(":")[7], s.split(":")[3:7]) for s in segs if s.split(":")[0] == "99"]
    print(f"  {nm:24s} 行{ln:8d}  {len(segs)} 段 = {len(st)} 笔画 + {len(refs)} 引用")
    for r in refs:
        print(f"      → {r[0]:22s} rect={r[1]}")

for nm in ("u9e7f-05", "u2ff1-cdp-88b4-u6bd4", "u9e7f-jn", "u9e7f", "u6bd4-j"):
    show(nm)

print("\n  get_data(target) 实际命中 (取行号最大的子串命中):")
for t in ("u9e7f-05", "u9e7f", "u5e7f-05"):
    best = None
    for nm, (ln, data) in IDX.items():
        if nm in t and (best is None or ln > best[1]):
            best = (nm, ln)
    print(f"    {t:12s} → {best[0] if best else None} (行{best[1] if best else '-'})")
