# -*- coding: utf-8 -*-
"""
EDA 4: 用"目标矩形真值"重洗 — 设计者真正设定的 type-99 矩形重叠,
       而不是视觉笔画 bbox 重叠 (后者被部件内部空白污染)

真值: rect_overlap = ref_left.x2 - ref_right.x1
自变量: 左部件右缘竖直度 / 右部件左缘竖直度
"""
import sys, io, json, time
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 220)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"
BAND = 12.0


def collect_strokes(data, db, rect=(0, 0, 200, 200), visited=None, depth=0):
    if visited is None:
        visited = set()
    if depth > 12:
        return []
    rx1, ry1, rx2, ry2 = rect
    rw, rh = rx2 - rx1, ry2 - ry1
    out = []
    for seg in data.split("$"):
        seg = seg.strip()
        if not seg:
            continue
        p = seg.split(":")
        try:
            kind = int(p[0])
        except ValueError:
            continue
        if kind == 99 and len(p) >= 8:
            name = p[7].split("@")[0]
            try:
                bx1, by1, bx2, by2 = int(p[3]), int(p[4]), int(p[5]), int(p[6])
            except ValueError:
                continue
            if name in db and name not in visited:
                visited.add(name)
                for k, pts in collect_strokes(db[name], db, (bx1, by1, bx2, by2), visited, depth + 1):
                    out.append((k, [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
        elif kind in (1, 2, 3, 4, 6, 7):
            pts = []
            for i in range(3, len(p) - 1, 2):
                try:
                    pts.append((int(p[i]), int(p[i + 1])))
                except ValueError:
                    pass
            if pts:
                out.append((kind, [(rx1 + (x / 200.0) * rw, ry1 + (y / 200.0) * rh) for x, y in pts]))
    return out


def edge_vert(strokes, band=BAND):
    """返回 (右缘竖直度, 左缘竖直度) — 触边界笔画中竖笔的 y 覆盖/高度"""
    if not strokes:
        return None
    xs = [x for _, pts in strokes for x, _ in pts]
    ys = [y for _, pts in strokes for _, y in pts]
    x1, x2, y1, y2 = min(xs), max(xs), min(ys), max(ys)
    hh = max(y2 - y1, 1.0)
    rv = lv = 0.0
    for _, pts in strokes:
        px = [q[0] for q in pts]
        py = [q[1] for q in pts]
        dx, dy = max(px) - min(px), max(py) - min(py)
        if dy <= dx:
            continue
        if max(px) >= x2 - band:
            rv += dy
        if min(px) <= x1 + band:
            lv += dy
    return (rv / hh, lv / hh)


def top_refs(data):
    """顶层 type-99 引用: [(x1,y1,x2,y2,name), ...]"""
    refs = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            try:
                refs.append((int(p[3]), int(p[4]), int(p[5]), int(p[6]), p[7]))
            except ValueError:
                pass
    return refs


def names_for_char(ch):
    cp = ord(ch)
    return [f"u{cp:x}", f"u{cp:x}-j", f"u{cp:x}-k", f"u{cp:x}-v"]


def main():
    t0 = time.time()
    db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
    print(f"core_glyphs: {len(db)} ({time.time()-t0:.1f}s)")

    df = pd.read_csv(CSV, encoding="utf-8-sig")
    hh = df[df["op"] == "⿰"]
    chars = sorted(set(hh["char"].astype(str)))
    print(f"⿰ 唯一字: {len(chars)}")

    vcache = {}
    def vert(name):
        if name in vcache:
            return vcache[name]
        data = db.get(name) or db.get(name.split("@")[0])
        r = edge_vert(collect_strokes(data, db)) if data else None
        vcache[name] = r
        return r

    rows = []
    skip = {"no_char_data": 0, "not_two_refs": 0, "no_vert": 0, "not_ok": 0}

    for ch in chars:
        cdata = None
        for nm in names_for_char(ch):
            if nm in db:
                cdata = db[nm]
                break
        if cdata is None:
            skip["no_char_data"] += 1
            continue
        refs = top_refs(cdata)
        if len(refs) != 2:
            skip["not_two_refs"] += 1
            continue
        refs.sort(key=lambda r: r[0])          # 按 x1 排: 左 → 右
        (lx1, ly1, lx2, ly2, ln), (rx1, ry1, rx2, ry2, rn) = refs

        fl = vert(ln)
        fr = vert(rn)
        if fl is None or fr is None:
            skip["no_vert"] += 1
            continue

        rect_overlap = lx2 - rx1                  # 设计者设定的矩形重叠
        rows.append({
            "char": ch, "L": ln, "R": rn,
            "rect_overlap": rect_overlap,
            "L_rect_w": lx2 - lx1, "R_rect_w": rx2 - rx1,
            "L_right_v": fl[0], "L_left_v": fl[1],
            "R_right_v": fr[0], "R_left_v": fr[1],
            "L_gap_in_rect": 200 - lx2,           # 左部件矩形右侧空白? (通常0)
            "sum_rect_w": (lx2 - lx1) + (rx2 - rx1),
        })

    d = pd.DataFrame(rows)
    print(f"有效: {len(d)}  跳过: {skip}\n")
    if len(d) == 0:
        return

    d.to_csv(r"D:\2026harucpp\web\analysis\rect_truth.csv", index=False, encoding="utf-8-sig")

    print("=" * 74)
    print("0. 矩形重叠真值的分布")
    print("=" * 74)
    o = d["rect_overlap"]
    print(f"  n={len(o)} mean={o.mean():.2f} std={o.std():.2f} median={o.median():.2f}")
    print("  分位: " + "  ".join(f"p{q}={np.percentile(o,q):.0f}" for q in [1, 5, 25, 50, 75, 95, 99]))
    print(f"  整数占比: {(o == o.round()).mean()*100:.1f}%")
    print(f"  最常见值: {o.value_counts().head(8).to_dict()}")

    print()
    print("=" * 74)
    print("1. 相关性 (干净真值)")
    print("=" * 74)
    print(f"  corr(rect_overlap, L_right_v) = {d['rect_overlap'].corr(d['L_right_v']):+.3f}")
    print(f"  corr(rect_overlap, R_left_v)  = {d['rect_overlap'].corr(d['R_left_v']):+.3f}")
    print(f"  corr(rect_overlap, L_right_v + R_left_v) = "
          f"{d['rect_overlap'].corr(d['L_right_v'] + d['R_left_v']):+.3f}")
    print(f"  corr(rect_overlap, L_rect_w) = {d['rect_overlap'].corr(d['L_rect_w']):+.3f}")
    print(f"  corr(rect_overlap, R_rect_w) = {d['rect_overlap'].corr(d['R_rect_w']):+.3f}")

    print()
    print("=" * 74)
    print("2. 分箱: 两侧竖度之和 → 矩形重叠")
    print("=" * 74)
    d["vsum"] = d["L_right_v"] + d["R_left_v"]
    d["vbin"] = pd.cut(d["vsum"], [-0.01, 0.15, 0.4, 0.7, 1.0, 5],
                       labels=["0-0.15", "0.15-0.4", "0.4-0.7", "0.7-1.0", ">1.0"])
    print(f"  {'竖度和':<10} {'n':>7} {'均值':>9} {'std':>8} {'中位':>8}")
    for b, g in d.groupby("vbin", observed=True):
        print(f"  {str(b):<10} {len(g):>7} {g['rect_overlap'].mean():>9.2f} "
              f"{g['rect_overlap'].std():>8.2f} {g['rect_overlap'].median():>8.1f}")

    print()
    print("=" * 74)
    print("3. 四象限 (阈值 0.35)")
    print("=" * 74)
    print(f"  {'左缘竖':<7} {'右缘竖':<7} {'n':>7} {'矩形重叠均值':>13} {'std':>8} {'中位':>8}")
    for lv in [False, True]:
        for rv in [False, True]:
            s = d[((d["L_right_v"] > 0.35) == lv) & ((d["R_left_v"] > 0.35) == rv)]
            if len(s) < 5:
                continue
            print(f"  {('高' if lv else '低'):<7} {('高' if rv else '低'):<7} {len(s):>7} "
                  f"{s['rect_overlap'].mean():>13.2f} {s['rect_overlap'].std():>8.2f} "
                  f"{s['rect_overlap'].median():>8.1f}")

    print()
    print("=" * 74)
    print("4. 典型部件对的矩形重叠 (验证语义)")
    print("=" * 74)
    for a, b in [("口", "口"), ("口", "木"), ("氵", "工"), ("木", "木"),
                 ("日", "月"), ("扌", "土"), ("亻", "尔"), ("纟", "工"),
                 ("讠", "十"), ("土", "土"), ("石", "马"), ("女", "子")]:
        s = d[(d["L"].str.startswith(f"u{ord(a):x}")) & (d["R"].str.startswith(f"u{ord(b):x}"))]
        if len(s) == 0:
            continue
        print(f"  ⿰{a}{b}: n={len(s):<4} 矩形重叠 mean={s['rect_overlap'].mean():>6.1f} "
              f"| L右缘竖={s['L_right_v'].mean():.2f} R左缘竖={s['R_left_v'].mean():.2f}")


if __name__ == "__main__":
    main()
