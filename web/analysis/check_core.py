import json, sys, io, collections
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
p = r"D:\2026harucpp\web\public\core_glyphs.json"
d = json.load(open(p, encoding="utf-8"))
g = d["glyphs"]
print("总字形数:", len(g))
test = ["u6708","u6708-01","u6708-02","u6c34-01","u624c-01","u53e3-01",
        "u65e5-01","u76ee-01","u7530-01","u7cf8-01","u8ba0-01","u6728-01","u6728-02"]
for n in test:
    print(f"  {n:<12} {'OK' if n in g else 'MISSING'}")
n_dash = sum(1 for k in g if "-" in k)
print(f"含 '-' 的名字数: {n_dash}")
n_var = sum(1 for k in g if "-var-" in k)
print(f"含 '-var-' 的名字数: {n_var}")
