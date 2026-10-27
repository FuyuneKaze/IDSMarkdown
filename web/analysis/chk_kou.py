import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
db = json.load(open(r"D:\2026harucpp\web\public\core_glyphs.json", encoding="utf-8"))["glyphs"]

def parse(data):
    refs = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
    return refs

def resolve(name, hop=10):
    cur = db.get(name)
    for _ in range(hop):
        if cur is None: return None
        r = parse(cur)
        if len(r) == 1 and "$" not in cur.replace("$","",0) and len(r) == 1:
            refs = parse(cur)
            if len(refs) == 1:
                nxt = refs[0][4].split("@")[0]
                if nxt in db and nxt != name:
                    cur = db[nxt]; name = nxt; continue
        break
    return cur

# 看"口"作为左旁在不同字里的引用矩形
print("口 作为左旁 (⿰口X) 的引用矩形:")
for ch in ["叶","吐","叫","吸","吧","听","吗","呢","唱","味","呼","咬"]:
    nm = f"u{ord(ch):x}"
    d = resolve(nm)
    if d is None:
        continue
    refs = parse(d)
    for (x1,y1,x2,y2,rn) in refs:
        if rn.startswith("u53e3"):
            w = x2-x1
            print(f"  {ch} ({nm}): u53e3 引用矩形=({x1},{y1},{x2},{y2}) 宽={w}  变体={rn}")
            break
