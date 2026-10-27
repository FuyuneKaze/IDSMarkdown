# -*- coding: utf-8 -*-
"""
EDA 8: 用"变体名精确匹配"提取矩形真值 (修正 EDA 4 的失败)

上次失败原因: 取"顶层两个 type-99", 但像"国"是"全画布外框+内部件",
             把外框(0..200)当成了部件 → rect_overlap 均值 126 (荒谬)。

本次: 用 composition_v3.csv 的 c1_variant/c2_variant 精确匹配到目标矩形,
      并沿嵌套链把矩形坐标累积映射到顶层坐标系。
"""
import sys, io, json, time
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
pd.set_option("display.width", 240)

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"


def find_ref_rects(data, db, targets, rect=(0.0, 0.0, 200.0, 200.0),
                   visited=None, depth=0):
    """递归查找 targets 中变体名对应的目标矩形, 映射到 rect 坐标系"""
    if visited is None:
        visited = set()
    if depth > 14:
        return {}
    rx1, ry1, rx2, ry2 = rect
    rw, rh = rx2 - rx1, ry2 - ry1
    found = {}

    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] != "99" or len(p) < 8:
            continue
        name = p[7].split("@")[0]
        try:
            bx1, by1, bx2, by2 = int(p[3]), int(p[4]), int(p[5]), int(p[6])
        except ValueError:
            continue

        # 该引用的目标矩形 (映射到顶层坐标系)
        mx1 = rx1 + bx1 / 200.0 * rw
        my1 = ry1 + by1 / 200.0 * rh
        mx2 = rx1 + bx2 / 200.0 * rw
        my2 = ry1 + by2 / 200.0 * rh

        if name in targets and name not in found:
            found[name] = (mx1, my1, mx2, my2)

        if name in db and name not in visited and name not in targets:
            visited.add(name)
            # 子部件的 0-200 空间 对应顶层范围 = 该引用的目标矩形(顶层坐标)
            sub = find_ref_rects(db[name], db, targets,
                                 (mx1, my1, mx2, my2), visited, depth + 1)
            for k, r in sub.items():
                if k not in found:
                    found[k] = r          # sub 已是顶层坐标, 不再二次映射
    return found


def names_for_char(ch):
    cp = ord(ch)
    return [f"u{cp:x}", f"u{cp:x}-j", f"u{cp:x}-k", f"u{cp:x}-v"]


