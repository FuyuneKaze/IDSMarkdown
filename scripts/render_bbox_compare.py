"""
生成矩形分配对比图 — 直接在 200×200 坐标系上绘制新旧方案的矩形
输出到 scripts/output/bbox_compare/
"""
import sys, io, math, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 复用验证脚本的函数 ---
from test_bbox_alloc import (
    load_glyph_db, compute_moments, MomentInfo, BBox,
    resolve_kage, clamp,
    allocate_rectangle_horizontal, allocate_rectangle_vertical,
    current_allocate_horizontal, current_allocate_vertical,
    get_variant_key, CHAR_TO_KEYS, WEAK_RADICAL_TABLE, lookup_weak_radical,
)

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"

# --- 测试用例 ---
TEST_CASES = [
    ("⿰亻尔", 0x2FF0, '亻', '尔'),
    ("⿰木子", 0x2FF0, '木', '子'),
    ("⿰木木", 0x2FF0, '木', '木'),
    ("⿰口口", 0x2FF0, '口', '口'),
    ("⿱艹朋", 0x2FF1, '艹', '朋'),
    ("⿱日日", 0x2FF1, '日', '日'),
    ("⿰人言", 0x2FF0, '人', '言'),
    ("⿰亻言", 0x2FF0, '亻', '言'),
]

# --- 加载数据 ---
all_keys = set()
for _, _, c1, c2 in TEST_CASES:
    for pos_idx, c in enumerate([c1, c2]):
        k = get_variant_key(c, pos_idx)
        if k: all_keys.add(k)
print(f"加载 {len(all_keys)} 个字形...")
glyph_db = load_glyph_db(DUMP, all_keys)

# --- 生成 SVG ---
OUT_DIR = os.path.join(os.path.dirname(__file__), "output", "bbox_compare")
os.makedirs(OUT_DIR, exist_ok=True)

CANVAS = 250  # 渲染画布大小 (含边距)
CELL = 200     # KAGE 坐标系
MARGIN = 25

def styled_rect(x1, y1, x2, y2, fill, stroke, stroke_w=1.5, opacity=0.35, dash=None):
    w = x2 - x1
    h = y2 - y1
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x1+MARGIN}" y="{y1+MARGIN}" width="{w}" height="{h}" '
            f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" '
            f'stroke-width="{stroke_w}"{dash_attr}/>')

def styled_line(x1, y1, x2, y2, stroke, w=1.5, dash=None):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1+MARGIN}" y1="{y1+MARGIN}" x2="{x2+MARGIN}" y2="{y2+MARGIN}" stroke="{stroke}" stroke-width="{w}"{dash_attr}/>'

def styled_text(x, y, text, size=10, fill="#ccc", anchor="middle"):
    return f'<text x="{x+MARGIN}" y="{y+MARGIN}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" font-family="monospace">{text}</text>'

