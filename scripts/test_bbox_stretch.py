"""
验证 bbox 驱动的伸缩映射

核心思路:
  不再做 (0,200)→目标矩形的线性映射
  而是让部件的真实 bbox 填满目标矩形
  这样分配多大矩形 = 视觉上就占多大

对于 type-99: 99:sx:sy:x1:y1:x2:y2:name:sx2:sy2
  当前 sx=sy=sx2=sy2=0 → 简单线性映射, 不伸缩
  需要计算 sx/sy 让 bbox 区域填满目标矩形
"""

import sys, io, math, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from test_bbox_alloc import (
    load_glyph_db, compute_moments, resolve_kage, clamp,
    get_variant_key, CHAR_TO_KEYS, BBox,
)

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"

# ============================================================
# 1. 从 KAGE 数据计算真实 bbox
# ============================================================

# KAGE Mincho 笔宽: kWidth=5, kMinWidthT=6, 半宽≈3, 加安全边距=4
STROKE_PAD = 4

def compute_true_bbox(data_str, glyph_db, pad=True):
    """计算部件的视觉包围盒 (骨架 + 笔宽 padding)"""
    pts = resolve_kage(data_str, glyph_db, set())
    if not pts:
        return BBox()
    bb = BBox()
    for x, y in pts:
        bb.expand(int(x), int(y))
    if pad and bb.valid():
        bb.x1 -= STROKE_PAD; bb.y1 -= STROKE_PAD
        bb.x2 += STROKE_PAD; bb.y2 += STROKE_PAD
        # 不超出 0-200 画布
        bb.x1 = max(0, bb.x1); bb.y1 = max(0, bb.y1)
        bb.x2 = min(200, bb.x2); bb.y2 = min(200, bb.y2)
    return bb


# ============================================================
# 2. 渲染 — bbox 驱动伸缩
# ============================================================

def resolve_kage_structured(data_str, glyph_db, visited=None):
    """递归展开 type-99, 保持笔画结构"""
    if visited is None: visited = set()
    strokes = []
    for s in data_str.split('$'):
        s = s.strip()
        if not s: continue
        parts = s.split(':')
        if len(parts) < 4: continue
        try: kind = int(parts[0])
        except ValueError: continue
        if kind == 99 and len(parts) >= 8:
            ref_name = parts[7]
            base = ref_name.split('@')[0]
            if base not in visited and base in glyph_db:
                visited.add(base)
                sx1, sy1 = int(parts[3]), int(parts[4])
                sx2, sy2 = int(parts[5]), int(parts[6])
                sub = resolve_kage_structured(glyph_db[base], glyph_db, visited)
                for sk, scoords in sub:
                    mapped = []
                    for j in range(0, len(scoords), 2):
                        mx = sx1 + (scoords[j] / 200.0) * (sx2 - sx1)
                        my = sy1 + (scoords[j+1] / 200.0) * (sy2 - sy1)
                        mapped.extend([mx, my])
                    strokes.append((sk, mapped))
        elif kind >= 0 and kind <= 8:
            coords = []
            for j in range(3, len(parts)):
                try: coords.append(int(parts[j]))
                except ValueError: coords.append(0)
            strokes.append((kind, coords))
    return strokes


