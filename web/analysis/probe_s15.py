# -*- coding: utf-8 -*-
"""-15 到底是不是垃圾桶? 把 38 条全列出来, 和 -05 / 本体比

看三件事:
  ① data 形状: 单条"全幅引用"(= 整字原样) 还是多笔"框架"
  ② 和本体(不带后缀)的笔画数、外框对比
  ③ 和 -05 的对比 (同时有 -05 和 -15 的字头)
"""
import sys, io, re, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
import glyph_extend, stroke_outer

buf = io.StringIO()
KINDS = ("1", "2", "3", "4", "6", "7")
PAT = re.compile(r"^(u[0-9a-f]+)(?:-(\d+))?$")


def nstroke(data):
    return sum(1 for s in data.split("$") if s.split(":")[0] in KINDS)


def nref(data):
    return sum(1 for s in data.split("$") if s.split(":")[0] == "99")


def bbox(data):
    boxes = []
    for s in data.split("$"):
        if s.split(":")[0] not in KINDS:
            continue
        try:
            with contextlib.redirect_stdout(buf):
                b = stroke_outer.strokic_boundary(s, False)
        except Exception:
            continue
        if b.x2 > b.x1 and b.y2 > b.y1:
            boxes.append((b.x1, b.y1, b.x2, b.y2))
    if not boxes:
        return None
    return (round(min(b[0] for b in boxes), 1), round(min(b[1] for b in boxes), 1),
            round(max(b[2] for b in boxes), 1), round(max(b[3] for b in boxes), 1))


def full_ref(data):
    """data 是不是单条全幅 99 引用"""
    segs = [s for s in data.split("$") if s]
    if len(segs) != 1 or not segs[0].startswith("99:"):
        return None
    p = segs[0].split(":")
    if len(p) < 8:
        return None
    r = [int(float(v)) for v in p[3:7]]
    if r == [0, 0, 200, 200]:
        return p[7].split("@")[0]
    return None


want = {}
for line in glyph_extend.dbs:
    cols = line.split(" | ")
    if len(cols) < 3:
        continue
    nm = cols[0].strip()
    m = PAT.match(nm)
    if m and m.group(2) in ("15", "05") or (m and not m.group(2)):
        want[nm] = cols[2].strip()

fifteen = {nm: d for nm, d in want.items() if nm.endswith("-15")}
print(f"=== -15 共 {len(fifteen)} 条 ===")
print(f"{'名字':14s} {'笔':>2s} {'引':>2s} {'-15 盒':>30s} {'本体笔':>5s} {'本体盒':>30s} {'-05':>4s}")
single_full = 0
for nm in sorted(fifteen):
    data = fifteen[nm]
    base = nm[:-3]
    fr = full_ref(data)
    if fr:
        single_full += 1
    b15 = bbox(data)
    bbase = bbox(want.get(base, "")) if base in want else None
    has05 = (base + "-05") in want
    b05 = bbox(want[base + "-05"]) if has05 else None
    print(f"{nm:14s} {nstroke(data):2d} {nref(data):2d} "
          f"{str(b15):>30s} {nstroke(want.get(base,'')):5d} {str(bbase):>30s} "
          f"{('有' if has05 else '-') + (str(b05) if b05 else ''):>30s}")
print(f"\n  其中'单条全幅引用 (= 整字原样)'的: {single_full}/{len(fifteen)}")
print("  同时有 -05 的字头:", sum(1 for nm in fifteen if nm[:-3] + "-05" in want))