def main():
    t0 = time.time()
    db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
    print(f"core_glyphs: {len(db)} ({time.time()-t0:.1f}s)")

    src = pd.read_csv(CSV, encoding="utf-8-sig")
    h = src[src["op"] == "⿰"].dropna(subset=["c1_str_x1", "c1_str_x2", "c2_str_x1", "c2_str_x2"]).copy()
    h = h.dropna(subset=["c1_variant", "c2_variant"])
    h = h[(h["c1_variant"].astype(str).str.len() > 0) &
          (h["c2_variant"].astype(str).str.len() > 0)].copy()
    h["vis_overlap"] = h["c1_str_x2"] - h["c2_str_x1"]
    h = h.reset_index(drop=True)
    print(f"⿰ 样本: {len(h)}")

    rows = []
    miss = 0
    for r in h.itertuples(index=False):
        cdata = None
        for nm in names_for_char(r.char):
            if nm in db:
                cdata = db[nm]
                break
        if cdata is None:
            miss += 1
            continue
        targets = {r.c1_variant, r.c2_variant}
        rects = find_ref_rects(cdata, db, targets)
        if r.c1_variant not in rects or r.c2_variant not in rects:
            miss += 1
            continue
        a = rects[r.c1_variant]
        b = rects[r.c2_variant]
        rows.append({
            "char": r.char, "c1": r.c1_char, "c2": r.c2_char,
            "vis_overlap": r.vis_overlap,
            "Lrect_x1": a[0], "Lrect_x2": a[2], "Lrect_w": a[2] - a[0],
            "Rrect_x1": b[0], "Rrect_x2": b[2], "Rrect_w": b[2] - b[0],
            "rect_overlap": a[2] - b[0],
        })
    d = pd.DataFrame(rows)
    print(f"有效: {len(d)}  未匹配: {miss}\n")
    if len(d) == 0:
        return
    d.to_csv(r"D:\2026harucpp\web\analysis\rect_truth2.csv", index=False, encoding="utf-8-sig")

    print("=" * 78)
    print("0. 矩形重叠真值分布 (修正后)")
    print("=" * 78)
    o = d["rect_overlap"]
    print(f"  n={len(o)} mean={o.mean():.2f} std={o.std():.2f} median={o.median():.2f}")
    print("  分位: " + "  ".join(f"p{q}={np.percentile(o,q):.0f}" for q in [1, 5, 25, 50, 75, 95, 99]))
    print(f"  整数占比: {(o == o.round()).mean()*100:.1f}%")
    print(f"  最常见值: {o.round().value_counts().head(8).to_dict()}")
    print(f"\n  与视觉重叠的相关: {o.corr(d['vis_overlap']):+.3f}")

    # 合并边缘特征
    ef = pd.read_csv(r"D:\2026harucpp\web\analysis\cond_features.csv", encoding="utf-8-sig")
    d = d.merge(ef[["char", "L_rv", "R_lv", "seg_ov"]].drop_duplicates("char"),
                on="char", how="left")
    d = d.dropna(subset=["L_rv"])
    print(f"  合并边缘特征后: {len(d)}")

    print()
    print("=" * 78)
    print("1. 相关性 (矩形真值 vs 视觉重叠真值)")
    print("=" * 78)
    print(f"  {'自变量':<16} {'vs 矩形重叠':>14} {'vs 视觉重叠':>14}")
    for c in ["L_rv", "R_lv", "seg_ov", "Lrect_w", "Rrect_w"]:
        if c not in d:
            continue
        print(f"  {c:<16} {d['rect_overlap'].corr(d[c]):>14.3f} {d['vis_overlap'].corr(d[c]):>14.3f}")

    print()
    print("=" * 78)
    print("2. 二维规律表: 矩形重叠 均值")
    print("=" * 78)
    Lb, Rb = [0, 0.15, 0.5, 1.01], [0, 0.15, 0.5, 1.01]
    Llab = ["L低(0-.15)", "L中(.15-.5)", "L高(.5-1)"]
    Rlab = ["R低(0-.15)", "R中(.15-.5)", "R高(.5-1)"]
    print(f"  {'':<13}" + "".join(f"{x:>20}" for x in Rlab))
    for i in range(3):
        row = f"  {Llab[i]:<13}"
        for j in range(3):
            s = d[(d["L_rv"] >= Lb[i]) & (d["L_rv"] < Lb[i+1]) &
                  (d["R_lv"] >= Rb[j]) & (d["R_lv"] < Rb[j+1])]
            row += f"{'--':>20}" if len(s) < 20 else f"{s['rect_overlap'].mean():>9.1f} (n={len(s):<6})"
        print(row)

    print()
    print("=" * 78)
    print("3. L_rv 分档 → 矩形重叠 (一维规律)")
    print("=" * 78)
    print(f"  {'L_rv':<14} {'n':>7} {'矩形重叠':>10} {'std':>8} {'中位':>8}")
    for lo, hi in [(0, 0.05), (0.05, 0.2), (0.2, 0.5), (0.5, 0.8), (0.8, 1.01)]:
        g = d[(d["L_rv"] >= lo) & (d["L_rv"] < hi)]
        if len(g) < 20:
            continue
        print(f"  [{lo:.2f}, {hi:.2f})    {len(g):>7} {g['rect_overlap'].mean():>10.2f} "
              f"{g['rect_overlap'].std():>8.2f} {g['rect_overlap'].median():>8.1f}")

    print()
    print("=" * 78)
    print("4. 偏相关 (矩形真值下重新检验 confound)")
    print("=" * 78)
    def pc(a, b, c):
        rab, rac, rbc = a.corr(b), a.corr(c), b.corr(c)
        den = np.sqrt((1 - rac**2) * (1 - rbc**2))
        return (rab - rac * rbc) / den if den > 1e-12 else np.nan

    print(f"  corr(rect_ov, L_rv)            = {d['rect_overlap'].corr(d['L_rv']):+.3f}")
    print(f"  corr(rect_ov, Lrect_w)         = {d['rect_overlap'].corr(d['Lrect_w']):+.3f}")
    print(f"  corr(rect_ov, L_rv | Lrect_w)  = {pc(d['rect_overlap'], d['L_rv'], d['Lrect_w']):+.3f}")
    print(f"  corr(rect_ov, R_lv)            = {d['rect_overlap'].corr(d['R_lv']):+.3f}")
    print(f"  corr(rect_ov, seg_ov)          = {d['rect_overlap'].corr(d['seg_ov']):+.3f}")


if __name__ == "__main__":
    main()
