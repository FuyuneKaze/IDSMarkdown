#!/usr/bin/env python3
"""
分析 IDS 数据库中的叶子字形，统计核心字形集大小。
输出：
  1. IDS 表达式中引用的不同叶子字形数量
  2. dump 文件覆盖率
  3. type-99 传递依赖分析
  4. 核心字形集大小估算
"""
import sys, os, re, json
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
IDS_DIR = os.path.join(DATA_DIR, "ids")
IDS_FILES = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]

# Dump file path - adjust as needed
DUMP_PATH = r"D:\2026harucpp\19G252FuyuneKazec++高级语言程序设计\程序和数据\data\dump_newest_only.txt"

# IDS operators (U+2FF0-U+2FFF + U+31EF)
def is_ids_operator(cp):
    return (0x2FF0 <= cp <= 0x2FFF) or cp == 0x31EF

def is_surrogate(cp):
    return 0xD800 <= cp <= 0xDFFF

def is_variation_selector(cp):
    return 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF

def is_ids_annotation(cp):
    """IDS annotations like [X], (X), {X}"""
    return cp in (0x28, 0x29, 0x5B, 0x5D, 0x7B, 0x7D)  # () [] {}

# ---------- Step 1: Extract leaf characters from IDS files ----------
print("=" * 60)
print("Step 1: 提取 IDS 叶子字形")
print("=" * 60)

leaf_chars = set()  # Set of single characters
leaf_surrogates = set()  # Multi-codepoint sequences (for supplementary plane)
ids_count = 0
per_file_stats = {}

