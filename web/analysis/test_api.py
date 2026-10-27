# -*- coding: utf-8 -*-
"""HTTP 端到端测试"""
import sys, io, json, time, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


# ---- 1. 首页 ----
try:
    with urllib.request.urlopen(BASE + "/", timeout=20) as r:
        html = r.read().decode("utf-8")
    print(f"[GET /] {r.status}  {len(html):,} bytes  "
          f"{'含 IDS 输入框' if 'textarea' in html else '!!异常'}")
except Exception as e:
    print(f"[GET /] 失败: {e}")
    sys.exit(1)

# ---- 2. 渲染 ----
cases = [
    "⿰忄忽", "⿰氵工", "⿰木木", "⿰口木", "⿱艹朋", "⿰亻尔",
    "⿰日月", "⿰扌土", "⿲木木木", "木木", "⿰𠀀木",
]
t0 = time.time()
res = post("/api/render", {"ids": cases})
dt = time.time() - t0
print(f"\n[POST /api/render] {len(cases)} 个 → {res['total_ms']}ms "
      f"(往返 {dt*1000:.0f}ms)\n")
print(f"{'IDS':<9} {'结果':<6} {'轮廓':>5} {'点数':>6}  说明")
print("-" * 74)
for it in res["results"]:
    ok = "OK" if it.get("contours") else "FAIL"
    n = it["info"]["n_contours"] if it.get("info") else ""
    p = it["info"]["n_points"] if it.get("info") else ""
    note = ""
    if it.get("error"):
        note = " / ".join(it["error"].splitlines()[:2])[:52]
    elif it.get("info"):
        note = "+".join(it["info"].get("names") or [])
    print(f"{it['ids']:<9} {ok:<6} {str(n):>5} {str(p):>6}  {note}")

# ---- 3. 检查失败项的诊断信息质量 ----
print("\n--- 失败项的提示是否区分了'数据缺失/算法问题' ---")
for it in res["results"]:
    if it.get("error"):
        print(f"\n[{it['ids']}]")
        for ln in it["error"].splitlines()[:6]:
            print("   " + ln)