def render_kage_bbox_stretch(data_str, glyph_db, rx1, ry1, rx2, ry2, color, opacity=0.8, sw=1.2):
    """
    bbox 驱动伸缩渲染:
    计算部件的真实 bbox, 然后将 bbox 映射到目标矩形
    bbox 之外的点按比例外推/压缩
    """
    strokes = resolve_kage_structured(data_str, glyph_db, set())
    if not strokes: return ""

    bb = compute_true_bbox(data_str, glyph_db)
    if not bb.valid(): return ""

    rw, rh = rx2 - rx1, ry2 - ry1
    bw, bh = bb.width(), bb.height()
    if rw <= 0 or rh <= 0 or bw <= 0 or bh <= 0: return ""

    def map_pt(x, y):
        """将原始坐标映射到目标矩形, 保持宽高比, 居中放置"""
        tx = (x - bb.x1) / bw if bw > 0 else 0.5
        ty = (y - bb.y1) / bh if bh > 0 else 0.5
        # 统一缩放: 取较小比例, 保持宽高比不扭曲
        scale = min(rw / bw, rh / bh)
        used_w = bw * scale
        used_h = bh * scale
        # 在目标矩形中居中
        ox = rx1 + (rw - used_w) / 2
        oy = ry1 + (rh - used_h) / 2
        return (ox + tx * used_w, oy + ty * used_h)

    def map_pt_legacy(x, y):
        """旧方案: 线性映射 (0,200)→目标矩形"""
        return (rx1 + x * rw / 200.0, ry1 + y * rh / 200.0)

    lines = []
    for kind, coords in strokes:
        if len(coords) < 2: continue
        pts = [map_pt(coords[j], coords[j+1]) for j in range(0, len(coords)//2*2, 2)]

        if kind == 1 and len(pts) >= 2:
            lines.append(f'<line x1="{pts[0][0]:.1f}" y1="{pts[0][1]:.1f}" '
                        f'x2="{pts[1][0]:.1f}" y2="{pts[1][1]:.1f}" '
                        f'stroke="{color}" stroke-width="{sw}" opacity="{opacity}" '
                        f'stroke-linecap="round"/>')
        elif kind == 2 and len(pts) >= 3:
            lines.append(f'<path d="M{pts[0][0]:.1f},{pts[0][1]:.1f} '
                        f'Q{pts[1][0]:.1f},{pts[1][1]:.1f} '
                        f'{pts[2][0]:.1f},{pts[2][1]:.1f}" '
                        f'fill="none" stroke="{color}" stroke-width="{sw}" '
                        f'opacity="{opacity}" stroke-linecap="round"/>')
        else:
            d = " ".join(f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" if i == 0
                        else f"L{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
            lines.append(f'<path d="{d}" fill="none" stroke="{color}" '
                        f'stroke-width="{sw}" opacity="{opacity}" '
                        f'stroke-linecap="round" stroke-linejoin="round"/>')
    return "\n".join(lines)


# ============================================================
# 3. 新旧渲染对比
# ============================================================

CANVAS = 300; CELL = 200; MARGIN = 50
OUT_DIR = os.path.join(os.path.dirname(__file__), "output", "bbox_compare")
os.makedirs(OUT_DIR, exist_ok=True)

def rect_svg(x, y, w, h, fill, stroke, sw=1, op=0.15):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"/>'

def line_svg(x1, y1, x2, y2, c, w=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}"{d}/>'

def text_svg(x, y, t, sz=10, c="#ccc", anc="middle", bold=False):
    fw = 'font-weight="bold"' if bold else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{c}" font-size="{sz}" text-anchor="{anc}" font-family="monospace" {fw}>{t}</text>'


TEST_CASES = [
    ("⿰亻尔", 0x2FF0, '亻', '尔', 55, 12),   # (split, overlap)
    ("⿰木子", 0x2FF0, '木', '子', 74, 12),
    ("⿰口木", 0x2FF0, '口', '木', 62, 8),
    ("⿱艹朋", 0x2FF1, '艹', '朋', 38, 6),
    ("⿰木木", 0x2FF0, '木', '木', 74, 12),
]

# 加载
all_keys = set()
for _, _, c1, c2, _, _ in TEST_CASES:
    for pos_idx, c in enumerate([c1, c2]):
        k = get_variant_key(c, pos_idx)
        if k: all_keys.add(k)
print(f"加载 {len(all_keys)} 个字形...")
glyph_db = load_glyph_db(DUMP, all_keys)

# 构建 SVG
COLS = 2  # 旧线性映射 vs bbox伸缩映射
COL_W = CANVAS + 30
ROW_H = CANVAS + 80
ROWS = len(TEST_CASES)
TOTAL_W = COL_W * COLS + 20
TOTAL_H = ROW_H * ROWS + 70

parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{TOTAL_W}" height="{TOTAL_H}">',
         f'<rect width="100%" height="100%" fill="#1a1a2e"/>']

for ci, label in enumerate(["旧: (0,200)→目标矩形 线性映射", "新: bbox填满目标矩形 (伸缩映射)"]):
    x = MARGIN + ci * COL_W + CELL // 2
    parts.append(text_svg(x, 24, label, 12, "#ddd", "middle", True))

for ri, (desc, op_cp, c1, c2, split, overlap) in enumerate(TEST_CASES):
    y0 = 50 + ri * ROW_H
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    d1 = glyph_db.get(k1, '')
    d2 = glyph_db.get(k2, '')

    bb1 = compute_true_bbox(d1, glyph_db)
    bb2 = compute_true_bbox(d2, glyph_db)

    # ---- 列 0: 旧线性映射 ----
    cx0 = 0 * COL_W
    parts.append(rect_svg(MARGIN+cx0, y0, CELL, CELL, "none", "#444", 0.5, 0))

    if op_cp == 0x2FF0:
        r1 = (3, 3, split + overlap//2, 200)
        r2 = (split - overlap//2, 3, 200, 200)
    else:
        r1 = (3, 3, 200, split + overlap//2)
        r2 = (3, split - overlap//2, 200, 200)

    # 部件矩形 + 旧线性映射渲染
    for (rx1, ry1, rx2, ry2), d, color in [(r1, d1, "#4fc3f7"), (r2, d2, "#ef9a9a")]:
        parts.append(rect_svg(MARGIN+cx0+rx1, y0+ry1, rx2-rx1, ry2-ry1, color, color, 1.2, 0.08))

    # 旧线性映射渲染 (手动实现) — 保留作为对照
    for (rx1, ry1, rx2, ry2), d, color in [(r1, d1, "#4fc3f7"), (r2, d2, "#ef9a9a")]:
        strokes = resolve_kage_structured(d, glyph_db, set())
        rw, rh = rx2 - rx1, ry2 - ry1
        for kind, coords in strokes:
            if len(coords) < 2: continue
            pts = []
            for j in range(0, len(coords)//2*2, 2):
                x = coords[j]; y = coords[j+1]
                mx = MARGIN + cx0 + rx1 + x * rw / 200.0
                my = y0 + ry1 + y * rh / 200.0
                pts.append((mx, my))
            if kind == 1 and len(pts) >= 2:
                parts.append(f'<line x1="{pts[0][0]:.1f}" y1="{pts[0][1]:.1f}" '
                            f'x2="{pts[1][0]:.1f}" y2="{pts[1][1]:.1f}" '
                            f'stroke="{color}" stroke-width="1.0" opacity="0.7" stroke-linecap="round"/>')
            elif kind == 2 and len(pts) >= 3:
                parts.append(f'<path d="M{pts[0][0]:.1f},{pts[0][1]:.1f} '
                            f'Q{pts[1][0]:.1f},{pts[1][1]:.1f} '
                            f'{pts[2][0]:.1f},{pts[2][1]:.1f}" '
                            f'fill="none" stroke="{color}" stroke-width="1.0" opacity="0.7" stroke-linecap="round"/>')
            else:
                d_str = " ".join(f"M{pts[0][0]:.1f},{pts[0][1]:.1f}" if i == 0
                                else f"L{p[0]:.1f},{p[1]:.1f}" for i, p in enumerate(pts))
                parts.append(f'<path d="{d_str}" fill="none" stroke="{color}" '
                            f'stroke-width="1.0" opacity="0.7" stroke-linecap="round" stroke-linejoin="round"/>')

    parts.append(text_svg(MARGIN+cx0+CELL//2, y0-8, desc, 12, "#aaa"))
    parts.append(text_svg(MARGIN+cx0+CELL//2, y0+CELL+15, f"线性映射 split={split}", 9, "#f88"))

    # ---- 列 1: bbox 伸缩映射 ----
    cx1 = 1 * COL_W
    parts.append(rect_svg(MARGIN+cx1, y0, CELL, CELL, "none", "#444", 0.5, 0))

    if op_cp == 0x2FF0:
        r1s = (3, 3, split + overlap//2, 200)
        r2s = (split - overlap//2, 3, 200, 200)
    else:
        r1s = (3, 3, 200, split + overlap//2)
        r2s = (3, split - overlap//2, 200, 200)

    for (rx1, ry1, rx2, ry2), d, color in [(r1s, d1, "#4fc3f7"), (r2s, d2, "#ef9a9a")]:
        parts.append(rect_svg(MARGIN+cx1+rx1, y0+ry1, rx2-rx1, ry2-ry1, color, color, 1.2, 0.08))
        svg = render_kage_bbox_stretch(d, glyph_db,
            MARGIN+cx1+rx1, y0+ry1, MARGIN+cx1+rx2, y0+ry2, color, 0.8, 1.2)
        if svg:
            parts.append(svg)

    # 画 bbox 线 (伸缩前)
    for (rx1, ry1, rx2, ry2), bb, color in [(r1s, bb1, "#4fc3f7"), (r2s, bb2, "#ef9a9a")]:
        # bbox 在目标矩形中的位置 (伸缩后会填满, 这里画出来就是矩形本身)
        pass

    parts.append(text_svg(MARGIN+cx1+CELL//2, y0-8, desc, 12, "#aaa"))
    parts.append(text_svg(MARGIN+cx1+CELL//2, y0+CELL+15, f"bbox伸缩 split={split}", 9, "#4f4"))

    # bbox 数值
    L_str = f"{c1}: bbox({bb1.x1},{bb1.y1}-{bb1.x2},{bb1.y2}) W={bb1.width()} H={bb1.height()}"
    R_str = f"{c2}: bbox({bb2.x1},{bb2.y1}-{bb2.x2},{bb2.y2}) W={bb2.width()} H={bb2.height()}"
    parts.append(text_svg(MARGIN+cx1+CELL//2, y0+CELL+30, L_str, 8, "#888"))
    parts.append(text_svg(MARGIN+cx1+CELL//2, y0+CELL+42, R_str, 8, "#888"))

parts.append('</svg>')

svg_path = os.path.join(OUT_DIR, "bbox_stretch_compare.svg")
with open(svg_path, 'w', encoding='utf-8') as f:
    f.write("\n".join(parts))
print(f"已保存: {svg_path}")

# 打印 bbox 数据
print("\n部件真实 bbox:")
for _, _, c1, c2, _, _ in TEST_CASES:
    k1 = get_variant_key(c1, 0)
    k2 = get_variant_key(c2, 1)
    bb1 = compute_true_bbox(glyph_db.get(k1, ''), glyph_db)
    bb2 = compute_true_bbox(glyph_db.get(k2, ''), glyph_db)
    print(f"  {c1}: ({bb1.x1},{bb1.y1})-({bb1.x2},{bb1.y2}) W={bb1.width()} H={bb1.height()}")
    print(f"  {c2}: ({bb2.x1},{bb2.y1})-({bb2.x2},{bb2.y2}) W={bb2.width()} H={bb2.height()}")
    print()
