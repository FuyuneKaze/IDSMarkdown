"""
生成矩形分配对比图 v2 — 调弱偏旁表 + 渲染实际 KAGE 笔画
"""
import sys, io, math, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from test_bbox_alloc import (
    load_glyph_db, compute_moments, resolve_kage, clamp,
    allocate_rectangle_horizontal, allocate_rectangle_vertical,
    current_allocate_horizontal, current_allocate_vertical,
    get_variant_key, CHAR_TO_KEYS, WEAK_RADICAL_TABLE, BBox,
)

# --- 调弱后的偏旁表 (不再那么激进) ---
WEAK_RADICAL_TABLE_V2 = {
    '亻': {('⿰', 0): 0.28},
    '刂': {('⿰', 0): 0.25},
    '口': {('⿰', 0): 0.32},
    '日': {('⿰', 0): 0.35},
    '月': {('⿰', 0): 0.36},
    '氵': {('⿰', 0): 0.30},
    '扌': {('⿰', 0): 0.32},
    '忄': {('⿰', 0): 0.28},
    '王': {('⿰', 0): 0.36},
    '石': {('⿰', 0): 0.38},
    '土': {('⿰', 0): 0.35},
    '火': {('⿰', 0): 0.36},
    '木': {('⿰', 0): 0.38},
    '水': {('⿰', 0): 0.38},
    '言': {('⿰', 0): 0.40},
    '艹': {('⿱', 0): 0.24},
    '日': {('⿱', 0): 0.35},
    '口': {('⿱', 0): 0.32},
}

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"
OUT_DIR = os.path.join(os.path.dirname(__file__), "output", "bbox_compare")
os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# KAGE 笔画渲染 — 保持笔画结构
# ============================================================

def resolve_kage_structured(data_str, glyph_db, visited=None):
    """
    递归展开 type-99，保持笔画结构。
    返回: [(kind, [x1,y1,x2,y2,...]), ...]
    """
    if visited is None: visited = set()
    strokes = []

    for s in data_str.split('$'):
        s = s.strip()
        if not s: continue
        parts = s.split(':')
        if len(parts) < 4: continue
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            ref_name = parts[7]
            at_idx = ref_name.find('@')
            base = ref_name[:at_idx] if at_idx > 0 else ref_name
            if base not in visited and base in glyph_db:
                visited.add(base)
                sx1 = int(parts[3]); sy1 = int(parts[4])
                sx2 = int(parts[5]); sy2 = int(parts[6])
                sub_strokes = resolve_kage_structured(glyph_db[base], glyph_db, visited)
                for sk, scoords in sub_strokes:
                    # 映射坐标
                    mapped = []
                    for j in range(0, len(scoords), 2):
                        x = scoords[j]; y = scoords[j+1]
                        mx = sx1 + (x / 200.0) * (sx2 - sx1)
                        my = sy1 + (y / 200.0) * (sy2 - sy1)
                        mapped.extend([mx, my])
                    strokes.append((sk, mapped))
        elif kind >= 0 and kind <= 8:
            # 提取坐标 (跳过 a2, a3 即 parts[1], parts[2])
            coords = []
            for j in range(3, len(parts)):
                try:
                    coords.append(int(parts[j]))
                except ValueError:
                    coords.append(0)
            strokes.append((kind, coords))

    return strokes