for fname in IDS_FILES:
    fpath = os.path.join(IDS_DIR, fname)
    if not os.path.exists(fpath):
        print(f"  SKIP {fname} (not found)")
        continue

    file_leaves = set()
    file_ids_count = 0
    with open(fpath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: char\tIDS[ \t variant...]
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            ids_str = parts[1]

            # Take first ;-separated variant
            ids_str = ids_str.split(";")[0]

            file_ids_count += 1

            # Walk through the IDS string, skip operators and annotations
            i = 0
            while i < len(ids_str):
                cp = ord(ids_str[i])

                # Handle surrogate pairs
                if 0xD800 <= cp <= 0xDBFF and i + 1 < len(ids_str):
                    lo = ord(ids_str[i+1])
                    if 0xDC00 <= lo <= 0xDFFF:
                        cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
                        if not is_ids_operator(cp) and not is_variation_selector(cp) and not is_ids_annotation(cp):
                            file_leaves.add(chr(cp))
                        i += 2
                        continue

                if not is_ids_operator(cp) and not is_variation_selector(cp) and not is_ids_annotation(cp) and cp not in (0x2E,):  # skip . position markers
                    file_leaves.add(ids_str[i])
                i += 1

    leaf_chars.update(file_leaves)
    per_file_stats[fname] = {"ids_count": file_ids_count, "unique_leaves": len(file_leaves)}
    ids_count += file_ids_count
    print(f"  {fname}: {file_ids_count} IDS 条目, {len(file_leaves)} 个不同叶子字形")

print(f"\n总计: {ids_count} 个 IDS 表达式, {len(leaf_chars)} 个不同叶子字形")

# Show some examples
print(f"\n叶子字形示例 (前30个):")
sample = sorted(leaf_chars)[:30]
for c in sample:
    cp = ord(c)
    print(f"  U+{cp:04X} {c}", end="")
print()

# ---------- Step 2: Convert leaf chars to glyph names ----------
print("\n" + "=" * 60)
print("Step 2: 叶子字形 → GlyphWiki 字形名")
print("=" * 60)

def char_to_glyph_names(c):
    """Convert a character to possible GlyphWiki glyph names."""
    names = []
    cp = ord(c)
    if cp >= 0x10000:
        names.append(f"u{cp:05x}")
    else:
        names.append(f"u{cp:04x}")
    return names

all_glyph_names = set()
for c in leaf_chars:
    for name in char_to_glyph_names(c):
        all_glyph_names.add(name)

print(f"基础字形名（去重后）: {len(all_glyph_names)}")

# ---------- Step 3: Check dump coverage ----------
print("\n" + "=" * 60)
print("Step 3: dump 文件覆盖率")
print("=" * 60)

dump_glyphs = {}  # name -> (related, data)
if os.path.exists(DUMP_PATH):
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
            related = parts[1].strip()
            data = parts[2].strip()
            dump_glyphs[name] = (related, data)

    print(f"dump 文件中共 {len(dump_glyphs)} 个字形")

    # Direct coverage
    covered = all_glyph_names & set(dump_glyphs.keys())
    not_covered = all_glyph_names - set(dump_glyphs.keys())
    print(f"叶子字形直接覆盖: {len(covered)}/{len(all_glyph_names)} ({100*len(covered)/len(all_glyph_names):.1f}%)")
    print(f"未覆盖: {len(not_covered)} 个")

    if not_covered:
        print(f"\n未覆盖示例 (前20个):")
        for name in sorted(not_covered)[:20]:
            print(f"  {name}", end="")
        print()

    # ---------- Step 4: Type-99 dependency analysis ----------
    print("\n" + "=" * 60)
    print("Step 4: type-99 传递依赖分析")
    print("=" * 60)

    def extract_type99_refs(data):
        """Extract all type-99 glyph references from KAGE data."""
        refs = set()
        if not data:
            return refs
        for stroke in data.split("$"):
            if stroke.startswith("99:"):
                parts = stroke.split(":")
                if len(parts) >= 8:
                    ref = parts[7]
                    # Remove version suffix like @2
                    ref = ref.split("@")[0]
                    refs.add(ref)
        return refs

    # Analyze: for each covered leaf, what's the full dependency closure?
    sample_size = min(500, len(covered))
    sample_covered = list(covered)[:sample_size]

    total_deps = set()
    max_depth = 0
    dep_chain_examples = []

    for name in sample_covered:
        visited = set()
        queue = [name]
        depth = 0
        while queue and depth < 10:  # safety limit
            next_queue = []
            for n in queue:
                if n in visited:
                    continue
                visited.add(n)
                if n in dump_glyphs:
                    _, data = dump_glyphs[n]
                    refs = extract_type99_refs(data)
                    next_queue.extend(refs)
            queue = next_queue
            if queue:
                depth += 1

        dep_count = len(visited) - 1  # exclude self
        total_deps.update(visited)
        if depth > max_depth:
            max_depth = depth
        if len(dep_chain_examples) < 5:
            dep_chain_examples.append((name, len(visited), depth))

    print(f"样本 {sample_size} 个叶子字形的传递依赖:")
    print(f"  总涉及不同字形: {len(total_deps)}")
    print(f"  最大递归深度: {max_depth}")
    print(f"  平均每个叶子依赖: {len(total_deps)/sample_size:.1f} 个字形")

    print(f"\n依赖链示例:")
    for name, total, depth in dep_chain_examples:
        print(f"  {name}: {total} 个字形, 深度 {depth}")

    # Now estimate total core set
    print("\n" + "=" * 60)
    print("Step 5: 核心字形集大小估算")
    print("=" * 60)

    # Full analysis: for ALL covered leaves, compute dependency closure
    # We'll estimate from the sample
    estimate_factor = len(total_deps) / sample_size
    estimated_total = int(len(all_glyph_names) * estimate_factor)
    print(f"基于样本估算: {estimated_total} 个字形（包含依赖）")

    # Actually, let's compute the real dependency closure for all covered leaves
    # But limit to a reasonable time
    print("\n正在计算全量传递依赖（所有已覆盖叶子）...")
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
                _, data = dump_glyphs[n]
                for ref in extract_type99_refs(data):
                    queue.append(ref)
        all_deps.update(visited)
        processed += 1
        if processed % 1000 == 0:
            print(f"  已处理 {processed}/{len(covered)}... 当前 {len(all_deps)} 个字形")

    print(f"\n核心字形集（叶子 + 传递依赖）: {len(all_deps)} 个不同字形")
    print(f"覆盖叶子字形 {len(covered)} 个")
    print(f"附加依赖字形 {len(all_deps) - len(covered)} 个")

    # Estimate JSON size
    total_data_size = 0
    sampled_count = 0
    for name in list(all_deps)[:1000]:
        if name in dump_glyphs:
            _, data = dump_glyphs[name]
            total_data_size += len(data)
            sampled_count += 1

    if sampled_count > 0:
        avg_size = total_data_size / sampled_count
        estimated_total_size = int(avg_size * len(all_deps))
        print(f"\n预估 JSON 大小:")
        print(f"  平均每个字形 {avg_size:.0f} 字节")
        print(f"  原始大小: ~{estimated_total_size / 1024 / 1024:.1f} MB")
        print(f"  gzip 后 (文本 ~5:1 压缩): ~{estimated_total_size / 1024 / 1024 / 5:.1f} MB")

    # Output a report summary
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"IDS 数据库: {ids_count} 个表达式")
    print(f"不同叶子字形: {len(leaf_chars)}")
    print(f"dump 覆盖率: {len(covered)}/{len(all_glyph_names)} ({100*len(covered)/len(all_glyph_names):.1f}%)")
    print(f"核心字形集（含依赖）: {len(all_deps)} 个")
    print(f"未覆盖叶子: {len(not_covered)} 个")

    if len(not_covered) > 0:
        print(f"\n未覆盖字形示例:")
        for name in sorted(not_covered)[:30]:
            print(f"  {name}", end="")
        print()

else:
    print(f"dump 文件未找到: {DUMP_PATH}")
    print("请确认路径后重试")
