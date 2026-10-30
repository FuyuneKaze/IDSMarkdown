#!/usr/bin/env python3
"""
从 dump 文件中提取核心字形集（~27K 字形），输出为单个 JSON 文件。

输入：dump_newest_only.txt（~333MB）
输出：core_glyphs.json（~1.6MB）

用法：python extract_core_glyphs.py
"""
import sys, os, re, json
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
# IDS 表只有一份, 在 web/public/ (运行时也要从这里取); data/ids/ 仅留 ts.txt
IDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "web", "public")
_fallback = os.path.join(DATA_DIR, "ids")
if not os.path.exists(os.path.join(IDS_DIR, "ids_lv0.txt")):
    IDS_DIR = _fallback
OUTPUT = os.path.join(DATA_DIR, "core_glyphs.json")

DUMP_PATH = os.environ.get("KAGE_DUMP", r"D:\KAGE_GLYPH\dump_newest_only.txt")

def is_ids_operator(cp):
    return (0x2FF0 <= cp <= 0x2FFF) or cp == 0x31EF

# Step 1: Extract leaf chars from IDS files
print("提取 IDS 叶子字形...")
leaf_chars = set()
for fname in ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]:
    fpath = os.path.join(IDS_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            ids_str = parts[1].split(";")[0]
            i = 0
            while i < len(ids_str):
                cp = ord(ids_str[i])
                if 0xD800 <= cp <= 0xDBFF and i + 1 < len(ids_str):
                    lo = ord(ids_str[i+1])
                    if 0xDC00 <= lo <= 0xDFFF:
                        cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
                        if not is_ids_operator(cp) and not (0xFE00 <= cp <= 0xFE0F):
                            leaf_chars.add(ids_str[i:i+2])
                        i += 2
                        continue
                if not is_ids_operator(cp) and cp != 0x2E:
                    leaf_chars.add(ids_str[i])
                i += 1

# Convert to glyph names
all_names = set()
for c in leaf_chars:
    cp = ord(c) if len(c) == 1 else 0x10000 + (ord(c[0]) - 0xD800) * 0x400 + (ord(c[1]) - 0xDC00)
    if cp >= 0x10000:
        all_names.add(f"u{cp:05x}")
    else:
        all_names.add(f"u{cp:04x}")

print(f"  叶子字形: {len(all_names)} 个基础名")

# Step 2: Load dump file, filter to relevant glyphs
print("加载 dump 文件...")
dump_glyphs = {}
with open(DUMP_PATH, "r", encoding="utf-8") as f:
    f.readline()  # header
    f.readline()  # separator
    for line in f:
        if not line.startswith(" u"):
            continue
        parts = line.split(" | ")
        if len(parts) < 3:
            continue
        name = parts[0].strip()
        data = parts[2].strip()
        # Only keep glyphs starting with u (skip a77uyh_abcde style names)
        if name.startswith("u"):
            dump_glyphs[name] = data

print(f"  dump 中 u* 字形: {len(dump_glyphs)} 个")

# Step 3: Compute transitive dependency closure
print("计算传递依赖...")

def extract_refs(data):
    refs = set()
    if not data:
        return refs
    for stroke in data.split("$"):
        if stroke.startswith("99:"):
            parts = stroke.split(":")
            if len(parts) >= 8:
                ref = parts[7].split("@")[0]
                refs.add(ref)
    return refs

covered = all_names & set(dump_glyphs.keys())
print(f"  已覆盖叶子: {len(covered)}/{len(all_names)}")

all_deps = set()
processed = 0
for name in covered:
    visited = set()
    queue = [name]
    while queue:
        n = queue.pop()
        if n in visited:
            continue
        visited.add(n)
        if n in dump_glyphs:
            for ref in extract_refs(dump_glyphs[n]):
                if ref.startswith("u"):
                    queue.append(ref)
    all_deps.update(visited)
    processed += 1
    if processed % 2000 == 0:
        print(f"    {processed}/{len(covered)}... {len(all_deps)} 个字形")

print(f"  核心字形总计: {len(all_deps)} 个")

# Step 4: Build output JSON
print("构建输出...")
core_data = {}
for name in all_deps:
    if name in dump_glyphs:
        core_data[name] = dump_glyphs[name]

output = {
    "description": "IDS editor core glyph set",
    "glyph_count": len(core_data),
    "glyphs": core_data,
}

# Write compact JSON
print(f"写入 {OUTPUT}...")
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(",", ":"))

file_size = os.path.getsize(OUTPUT)
print(f"\n完成！")
print(f"  字形数: {len(core_data)}")
print(f"  文件大小: {file_size / 1024 / 1024:.2f} MB")
print(f"  输出: {OUTPUT}")