def render_kage_strokes_svg(data_str, glyph_db, rx1, ry1, rx2, ry2, color, opacity=0.8, sw=1.2):
    """
    将 KAGE 数据渲染为 SVG，按笔画类型绘制
    """
    strokes = resolve_kage_structured(data_str, glyph_db, set())
    if not strokes:
        return ""

    rw = rx2 - rx1
    rh = ry2 - ry1
    if rw <= 0 or rh <= 0:
        return ""

    def map_pt(x, y):
        return (rx1 + x * rw / 200.0, ry1 + y * rh / 200.0)

    lines = []
    for kind, coords in strokes:
        if len(coords) < 2:
            continue
        pts = [map_pt(coords[j], coords[j+1]) for j in range(0, len(coords)//2*2, 2)]

        if kind == 1 and len(pts) >= 2:
            # 直线
            lines.append(f'<line x1="{pts[0][0]:.1f}" y1="{pts[0][1]:.1f}" '
                        f'x2="{pts[1][0]:.1f}" y2="{pts[1][1]:.1f}" '
                        f'stroke="{color}" stroke-width="{sw}" opacity="{opacity}" '
                        f'stroke-linecap="round"/>')
        elif kind == 2 and len(pts) >= 3:
            # 二次贝塞尔 (起点-控制点-终点)
            lines.append(f'<path d="M{pts[0][0]:.1f},{pts[0][1]:.1f} '
                        f'Q{pts[1][0]:.1f},{pts[1][1]:.1f} '
                        f'{pts[2][0]:.1f},{pts[2][1]:.1f}" '
                        f'fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'opacity="{opacity}" stroke-linecap="round"/>')
        elif kind == 6 and len(pts) >= 4:
            # 三次贝塞尔
            lines.append(f'<path d="M{pts[0][0]:.1f},{pts[0][1]:.1f} '
                        f'C{pts[1][0]:.1f},{pts[1][1]:.1f} '
                        f'{pts[2][0]:.1f},{pts[2][1]:.1f} '
                        f'{pts[3][0]:.1f},{pts[3][1]:.1f}" '
                        f'fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'opacity="{opacity}" stroke-linecap="round"/>')
        else:
            # 其余类型: 折线
            d = " ".join(f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" if i == 0 else f"L{p[0]:.1f},{p[1]:.1f}"
                         for i, p in enumerate(pts))
            lines.append(f'<path d="{d}" fill="none" stroke="{color}" '
                        f'stroke-width="{sw}" opacity="{opacity}" stroke-linecap="round" '
                        f'stroke-linejoin="round"/>')
    return "\n".join(lines)


# ============================================================
# 方框图生成
# ============================================================

CANVAS = 280
CELL = 200
MARGIN = 40

def rect_svg(x, y, w, h, fill, stroke, sw=1.5, opacity=0.25, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>')

def line_svg(x1, y1, x2, y2, color, w=1.0, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{w}"{d}/>'

def text_svg(x, y, text, size=10, fill="#ccc", anchor="middle", bold=False):
    fw = 'font-weight="bold"' if bold else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" text-anchor="{anchor}" font-family="monospace" {fw}>{text}</text>'


TEST_CASES = [
    ("⿰亻尔", 0x2FF0, '亻', '尔'),
    ("⿰木子", 0x2FF0, '木', '子'),
    ("⿰口木", 0x2FF0, '口', '木'),
    ("⿱艹朋", 0x2FF1, '艹', '朋'),
    ("⿰木木", 0x2FF0, '木', '木'),
    ("⿰人言", 0x2FF0, '人', '言'),
]

# 加载数据
all_keys = set()
for _, _, c1, c2 in TEST_CASES:
    for pos_idx, c in enumerate([c1, c2]):
        k = get_variant_key(c, pos_idx)
        if k: all_keys.add(k)
print(f"加载 {len(all_keys)} 个字形...")
glyph_db = load_glyph_db(DUMP, all_keys)

# ============================================================
# 构建 SVG
# ============================================================

# 覆盖 lookup_weak_radical 使用 v2 表
import test_bbox_alloc as tba
original_lookup = tba.lookup_weak_radical

def v2_lookup(ch, op_cp, pos):
    op_name = {0x2FF0: '⿰', 0x2FF1: '⿱'}.get(op_cp, '?')
    entry = WEAK_RADICAL_TABLE_V2.get(ch, {})
    return entry.get((op_name, pos), None)

tba.lookup_weak_radical = v2_lookup

ROWS = len(TEST_CASES)
COLS = 3  # 旧方案 / 新方案(v2) / 密度+split对比
COL_W = CANVAS + 30
ROW_H = CANVAS + 80
TOTAL_W = COL_W * COLS + 20
TOTAL_H = ROW_H * ROWS + 80

parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{TOTAL_W}" height="{TOTAL_H}">
<rect width="100%" height="100%" fill="#1a1a2e"/>''']

# 列标题
for ci, label in enumerate(["当前算法", "新算法 (v2 偏旁表)", "密度投影 + split对比"]):
    x = MARGIN + ci * COL_W + CELL // 2
    parts.append(text_svg(x, 24, label, 12, "#ddd", "middle", True))

for ri, (desc, op_cp, c1, c2) in enumerate(TEST_CASES):
    y0 = 50 + ri * ROW_H
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    d1 = glyph_db.get(k1, '')
    d2 = glyph_db.get(k2, '')

    # --- 列 0: 当前算法 ---
    cx0 = 0 * COL_W
    parts.append(rect_svg(MARGIN+cx0, y0, CELL, CELL, "none", "#444", 0.5, 0))

    if op_cp == 0x2FF0:
        r1, r2, split, overlap = current_allocate_horizontal(d1, d2, glyph_db)
    else:
        r1, r2, split, overlap = current_allocate_vertical(d1, d2, glyph_db)

    # 绘制部件矩形 + 字形
    for (rx1, ry1, rx2, ry2), d, color in [
        (r1, d1, "#4fc3f7"),
        (r2, d2, "#ef9a9a")
    ]:
        parts.append(rect_svg(MARGIN+cx0+rx1, y0+ry1, rx2-rx1, ry2-ry1, color, color, 1.0, 0.12))
        # 渲染实际字形
        stroke_svg = render_kage_strokes_svg(d, glyph_db,
            MARGIN+cx0+rx1, y0+ry1, MARGIN+cx0+rx2, y0+ry2, color, 0.7, 1.0)
        if stroke_svg:
            parts.append(stroke_svg)

    # split 线
    if op_cp == 0x2FF0:
        parts.append(line_svg(MARGIN+cx0+split, y0, MARGIN+cx0+split, y0+CELL, "#f66", 1.2, "5,3"))
    else:
        parts.append(line_svg(MARGIN+cx0, y0+split, MARGIN+cx0+CELL, y0+split, "#f66", 1.2, "5,3"))

    parts.append(text_svg(MARGIN+cx0+CELL//2, y0-8, desc, 12, "#aaa", "middle"))
    parts.append(text_svg(MARGIN+cx0+CELL//2, y0+CELL+18, f"s={split} ol={overlap}", 9, "#f88", "middle"))

    # --- 列 1: 新算法 v2 ---
    cx1 = 1 * COL_W
    parts.append(rect_svg(MARGIN+cx1, y0, CELL, CELL, "none", "#444", 0.5, 0))

    if op_cp == 0x2FF0:
        r1, r2, split, overlap, dbg = allocate_rectangle_horizontal(d1, d2, c1, c2, glyph_db)
    else:
        r1, r2, split, overlap, dbg = allocate_rectangle_vertical(d1, d2, c1, c2, glyph_db)

    # 重叠区
    if op_cp == 0x2FF0 and r1[2] > r2[0]:
        parts.append(rect_svg(MARGIN+cx1+r2[0], y0+3, r1[2]-r2[0], CELL-6, "#ff0", "none", 0, 0.10))
    elif op_cp == 0x2FF1 and r1[3] > r2[1]:
        parts.append(rect_svg(MARGIN+cx1+3, y0+r2[1], CELL-6, r1[3]-r2[1], "#ff0", "none", 0, 0.10))

    for (rx1, ry1, rx2, ry2), d, color in [
        (r1, d1, "#4fc3f7"),
        (r2, d2, "#ef9a9a")
    ]:
        parts.append(rect_svg(MARGIN+cx1+rx1, y0+ry1, rx2-rx1, ry2-ry1, color, color, 1.0, 0.12))
        stroke_svg = render_kage_strokes_svg(d, glyph_db,
            MARGIN+cx1+rx1, y0+ry1, MARGIN+cx1+rx2, y0+ry2, color, 0.8, 1.2)
        if stroke_svg:
            parts.append(stroke_svg)

    if op_cp == 0x2FF0:
        parts.append(line_svg(MARGIN+cx1+split, y0, MARGIN+cx1+split, y0+CELL, "#4f4", 1.2, "5,3"))
    else:
        parts.append(line_svg(MARGIN+cx1, y0+split, MARGIN+cx1+CELL, y0+split, "#4f4", 1.2, "5,3"))

    parts.append(text_svg(MARGIN+cx1+CELL//2, y0-8, desc, 12, "#aaa", "middle"))
    parts.append(text_svg(MARGIN+cx1+CELL//2, y0+CELL+18, f"s={split} ol={overlap}", 9, "#4f4", "middle"))

    # --- 列 2: 密度投影 + 数值对比 ---
    cx2 = 2 * COL_W
    Lm = compute_moments(d1, glyph_db)
    Rm = compute_moments(d2, glyph_db)

    # 密度图
    BINS = 20
    BW = CELL // BINS
    parts.append(text_svg(MARGIN+cx2+CELL//2, y0-8, "密度投影", 11, "#aaa", "middle"))

    if op_cp == 0x2FF0:
        # 横向密度
        for bi in range(BINS):
            lv = Lm.x_profile[bi]
            if lv > 0.005:
                h = lv * 200 * 2.5
                parts.append(f'<rect x="{MARGIN+cx2+bi*BW+1:.1f}" y="{y0+CELL-h:.1f}" width="{BW-1:.1f}" height="{h:.1f}" fill="#4fc3f7" opacity="0.65"/>')
            rv = Rm.x_profile[bi]
            if rv > 0.005:
                h = rv * 200 * 2.5
                parts.append(f'<rect x="{MARGIN+cx2+bi*BW+1:.1f}" y="{y0+CELL:.1f}" width="{BW-1:.1f}" height="{h:.1f}" fill="#ef9a9a" opacity="0.65"/>')
        # 画布框
        parts.append(rect_svg(MARGIN+cx2, y0, CELL, CELL, "none", "#444", 0.5, 0))
        # 分隔线
        parts.append(line_svg(MARGIN+cx2, y0+CELL, MARGIN+cx2+CELL, y0+CELL, "#555", 0.5))
        # split 指示
        sx = MARGIN + cx2 + split * (CELL/200)
        parts.append(line_svg(sx, y0, sx, y0+CELL*2-2, "#ff0", 0.8, "3,3"))
    else:
        # 纵向密度
        for bi in range(BINS):
            lv = Lm.y_profile[bi]
            if lv > 0.005:
                w = lv * 200 * 2.5
                parts.append(f'<rect x="{MARGIN+cx2:.1f}" y="{y0+bi*BW+1:.1f}" width="{w:.1f}" height="{BW-1:.1f}" fill="#4fc3f7" opacity="0.65"/>')
            rv = Rm.y_profile[bi]
            if rv > 0.005:
                w = rv * 200 * 2.5
                parts.append(f'<rect x="{MARGIN+cx2+CELL-w:.1f}" y="{y0+bi*BW+1:.1f}" width="{w:.1f}" height="{BW-1:.1f}" fill="#ef9a9a" opacity="0.65"/>')
        parts.append(rect_svg(MARGIN+cx2, y0, CELL, CELL, "none", "#444", 0.5, 0))
        sy = y0 + split * (CELL/200)
        parts.append(line_svg(MARGIN+cx2, sy, MARGIN+cx2+CELL*2, sy, "#ff0", 0.8, "3,3"))

    # 数值对比表
    if op_cp == 0x2FF0:
        old_r = current_allocate_horizontal(d1, d2, glyph_db)
    else:
        old_r = current_allocate_vertical(d1, d2, glyph_db)
    old_split, old_ol = old_r[2], old_r[3]

    info_lines = [
        f"{c1}: μ({Lm.cx:.0f},{Lm.cy:.0f}) σ({Lm.sx:.0f},{Lm.sy:.0f}) W={Lm.bbox.width()} H={Lm.bbox.height()}",
        f"{c2}: μ({Rm.cx:.0f},{Rm.cy:.0f}) σ({Rm.sx:.0f},{Rm.sy:.0f}) W={Rm.bbox.width()} H={Rm.bbox.height()}",
        f"旧 split={old_split} ol={old_ol}  |  新 split={split} ol={overlap}",
    ]
    for li, txt in enumerate(info_lines):
        parts.append(text_svg(MARGIN+cx2+CELL//2, y0+CELL+28+li*14, txt, 8, "#888", "middle"))

    print(f"  {desc}: 旧split={old_split}/{old_ol} → 新split={split}/{overlap}")


parts.append('</svg>')

svg_path = os.path.join(OUT_DIR, "compare_v2.svg")
with open(svg_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(parts))
print(f"\n已保存: {svg_path}")

# 恢复
tba.lookup_weak_radical = original_lookup
