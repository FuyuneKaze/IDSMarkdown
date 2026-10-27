# -*- coding: utf-8 -*-
"""视觉验证: 用 matplotlib 复刻前端 contourToPath 逻辑, 渲染合成结果到 PNG"""
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
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


cases = ["⿰忄忽", "⿰氵工", "⿰木木", "⿰口木",
         "⿰亻尔", "⿰日月", "⿰扌土", "⿰糹工"]
res = post("/api/render", {"ids": cases})


def contour_to_path(contour):
    """与 preview.py 前端 contourToPath 完全相同的逻辑"""
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
            verts.append((x, y))
            codes.append(Path.MOVETO)
        else:
            verts.append((x, y))
            codes.append(Path.LINETO)

        j = i + 1
        ctrls = []
        while j < len(contour) and contour[j] and contour[j][2] == 1:
            ctrls.append(contour[j])
            j += 1
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
        verts.append(first)
        codes.append(Path.CLOSEPOLY)
    return Path(verts, codes)


ok = [r for r in res["results"] if r.get("contours")]
n = len(ok)
cols = 4
rows = max(1, (n + cols - 1) // cols)
fig, axes = plt.subplots(rows, cols, figsize=(cols * 2.3, rows * 2.5))
axes = list(axes.flatten()) if n > 1 else [axes]

for ax, r in zip(axes, ok):
    for c in r["contours"]:
        ax.add_patch(PathPatch(contour_to_path(c), facecolor="black",
                               edgecolor="none"))
    ax.set_xlim(-6, 206)
    ax.set_ylim(-6, 206)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.set_title(f"{r['ids']}  {r['info']['n_contours']}轮廓", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#cccccc")
for ax in axes[n:]:
    ax.axis("off")

plt.tight_layout()
out = r"D:\2026harucpp\web\analysis\preview_check.png"
plt.savefig(out, dpi=110, facecolor="white")
print(f"渲染 {n} 个字形 → {out}")
print(f"服务端耗时 {res['total_ms']}ms")
