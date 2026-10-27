# -*- coding: utf-8 -*-
"""在 kage-bundle.js 里定位 type 2/3/4 笔画的中心线生成算法"""
import sys, io, re, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

P = r"D:\2026harucpp\scripts\kage-bundle.js"
src = open(P, encoding="utf-8").read()
lines = src.split("\n")
print(f"{P}")
print(f"  {len(src):,} chars, {len(lines):,} lines\n")

# ---- 1. 文件里都有哪些函数 ----
print("=== 函数定义 (含 curve / bezier / stroke / draw 关键字) ===")
pat = re.compile(r"(?:function\s+([A-Za-z_$][\w$]*)|([A-Za-z_$][\w$]*)\.prototype\.([A-Za-z_$][\w$]*)\s*=)")
seen = set()
for i, ln in enumerate(lines):
    for m in pat.finditer(ln):
        nm = m.group(1) or (m.group(2) + "." + m.group(3))
        if nm in seen:
            continue
        seen.add(nm)
        if re.search(r"curve|bezier|stroke|draw|line|type", nm, re.I):
            print(f"  L{i+1:<6} {nm}")
print(f"  (共 {len(seen)} 个函数/方法)")

# ---- 2. 笔画类型的分派点 ----
print("\n=== 笔画类型分派 (case / 比较) ===")
for i, ln in enumerate(lines):
    if re.search(r"\bcase\s*[1-7]\b", ln) or re.search(r"(?:type|kind|linetype)\s*[=!]=\s*[1-7]\b", ln):
        print(f"  L{i+1:<6} {ln.strip()[:150]}")

# ---- 3. curve 相关代码块 ----
print("\n=== 含 'curve'/'bezier' 的行 ===")
for i, ln in enumerate(lines):
    if re.search(r"curve|bezier", ln, re.I):
        print(f"  L{i+1:<6} {ln.strip()[:160]}")
