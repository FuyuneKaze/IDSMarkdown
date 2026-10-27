# -*- coding: utf-8 -*-
"""
分配算式的纯函数参考数据

ids_anal.IDS 的 ⿰⿱⿲⿳ 分支里, 真正决定矩形的那几行只依赖「两个/三个包围盒」,
与字形无关。所以这里把那几行原样抄出来, 喂随机盒, 生成大批对照数据。

用随机盒而不是真字形的原因: 真字形跑一例要几分钟 (每例都要加载 KAGE 数据
并递归展开), 而算式的定义域 —— 空盒、倒置盒、越界盒、极扁/极窄盒 —— 只能靠
造数据覆盖。真字形的端到端对照另见 layout_ref_gen.py (13 例, 已逐步一致)。
"""
import sys, io, json, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

from ids_anal import minmax  # noqa: E402


def mm_hor(b1, b2):
    """⿰ 分支 (ids_anal.py 302-332) 的算式部分"""
    w1, w2 = b1[2] - b1[0], b2[2] - b2[0]
    w1, w2 = minmax(5, w1, 195), minmax(5, w2, 195)
    split = 3 + 197 * w1 / (w1 + w2)
    split = minmax(5, split, 195)
    leftbound = split * 200 / max(b1[2], 1)
    rightbound = 200 - 200 * (200 - split) / (200 - max(1, b2[0]))
    return [[0, 0, leftbound, 200], [rightbound, 0, 200, 200]]


def mm_ver(b1, b2):
    """⿱ 分支 (ids_anal.py 335-371) 的算式部分"""
    h1, h2 = b1[3] - b1[1], b2[3] - b2[1]
    h1, h2 = minmax(5, h1, 195), minmax(5, h2, 195)
    split = 3 + 197 * h1 / (h1 + h2)
    split = minmax(5, split, 195)
    bottombound = split * 200 / max(b1[3], 1)
    topbound = 200 - 200 * (200 - split) / (200 - max(1, b2[1]))
    return [[0, 0, 200, bottombound], [0, topbound, 200, 200]]


def mm_hor3(b1, b2, b3):
    """⿲ 分支 (ids_anal.py 372-396) 的算式部分"""
    w1, w2, w3 = b1[2] - b1[0], b2[2] - b2[0], b3[2] - b3[0]
    w1, w2, w3 = minmax(5, w1, 195), minmax(5, w2, 195), minmax(5, w3, 195)
    split1 = 1 + 199 * w1 / (w1 + w2 + w3)
    split2 = 199 - 199 * w3 / (w1 + w2 + w3)
    split1, split2 = minmax(2, split1, 90), minmax(110, split2, 198)
    leftbound = split1 * 200 / max(b1[2], 1)
    rightbound = 200 - 200 * (200 - split2) / (200 - max(1, b3[0]))
    k_c = (split2 - split1) / (b2[2] - b2[0])          # Python 原样: 可以除零
    centerbound1 = split1 - b2[0] * k_c
    centerbound2 = split2 + (200 - b2[2]) * k_c
    return [[0, 0, leftbound, 200], [centerbound1, 0, centerbound2, 200],
            [rightbound, 0, 200, 200]]


def mm_ver3(b1, b2, b3):
    """⿳ 分支 (ids_anal.py 398-421) 的算式部分"""
    h1, h2, h3 = b1[3] - b1[1], b2[3] - b2[1], b3[3] - b3[1]
    h1, h2, h3 = minmax(5, h1, 195), minmax(5, h2, 195), minmax(5, h3, 195)
    split1 = 1 + 199 * h1 / (h1 + h2 + h3)
    split2 = 199 - 199 * h3 / (h1 + h2 + h3)
    split1, split2 = minmax(2, split1, 90), minmax(110, split2, 198)
    topbound = split1 * 200 / max(b1[3], 1)
    bottombound = 200 - 200 * (200 - split2) / (200 - max(1, b3[1]))
    k_c = (split2 - split1) / (b2[3] - b2[1])
    centerbound1 = split1 - b2[1] * k_c
    centerbound2 = split2 + (200 - b2[3]) * k_c
    return [[0, 0, 200, topbound], [0, centerbound1, 200, centerbound2],
            [0, bottombound, 200, 200]]


EMPTY = (200.0, 200.0, 0.0, 0.0)   # ids_anal.bbox 的失败返回值


def rand_box(rng):
    r = rng.random()
    if r < 0.10:
        return EMPTY
    if r < 0.16:                                  # 零宽/零高
        x = rng.uniform(0, 200)
        y = rng.uniform(0, 200)
        if rng.random() < 0.5:
            return (x, y, x, rng.uniform(0, 200))
        return (x, y, rng.uniform(0, 200), y)
    if r < 0.22:                                  # 倒置
        x1, x2 = rng.uniform(0, 200), rng.uniform(0, 200)
        y1, y2 = rng.uniform(0, 200), rng.uniform(0, 200)
        return (max(x1, x2), max(y1, y2), min(x1, x2), min(y1, y2))
    if r < 0.30:                                  # 越界
        x1 = rng.uniform(-60, 60)
        x2 = rng.uniform(140, 260)
        y1 = rng.uniform(-60, 60)
        y2 = rng.uniform(140, 260)
        return (x1, y1, x2, y2)
    if r < 0.45:                                  # 贴边/极端扁窄
        return (0.0, rng.uniform(0, 190), rng.uniform(1, 12), 200.0)
    x1 = rng.uniform(0, 150)
    y1 = rng.uniform(0, 150)
    return (x1, y1, rng.uniform(x1, 200), rng.uniform(y1, 200))


OPS = [("⿰", 2, mm_hor), ("⿱", 2, mm_ver),
       ("⿲", 3, mm_hor3), ("⿳", 3, mm_ver3)]

rng = random.Random(20260214)
recs = []
per_op = 900
for op, n, fn in OPS:
    for _ in range(per_op):
        boxes = [rand_box(rng) for _ in range(n)]
        try:
            rects = fn(*boxes)
        except ZeroDivisionError:      # Python 原样会崩的输入, 记下来单独对齐
            recs.append({"op": op, "boxes": [list(b) for b in boxes],
                         "rects": None})
            continue
        recs.append({"op": op, "boxes": [list(b) for b in boxes],
                     "rects": [[float(v) for v in r] for r in rects]})

out_path = r"D:\2026harucpp\web\analysis\formula_ref.json"
json.dump({"cases": recs}, open(out_path, "w", encoding="utf-8"),
          ensure_ascii=False, indent=0)
n_div = sum(1 for r in recs if r["rects"] is None)
print(f"写出 {len(recs)} 例 (其中 {n_div} 例 Python 端除零) → {out_path}")
