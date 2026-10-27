import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
p = r"D:\2026harucpp\scripts\ids_anal.py"
t = io.open(p, encoding="utf-8", newline="").read()
for old, new in (("x = [eval(i) for i in li[3::2]]", "x = [float(i) for i in li[3::2]]"),
                 ("y = [eval(i) for i in li[4::2]]", "y = [float(i) for i in li[4::2]]")):
    n = t.count(old)
    print(f"  {old[:28]:30s} × {n}")
    t = t.replace(old, new)
io.open(p, "w", encoding="utf-8", newline="").write(t)
left = [i+1 for i, ln in enumerate(t.split("\n")) if "eval(" in ln and "eval1(" not in ln]
print("ids_anal 剩余 eval( 行:", left)