def render_single_case(desc, op_cp, c1, c2, label, allocate_fn, extra_info=""):
    """渲染单个方案的 SVG 片段"""
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    d1 = glyph_db.get(k1, '')
    d2 = glyph_db.get(k2, '')

    rect1, rect2, split, overlap, debug_str = allocate_fn(d1, d2, c1, c2, glyph_db)

    lines = []

    # 画布边框
    lines.append(styled_rect(0, 0, CELL, CELL, "none", "#555", 1, 0))

    # 重叠区域 (半透明)
    r1_x1, r1_y1, r1_x2, r1_y2 = rect1
    r2_x1, r2_y1, r2_x2, r2_y2 = rect2

    if op_cp == 0x2FF0:
        overlap_x1 = r2_x1
        overlap_x2 = r1_x2
        if overlap_x2 > overlap_x1:
            lines.append(styled_rect(overlap_x1, 3, overlap_x2, CELL-3, "#ff0", "none", 0, 0.15))
    else:
        overlap_y1 = r2_y1
        overlap_y2 = r1_y2
        if overlap_y2 > overlap_y1:
            lines.append(styled_rect(3, overlap_y1, CELL-3, overlap_y2, "#ff0", "none", 0, 0.15))

    # 部件矩形
    color1 = "#4fc3f7"  # 蓝
    color2 = "#ef9a9a"  # 红
    lines.append(styled_rect(r1_x1, r1_y1, r1_x2, r1_y2, color1, color1, 1.5, 0.30))
    lines.append(styled_rect(r2_x1, r2_y1, r2_x2, r2_y2, color2, color2, 1.5, 0.30))

    # split 线
    if op_cp == 0x2FF0:
        lines.append(styled_line(split, 0, split, CELL, "#fff", 0.8, "4,4"))
    else:
        lines.append(styled_line(0, split, CELL, split, "#fff", 0.8, "4,4"))

    # 标签
    lines.append(styled_text(r1_x1 + (r1_x2-r1_x1)//2, r1_y1 + (r1_y2-r1_y1)//2,
                             c1, 12, "#fff", "middle"))
    lines.append(styled_text(r2_x1 + (r2_x2-r2_x1)//2, r2_y1 + (r2_y2-r2_y1)//2,
                             c2, 12, "#fff", "middle"))

    # 数据标注
    title = f"{label}: split={split} overlap={overlap}"
    lines.append(styled_text(CELL//2, -8, title, 9, "#aaa", "middle"))
    if extra_info:
        lines.append(styled_text(CELL//2, CELL+16, extra_info, 8, "#888", "middle"))

    return "\n    ".join(lines)


# --- 生成全景对比图 ---
# 每个 IDS 一行, 左侧旧方案, 右侧新方案
COLS = 3  # 旧 / 新 / 密度
ROW_H = CANVAS + 10
COL_W = CANVAS + 20

total_w = COL_W * COLS + 30
total_h = ROW_H * len(TEST_CASES) + 60

svg_parts = []
svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}">
<style>
  .label {{ fill: #999; font-size: 11px; font-family: monospace; text-anchor: middle; }}
  .title {{ fill: #ddd; font-size: 13px; font-family: monospace; text-anchor: middle; font-weight: bold; }}
</style>
<rect width="100%" height="100%" fill="#1a1a2e"/>''')

# 列标题
col_labels = ["当前算法", "新算法", "密度投影 (新)"]
for ci, cl in enumerate(col_labels):
    x = MARGIN + ci * COL_W + CELL // 2
    svg_parts.append(f'<text x="{x}" y="22" class="title">{cl}</text>')

for ri, (desc, op_cp, c1, c2) in enumerate(TEST_CASES):
    y_off = 40 + ri * ROW_H

    # --- 当前算法 ---
    ci = 0
    if op_cp == 0x2FF0:
        rect1, rect2, split, overlap = current_allocate_horizontal(
            glyph_db[get_variant_key(c1, 0)], glyph_db[get_variant_key(c2, 1)], glyph_db)
    else:
        rect1, rect2, split, overlap = current_allocate_vertical(
            glyph_db[get_variant_key(c1, 0)], glyph_db[get_variant_key(c2, 1)], glyph_db)

    svg_parts.append(f'<g transform="translate({ci * COL_W}, {y_off})">')
    svg_parts.append(styled_rect(0, 0, CELL, CELL, "none", "#555", 1, 0))
    c1_color, c2_color = "#4fc3f7", "#ef9a9a"
    svg_parts.append(styled_rect(rect1[0], rect1[1], rect1[2], rect1[3], c1_color, c1_color, 1.5, 0.30))
    svg_parts.append(styled_rect(rect2[0], rect2[1], rect2[2], rect2[3], c2_color, c2_color, 1.5, 0.30))
    if op_cp == 0x2FF0:
        svg_parts.append(styled_line(split, 0, split, CELL, "#fff", 0.8, "4,4"))
    else:
        svg_parts.append(styled_line(0, split, CELL, split, "#fff", 0.8, "4,4"))
    svg_parts.append(styled_text(CELL//2, CELL+14, f"split={split} ol={overlap}", 9, "#f88", "middle"))
    svg_parts.append(styled_text(CELL//2, -6, desc, 11, "#aaa", "middle"))
    svg_parts.append('</g>')

    # --- 新算法 ---
    ci = 1
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    d1 = glyph_db.get(k1, '')
    d2 = glyph_db.get(k2, '')
    if op_cp == 0x2FF0:
        rect1, rect2, split, overlap, debug = allocate_rectangle_horizontal(d1, d2, c1, c2, glyph_db)
    else:
        rect1, rect2, split, overlap, debug = allocate_rectangle_vertical(d1, d2, c1, c2, glyph_db)

    svg_parts.append(f'<g transform="translate({ci * COL_W}, {y_off})">')
    svg_parts.append(styled_rect(0, 0, CELL, CELL, "none", "#555", 1, 0))
    svg_parts.append(styled_rect(rect1[0], rect1[1], rect1[2], rect1[3], c1_color, c1_color, 1.5, 0.30))
    svg_parts.append(styled_rect(rect2[0], rect2[1], rect2[2], rect2[3], c2_color, c2_color, 1.5, 0.30))
    if op_cp == 0x2FF0:
        svg_parts.append(styled_line(split, 0, split, CELL, "#fff", 0.8, "4,4"))
        # 重叠区域
        if rect1[2] > rect2[0]:
            svg_parts.append(styled_rect(rect2[0], 3, rect1[2], CELL-3, "#ff0", "none", 0, 0.13))
    else:
        svg_parts.append(styled_line(0, split, CELL, split, "#fff", 0.8, "4,4"))
        if rect1[3] > rect2[1]:
            svg_parts.append(styled_rect(3, rect2[1], CELL-3, rect1[3], "#ff0", "none", 0, 0.13))
    svg_parts.append(styled_text(CELL//2, CELL+14, f"split={split} ol={overlap}", 9, "#4f4", "middle"))
    svg_parts.append(styled_text(CELL//2, -6, desc, 11, "#aaa", "middle"))
    svg_parts.append('</g>')

    # --- 密度投影 ---
    ci = 2
    Lm = compute_moments(d1, glyph_db)
    Rm = compute_moments(d2, glyph_db)

    svg_parts.append(f'<g transform="translate({ci * COL_W}, {y_off})">')
    svg_parts.append(styled_rect(0, 0, CELL, CELL, "none", "#555", 1, 0))

    # 绘制密度条形图 (左右) 或上下
    if op_cp == 0x2FF0:
        BINS = 20
        BW = 10
        for bi in range(BINS):
            # L 密度
            lv = Lm.x_profile[bi]
            if lv > 0.01:
                h = lv * 200 * 3  # 缩放到可读
                svg_parts.append(f'<rect x="{bi*BW+3+MARGIN}" y="{CELL+MARGIN-h}" width="{BW-1}" height="{h}" fill="#4fc3f7" opacity="0.6"/>')
            # R 密度
            rv = Rm.x_profile[bi]
            if rv > 0.01:
                h = rv * 200 * 3
                svg_parts.append(f'<rect x="{bi*BW+3+MARGIN}" y="{CELL+MARGIN}" width="{BW-1}" height="{h}" fill="#ef9a9a" opacity="0.6"/>')
        svg_parts.append(styled_text(CELL//2, -6, "横向密度 (蓝=L 红=R)", 9, "#aaa", "middle"))
        # 标注split线在密度图上的位置
        split_bin = split / 10
        svg_parts.append(styled_line(split_bin*10, 0, split_bin*10, CELL, "#ff0", 0.8, "2,4"))
    else:
        BINS = 20
        BH = 10
        for bi in range(BINS):
            lv = Lm.y_profile[bi]
            if lv > 0.01:
                w = lv * 200 * 3
                svg_parts.append(f'<rect x="{MARGIN}" y="{bi*BH+3+MARGIN}" width="{w}" height="{BH-1}" fill="#4fc3f7" opacity="0.6"/>')
            rv = Rm.y_profile[bi]
            if rv > 0.01:
                w = rv * 200 * 3
                svg_parts.append(f'<rect x="{CELL+MARGIN-w}" y="{bi*BH+3+MARGIN}" width="{w}" height="{BH-1}" fill="#ef9a9a" opacity="0.6"/>')
        svg_parts.append(styled_text(CELL//2, -6, "纵向密度 (蓝=T 红=B)", 9, "#aaa", "middle"))
        split_bin = split / 10
        svg_parts.append(styled_line(0, split_bin*10, CELL, split_bin*10, "#ff0", 0.8, "2,4"))

    svg_parts.append('</g>')

svg_parts.append('</svg>')

svg_content = "\n".join(svg_parts)

# 保存
svg_path = os.path.join(OUT_DIR, "compare.svg")
with open(svg_path, 'w', encoding='utf-8') as f:
    f.write(svg_content)
print(f"已保存: {svg_path}")

# 同时生成单张详细图
for desc, op_cp, c1, c2 in TEST_CASES[:4]:  # 前4个
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    d1 = glyph_db.get(k1, '')
    d2 = glyph_db.get(k2, '')

    Lm = compute_moments(d1, glyph_db)
    Rm = compute_moments(d2, glyph_db)

    detail_parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS*2+80}" height="{CANVAS+60}">
<style>.t {{ fill: #aaa; font-size: 10px; font-family: monospace; text-anchor: middle; }}</style>
<rect width="100%" height="100%" fill="#1a1a2e"/>''']

    # 左: 矩形分配图
    detail_parts.append(f'<text x="{CANVAS//2+20}" y="18" class="t" font-size="13" fill="#fff">{desc}</text>')

    if op_cp == 0x2FF0:
        old_r = current_allocate_horizontal(d1, d2, glyph_db)
        new_r = allocate_rectangle_horizontal(d1, d2, c1, c2, glyph_db)
    else:
        old_r = current_allocate_vertical(d1, d2, glyph_db)
        new_r = allocate_rectangle_vertical(d1, d2, c1, c2, glyph_db)

    for scheme, rects, color, xoff in [
        ("旧", old_r, "#f66", 0),
        ("新", new_r, "#6f6", CANVAS+40)
    ]:
        r1, r2, split, overlap = rects[:4]
        detail_parts.append(f'<text x="{xoff+MARGIN+CANVAS//2}" y="34" class="t" fill="{color}">{scheme}: split={split} ol={overlap}</text>')
        # 画布
        detail_parts.append(styled_rect(0+xoff, 42, CELL+xoff, CELL+42, "none", "#555", 1, 0))
        # 部件
        detail_parts.append(styled_rect(r1[0]+xoff, r1[1]+42, r1[2]+xoff, r1[3]+42, "#4fc3f7", "#4fc3f7", 1.5, 0.30))
        detail_parts.append(styled_rect(r2[0]+xoff, r2[1]+42, r2[2]+xoff, r2[3]+42, "#ef9a9a", "#ef9a9a", 1.5, 0.30))
        # split
        if op_cp == 0x2FF0:
            detail_parts.append(styled_line(split+xoff, 42, split+xoff, CELL+42, color, 1.5, "4,4"))
        else:
            detail_parts.append(styled_line(xoff, split+42, CELL+xoff, split+42, color, 1.5, "4,4"))
        # 标签
        detail_parts.append(styled_text(r1[0]+xoff+(r1[2]-r1[0])//2, r1[1]+42+(r1[3]-r1[1])//2, c1, 14, "#fff", "middle"))
        detail_parts.append(styled_text(r2[0]+xoff+(r2[2]-r2[0])//2, r2[1]+42+(r2[3]-r2[1])//2, c2, 14, "#fff", "middle"))

    # 矩信息
    L_short = f"{c1}: μ({Lm.cx:.0f},{Lm.cy:.0f}) σ({Lm.sx:.0f},{Lm.sy:.0f}) bbox({Lm.bbox.x1},{Lm.bbox.y1}-{Lm.bbox.x2},{Lm.bbox.y2})"
    R_short = f"{c2}: μ({Rm.cx:.0f},{Rm.cy:.0f}) σ({Rm.sx:.0f},{Rm.sy:.0f}) bbox({Rm.bbox.x1},{Rm.bbox.y1}-{Rm.bbox.x2},{Rm.bbox.y2})"
    detail_parts.append(styled_text(CANVAS+20, CANVAS+58, L_short, 8, "#888", "middle"))
    detail_parts.append(styled_text(CANVAS+20, CANVAS+70, R_short, 8, "#888", "middle"))

    detail_parts.append('</svg>')
    detail_path = os.path.join(OUT_DIR, f"detail_{desc[0]}.svg")
    with open(detail_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(detail_parts))

print(f"输出目录: {OUT_DIR}")
print("文件列表:", os.listdir(OUT_DIR))
