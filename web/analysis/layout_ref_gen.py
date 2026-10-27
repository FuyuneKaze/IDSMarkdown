# -*- coding: utf-8 -*-
"""
生成"分配算式"的参考数据 + 一份迷你字形库(供 TS 侧注入)

手法: spy 住 glyph_extend.trans, 记录 ids_anal.IDS 实际传给它的矩形 geom[0]。
      不改动任何项目文件。
"""
import sys, io, json, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

# 借 preview 的索引: 它启动时建 name→data 索引并把 glyph_extend.get_data 换成
# _fast_get_data (官方文档说是"精确复刻三条通路")。裸 get_data 每次全表扫
# 248 万行 (命中 0.76s / 未命中 1.9s), 一例要查十几次 → 30 秒/例; 换索引后
# 整批从半小时变成几秒。注意它会把 glyph_extend.dbs 原地清空 (省内存)。
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview  # noqa: E402

import glyph_extend  # noqa: E402
import ids_anal  # noqa: E402

assert glyph_extend.get_data.__name__ == "_fast_get_data", \
    "preview 没有接管 get_data, 这批参考会用裸扫描跑几十分钟"

# ---- spy: trans(glyph, geom, tran) 里的 geom[0] 就是组件目标矩形 ----
_orig_trans = glyph_extend.trans
_calls = []


def _spy(glyph, geom, tran=(None, None)):
    _calls.append([str(v) for v in geom[0]])
    return _orig_trans(glyph, geom, tran)


glyph_extend.trans = _spy

SUFFIX = {
    "⿰": ["-01", "-02"],
    "⿱": ["-03", "-04"],
    "⿲": ["-01", "-01", "-02"],
    "⿳": ["-03", "-03", "-04"],
}

CASES = [
    ("⿰", ["u6c35", "u5de5"]),
    ("⿰", ["u6728", "u6728"]),
    ("⿰", ["u53e3", "u6728"]),
    ("⿰", ["u5fc4", "u5ffd"]),
    ("⿰", ["u65e5", "u6708"]),
    ("⿰", ["u4ebb", "u5c14"]),
    ("⿱", ["u5b80", "u4e01"]),
    ("⿱", ["u65e5", "u6728"]),
    ("⿱", ["u516b", "u5200"]),
    ("⿱", ["u7acb", "u65e5"]),
    ("⿱", ["u5c71", "u77f3"]),
    ("⿲", ["u6728", "u6728", "u6728"]),
    ("⿳", ["u4e00", "u53e3", "u4e00"]),
]

# ---- 自动扩样: 从常用部件池里随机组合, 覆盖各种笔数/引用/接缝结构 ----
POOL = [
    "u4eba", "u5165", "u516b", "u5200", "u529b", "u53c8", "u53e3", "u5927",
    "u5973", "u5b50", "u5b80", "u5c0f", "u5c38", "u5c71", "u5fc3", "u5fc4",
    "u5f73", "u5ffd", "u624b", "u6535", "u65e5", "u6708", "u6728", "u6c34",
    "u6c35", "u706b", "u738b", "u7530", "u76ee", "u77f3", "u79be", "u7acb",
    "u7af9", "u7c73", "u8033", "u8279", "u866b", "u8863", "u8ba0", "u8fb6",
    "u91d1", "u95e8", "u96e8", "u98df", "u9a6c", "u9c7c", "u5de5", "u5df2",
]

import random
_rng = random.Random(20260214)
for _ in range(28):
    a, b = _rng.sample(POOL, 2)
    CASES.append(("⿰", [a, b]))
for _ in range(24):
    a, b = _rng.sample(POOL, 2)
    CASES.append(("⿱", [a, b]))
for _ in range(8):
    a, b, c = _rng.sample(POOL, 3)
    CASES.append(("⿲", [a, b, c]))
for _ in range(8):
    a, b, c = _rng.sample(POOL, 3)
    CASES.append(("⿳", [a, b, c]))

mini_db = {}


def collect_closure(name, seen, exact=True):
    """把 name 及其引用闭包收进迷你库

    两条路径必须和引擎严格对齐, 否则迷你库里的数据和引擎查到的不是同一份:
      · 顶层叶子名 → exact=False (与 return_bone 的第一轮一致, 走"子串退化")
      · 字形内部的 99 引用 → exact=True (精确优先, 见 get_data 的说明)
    """
    if name in seen:
        return
    seen.add(name)
    data = glyph_extend.get_data(name, exact=exact)
    if not data:
        return
    mini_db[name] = data
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            collect_closure(p[7].split("@")[0], seen, exact=True)


recs = []
seen = set()
skipped = []
for op, args in CASES:
    print(f"[{len(recs)}] {op}{''.join(args)}", flush=True)
    sfx = SUFFIX[op]
    names = [args[k] + sfx[k] for k in range(len(args))]
    # 部件 bbox (ids_anal.bbox 的输入就是 return_bone 展平后的数据)
    boxes = []
    try:
        for nm in names:
            collect_closure(nm, seen, exact=False)   # 顶层叶子: 与 return_bone 一致
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                flat = glyph_extend.return_bone(nm)
            b = ids_anal.bbox(flat)
            boxes.append([round(float(v), 6) for v in b])

        _calls.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = ids_anal.IDS(op, list(args))
        rects = [[float(v) for v in r] for r in _calls]
    except Exception as e:  # noqa: BLE001
        skipped.append((op, tuple(args), f"{type(e).__name__}: {e}"))
        continue

    if not out or len(rects) != len(args) or len(boxes) != len(args):
        skipped.append((op, tuple(args), f"落空 out={bool(out)} rect={len(rects)} box={len(boxes)}"))
        continue

    recs.append({
        "op": op, "args": list(args), "leafNames": names,
        "boxes": boxes, "rects": rects,
        "ok": bool(out),
    })

out_path = r"D:\2026harucpp\web\analysis\layout_ref.json"
if skipped:
    print(f"跳过 {len(skipped)} 例:")
    for op, args, why in skipped:
        print(f"  - {op}{''.join(args)}: {why}")
json.dump({"cases": recs, "db": mini_db},
          open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"写出 {len(recs)} 个用例, 迷你库 {len(mini_db)} 条 → {out_path}")
print()
for r in recs:
    print(f"  {r['op']}{''.join(r['args'])}")
    for i, b in enumerate(r["boxes"]):
        print(f"      box{i} = [{b[0]:.2f}, {b[1]:.2f}, {b[2]:.2f}, {b[3]:.2f}]")
    for i, t in enumerate(r["rects"]):
        print(f"      rect{i}= [{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}, {t[3]:.2f}]")
