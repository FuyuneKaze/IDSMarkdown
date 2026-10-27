# -*- coding: utf-8 -*-
"""把带数字后缀的变体（-01…-15、-24）补进 web/public/core_glyphs.json

背景: 组成流程会用到 -01/-02（左右）、-03/-04（上下）、-05/-06（包围外框/内容物）、
-08/-09（纵横拉伸）、-10/-11/-15（按内容密度的包围外框）、-14/-24（下半边）。
原导出漏了 -05/-06 等，导致 ⿺辶鼻 取不到容器变体，只能退回本体。

用法:
    python web/analysis/patch_bundle.py            # 实际写入（先备份）
    python web/analysis/patch_bundle.py --dry-run  # 只报告
"""
import io, json, os, re, sys, shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
DUMP = r"D:/KAGE_GLYPH/dump_newest_only.txt"
BUNDLE = r"D:/2026harucpp/web/public/core_glyphs.json"
SUFFIXES = {f"{n:02d}" for n in list(range(1, 16)) + [24]}
NAME = re.compile(r"^(u[0-9a-f]+)-(\d+)$")
dry = "--dry-run" in sys.argv

# ① 从 dump 里挑出需要的变体
want = {}
with io.open(DUMP, encoding="utf-8") as f:
    f.readline(); f.readline()
    for line in f:
        cols = line.split(" | ")
        if len(cols) < 3:
            continue
        nm = cols[0].strip()
        m = NAME.match(nm)
        if m and m.group(2) in SUFFIXES:
            want[nm] = cols[2].strip()
print(f"dump 里带目标后缀的变体: {len(want)} 条")

# ② 读 bundle
bundle = json.load(io.open(BUNDLE, encoding="utf-8"))
glyphs = bundle.get("glyphs", bundle)
print(f"bundle 现有字形: {len(glyphs)} 条")

add = {k: v for k, v in want.items() if k not in glyphs}
print(f"需要新增: {len(add)} 条")
by_suf = {}
for k in add:
    by_suf[k.rsplit("-", 1)[-1]] = by_suf.get(k.rsplit("-", 1)[-1], 0) + 1
print("  按后缀:", dict(sorted(by_suf.items())))
for k in ("u8fb6-05", "u9f3b-06", "u56d7-05", "u53e3-05"):
    print(f"  {k:10s} {'已在' if k in glyphs else ('将新增' if k in add else 'dump 里也没有')}")

if dry or not add:
    print("(dry-run 或无需新增, 未写入)")
    sys.exit(0)

# ③ 备份 → 合并 → 原子替换
bak = BUNDLE + ".bak"
if not os.path.exists(bak):
    shutil.copy2(BUNDLE, bak)
    print(f"已备份 → {bak}")
glyphs.update(add)
if "glyphs" not in bundle:
    bundle = {"glyphs": glyphs}
tmp = BUNDLE + ".tmp"
io.open(tmp, "w", encoding="utf-8").write(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")))
os.replace(tmp, BUNDLE)
print(f"写入完成: {BUNDLE} ({os.path.getsize(BUNDLE)/1024/1024:.1f} MB, 共 {len(glyphs)} 条)")
