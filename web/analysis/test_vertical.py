# -*- coding: utf-8 -*-
"""⿱ 上下结构回归测试"""
import sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


v_cases = [
    ("⿱宀丁", "定"), ("⿱日木", "杳"), ("⿱木木", "?"), ("⿱口木", "?"),
    ("⿱亠口", "?"), ("⿱八刀", "分"), ("⿱立日", "音"), ("⿱日十", "早"),
    ("⿱人木", "?"), ("⿱艹朋", "?"), ("⿱山石", "岩"), ("⿱日生", "星"),
    ("⿱田力", "男"), ("⿱小白", "?"), ("⿱雨田", "雷"),
]
h_cases = [("⿰氵工", "江"), ("⿰木木", "林"), ("⿰日月", "明")]

allc = v_cases + h_cases
res = post("/api/render", {"ids": [c[0] for c in allc]})
label = {c[0]: c[1] for c in allc}

print(f"共 {len(allc)} 个 → 服务端 {res['total_ms']}ms\n")
print(f"{'IDS':<8} {'期望':<5} {'结果':<6} {'轮廓':>5} {'点数':>6}  说明")
print("-" * 76)
nok = nbad = 0
for it in res["results"]:
    ok = bool(it.get("contours"))
    if ok:
        nok += 1
    else:
        nbad += 1
    n = it["info"]["n_contours"] if it.get("info") else ""
    p = it["info"]["n_points"] if it.get("info") else ""
    note = ""
    if it.get("error"):
        note = " / ".join(it["error"].splitlines()[:2])[:44]
    print(f"{it['ids']:<8} {label.get(it['ids'], ''):<5} "
          f"{'OK' if ok else 'FAIL':<6} {str(n):>5} {str(p):>6}  {note}")

print("-" * 76)
print(f"成功 {nok} / 失败 {nbad}")
vn = sum(1 for it in res["results"] if it["ids"] in dict(v_cases) and it.get("contours"))
print(f"其中 ⿱ 上下结构: {vn} / {len(v_cases)} 成功")
