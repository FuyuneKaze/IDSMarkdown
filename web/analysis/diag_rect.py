# -*- coding: utf-8 -*-
"""诊断: 直接打印具体字的原始数据与矩形匹配结果, 人工核对"""
import sys, io, json
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CORE = r"D:\2026harucpp\web\public\core_glyphs.json"
CSV = r"D:\2026harucpp\scripts\output\composition_v3.csv"

db = json.load(open(CORE, encoding="utf-8"))["glyphs"]
h = pd.read_csv(CSV, encoding="utf-8-sig")
h = h[h["op"] == "⿰"]


def names_for_char(ch):
    cp = ord(ch)
    return [f"u{cp:x}", f"u{cp:x}-j", f"u{cp:x}-k", f"u{cp:x}-v"]


def refs_of(data):
    out = []
    for seg in data.split("$"):
        p = seg.strip().split(":")
        if p[0] == "99" and len(p) >= 8:
            out.append((p[3], p[4], p[5], p[6], p[7]))
    return out


for ch in ["明", "林", "江", "好", "时", "们", "休", "clearly"[:0] or "村"]:
    sub = h[h["char"] == ch]
    if len(sub) == 0:
        print(f"\n### {ch}: CSV 中无此行")
        continue
    row = sub.iloc[0]
    name = None
    data = None
    for nm in names_for_char(ch):
        if nm in db:
            name, data = nm, db[nm]
            break
    print(f"\n{'='*76}")
    print(f"### {ch}   (字形键={name})")
    print(f"  CSV: c1={row['c1_variant']!r} c2={row['c2_variant']!r}  "
          f"(字符 {row['c1_char']} / {row['c2_char']})")
    print(f"  CSV vis: c1_str_x2={row['c1_str_x2']} c2_str_x1={row['c2_str_x1']} "
          f"→ vis_overlap={row['c1_str_x2'] - row['c2_str_x1']:.1f}")
    if data is None:
        print("  !! core_glyphs 中找不到该字")
        continue
    print(f"  原始数据: {data[:220]}")
    print(f"  顶层 type-99 引用:")
    for r in refs_of(data):
        x1, y1, x2, y2, nm = r
        mark = ""
        if nm in (str(row["c1_variant"]), str(row["c2_variant"])):
            mark = "  <== 匹配 CSV"
        print(f"    rect=({x1},{y1},{x2},{y2})  name={nm}{mark}")
