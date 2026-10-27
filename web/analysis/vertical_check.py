# -*- coding: utf-8 -*-
"""⿱ 上下结构视觉验证"""
import sys, io, json, urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
BASE = "http://127.0.0.1:18080"


def post(path, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


cases = ["⿱宀丁", "⿱日木", "⿱八刀", "⿱立日", "⿱日十",
         "⿱山石", "⿱日生", "⿱田力", "⿱雨田", "⿱艹朋"]
res = post("/api/render", {"ids": cases})


def contour_to_path(contour):
    verts, codes = [], []
    first = None
    i = 0
    while i < len(contour):
        p = contour[i]
        if not p or p[2] != 0:
            i += 1
            continue
        x, y = p[0], p[1]
        if first is None:
            first = (x, y)
            verts.append((x, y)); codes.append(Path.MOVETO)
        else:
            verts.append((x, y)); codes.append(Path.LINETO)
        j = i + 1
        ctrls = []
        while j < len(contour) and contour[j] and contour[j][2] == 1:
            ctrls.append(contour[j]); j += 1
        if ctrls and j < len(contour) and contour[j] and contour[j][2] == 0:
            e = contour[j]
            if len(ctrls) == 1:
                verts.append((ctrls[0][0], ctrls[0][1])); codes.append(Path.CURVE3)
                verts.append((e[0], e[1]));               codes.append(Path.CURVE3)
            else:
                verts.append((ctrls[0][0], ctrls[0][1])); codes.append(Path.CURVE4)
                verts.append((ctrls[1][0], ctrls[1][1])); codes.append(Path.CURVE4)
                verts.append((e[0], e[1]));               codes.append(Path.CURVE4)
            i = j
            continue
        i += 1
    if first is not None:
        verts.append(first); codes.append(Path.CLOSEPOLY)
    return Path(verts, codes)


ok = [r for r in res["results"] if r.get("contours")]
cols = 5
rows = max(1, (len(ok) + cols - 1) // cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.0, rows * 2.3))
axes = list(axes.flatten())

for k, (ax, r) in enumerate(zip(axes, ok)):
    for c in r["contours"]:
        ax.add_patch(PathPatch(contour_to_path(c), facecolor="black",
                               edgecolor="none"))
    ax.set_xlim(-6, 206); ax.set_ylim(-6, 206)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_title(f"#{k+1}", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#bbbbbb")
for ax in axes[len(ok):]:
    ax.axis("off")

plt.tight_layout()
out = r"D:\2026harucpp\web\analysis\vertical_check.png"
plt.savefig(out, dpi=115, facecolor="white")
print(f"→ {out}")
print(f"服务端 {res['total_ms']}ms, 渲染 {len(ok)} 格")
print("\n编号对应:")
for k, r in enumerate(ok):
    print(f"  #{k+1}  {r['ids']}   {r['info']['n_contours']}轮廓")
