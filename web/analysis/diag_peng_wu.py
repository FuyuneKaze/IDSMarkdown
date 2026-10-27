# -*- coding: utf-8 -*-
"""诊断 ⿱艹朋 / ⿱勿心"""
import sys, io, json, urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


cases = ["⿱艹朋", "⿱勿心", "⿱艹明", "⿱勿木", "⿱日朋", "⿱日心",
         "⿱宀丁", "⿰氵工"]
res = post("/api/render", {"ids": cases})
print("=== API 结果 ===")
for it in res["results"]:
    st = f"OK {it['info']['n_contours']}轮廓" if it.get("contours") else "FAIL"
    print(f"  {it['ids']:<8} {st}")
    if it.get("error"):
        for ln in it["error"].splitlines()[:4]:
            print("      " + ln)

# ---- 检查部件数据 ----
print("\n=== 部件变体数据特征 ===")
import glyph_extend
IDX = {}
for ln, line in enumerate(glyph_extend.dbs):
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    IDX[cols[0].strip()] = cols[2].strip()


def show(ch):
    cp = ord(ch)
    nm = f"u{cp:x}"
    print(f"\n  {ch} ({nm}):")
    for sfx in ["", "-01", "-02", "-03", "-04"]:
        k = nm + sfx
        d = IDX.get(k)
        if d is None:
            print(f"    {k:<12} 【不存在】")
            continue
        # 找数据里的特殊标记
        marks = []
        for seg in d.split("$"):
            p = seg.split(":")
            if p[0] == "99":
                marks.append("99引用")
            elif p[0] == "0" and len(p) > 1 and p[1] in ("97", "98", "99"):
                marks.append(f"图元变形0:{p[1]}:{p[2] if len(p)>2 else '?'}")
            elif p[0] == "0":
                marks.append("特殊行0")
        n99 = sum(1 for s in d.split("$") if s.split(":")[0] == "99")
        nstr = sum(1 for s in d.split("$") if s.split(":")[0] in
                   ("1", "2", "3", "4", "6", "7"))
        print(f"    {k:<12} len={len(d):<5} 笔画={nstr:<3} 99引用={n99:<3} "
              f"{' '.join(sorted(set(marks)))}")
        if sfx in ("", "-04") and len(d) < 200:
            print(f"        data: {d}")


for ch in "艹朋勿心日木明丁工":
    show(ch)
