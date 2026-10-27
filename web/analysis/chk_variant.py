import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
db = json.load(open(r"D:\2026harucpp\web\public\core_glyphs.json", encoding="utf-8"))["glyphs"]
for nm in ["u53e3-01", "u6c35-01", "u6728-01", "u624c-01", "u4ebb-01"]:
    d = db.get(nm)
    print(f"{nm}: {d}")
    print()
