#!/usr/bin/env python3
"""
变体查找 + KAGE 渲染验证
生成 HTML 文件，在浏览器中查看渲染结果
"""

import sys, os

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DUMP_PATH = r'D:\KAGE_GLYPH\dump_newest_only.txt'
BUNDLE_PATH = r'D:\2026harucpp\scripts\kage-bundle.js'

# ============================================================
# 1. 加载 dump: {name → data}
# ============================================================

def load_dump(path):
    print(f"加载 dump...")
    glyphs = {}
    with open(path, 'r', encoding='utf-8') as f:
        f.readline(); f.readline()  # 跳表头
        for line in f:
            if line[0] != ' ': continue
            pipe1 = line.find(' | ')
            if pipe1 < 0: continue
            name = line[1:pipe1].strip()
            pipe2 = line.find(' | ', pipe1 + 3)
            if pipe2 < 0: continue
            data = line[pipe2 + 3:].strip()
            if data:
                glyphs[name] = data
    print(f"  {len(glyphs)} 个字形")
    return glyphs


# ============================================================
# 2. IDS 解析
# ============================================================

SURROUND_OPS = set('⿴⿵⿶⿷⿸⿹⿺')

def is_ids_op(ch):
    return (0x2FF0 <= ord(ch) <= 0x2FFF) or ord(ch) == 0x31EF

def parse_ids(ids, pos=0, depth=0):
    """返回 [kind, op/char, name_or_None, children_list, ?modifier] — list 可变"""
    if pos >= len(ids): return None, pos
    ch = ids[pos]
    if not is_ids_op(ch):
        return ['leaf', ch, None, []], pos + 1
    op = ch
    pos += 1

    # 解析 ⿻ 后面的 [... ] 修饰符 (速成版 [a:b] 或完整版矩阵)
    modifier = None
    if op == '⿻' and pos < len(ids) and ids[pos] == '[':
        end = ids.find(']', pos)
        if end >= 0:
            modifier = ids[pos + 1:end]
            pos = end + 1

    arity = 3 if ch in '⿲⿳' else 2
    children = []
    for _ in range(arity):
        if pos >= len(ids): break
        child, pos = parse_ids(ids, pos, depth + 1)
        if child:
            children.append(child)

    if modifier is not None:
        return ['node', op, None, children, modifier], pos
    return ['node', op, None, children], pos


# ============================================================
# 3. 变体查找 (基于包围盒, 方案B)
# ============================================================

def position_suffix(position, op):
    op_cp = ord(op) if op else 0
    if op in SURROUND_OPS:
        if position == 0:
            # 外框按包围方向返回对应方位后缀
            suffix_map = {
                0x2FF4: 'j',   # ⿴ 全包: 日式全框
                0x2FF5: '01',  # ⿵ 上三包: 外框偏左
                0x2FF6: '04',  # ⿶ 下三包: 外框偏下
                0x2FF7: '01',  # ⿷ 左三包: 外框偏左
                0x2FF8: '02',  # ⿸ 左上包: 外框偏右腾出右下
                0x2FF9: '02',  # ⿹ 右上包: 外框偏右腾出左下
                0x2FFA: '04',  # ⿺ 左下包: 外框偏下腾出右上
                0x2FFC: '02',  # ⿼ 右三包: 外框偏右
            }
            return suffix_map.get(op_cp, 'j')
        else:
            # 内部件
            inner_map = {
                0x2FF8: '04', 0x2FF9: '04',  # 右下/左下
                0x2FFA: '03',  # 右上
            }
            return inner_map.get(op_cp, '01')
    if op_cp == 0x2FF0: return '01' if position == 0 else '02'
    if op_cp == 0x2FF1: return '03' if position == 0 else '04'
    if op_cp == 0x2FF2: return ['01','01','02'][position] if position < 3 else '01'
    if op_cp == 0x2FF3: return ['03','03','04'][position] if position < 3 else '04'
    return '01'


def surround_outer_suffixes(op):
    """包围外框的备选后缀列表, 按优先级排列"""
    op_cp = ord(op) if op else 0
    all_suffixes = {
        0x2FF4: ['j', '01', '02'],        # ⿴ 全包
        0x2FF5: ['01', 'j', '02'],        # ⿵ 上三包
        0x2FF6: ['04', 'j', '02'],        # ⿶ 下三包
        0x2FF7: ['01', 'j', '04'],        # ⿷ 左三包
        0x2FF8: ['02', 'j', '04'],        # ⿸ 左上包
        0x2FF9: ['j', '01'],            # ⿹ 右上包 (不用-02, 会把外框推太右)
        0x2FFA: ['04', 'j', '01'],        # ⿺ 左下包
        0x2FFC: ['02', 'j', '04'],        # ⿼ 右三包
    }
    return all_suffixes.get(op_cp, ['j'])


def compute_bbox(data, glyphs, visited=None):
    """递归计算 KAGE 数据的笔画包围盒 (0-200 坐标空间).
    返回 (min_x, min_y, max_x, max_y) 或 None"""
    if visited is None:
        visited = set()
    if not data:
        return None

    min_x, min_y = 200, 200
    max_x, max_y = 0, 0

    for stroke in data.split('$'):
        stroke = stroke.strip()
        if not stroke: continue
        parts = stroke.split(':')
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            # 99:sx:sy:x1:y1:x2:y2:name:unused:sx2:sy2
            x1 = int(parts[3]); y1 = int(parts[4])
            x2 = int(parts[5]); y2 = int(parts[6])
            ref_name = parts[7]
            # 剥离 @N 后缀
            base = ref_name.split('@')[0]
            if base not in visited and base in glyphs:
                visited.add(base)
                ref_box = compute_bbox(glyphs[base], glyphs, visited)
                if ref_box:
                    rx1, ry1, rx2, ry2 = ref_box
                    rw = rx2 - rx1 or 1; rh = ry2 - ry1 or 1
                    # 从 ref 坐标空间 → (0,200) 空间的线性映射
                    sx = (200 - rx1) / rw if rw else 1  # 占位比例
                    sy = (200 - ry1) / rh if rh else 1
                    # 映射到目标矩形
                    sx1 = x1 + (x2 - x1) * (rx1 / 200)
                    sy1 = y1 + (y2 - y1) * (ry1 / 200)
                    sx2 = x1 + (x2 - x1) * (rx2 / 200)
                    sy2 = y1 + (y2 - y1) * (ry2 / 200)
                    min_x = min(min_x, sx1); min_y = min(min_y, sy1)
                    max_x = max(max_x, sx2); max_y = max(max_y, sy2)
        else:
            # 笔画行: 字段 3 开始是坐标对 (x1,y1, x2,y2, ...)
            coords = [int(p) for p in parts[3:] if p.lstrip('-').isdigit()]
            for i in range(0, len(coords) - 1, 2):
                x, y = coords[i], coords[i+1]
                min_x = min(min_x, x); min_y = min(min_y, y)
                max_x = max(max_x, x); max_y = max(max_y, y)

    if min_x <= max_x and min_y <= max_y:
        return (min_x, min_y, max_x, max_y)
    return None


def score_variant(name, position, op, glyphs):
    """根据位置给变体打分: 越高越好"""
    data = glyphs.get(name)
    if not data:
        return -1, '无数据'

    bbox = compute_bbox(data, glyphs)
    if not bbox:
        return 0, '无笔画'
    min_x, min_y, max_x, max_y = bbox
    w = max_x - min_x or 1
    h = max_y - min_y or 1
    area = w * h

    op_cp = ord(op) if op else 0

    if op_cp == 0x2FF0:  # ⿰ 左右
        if position == 0:  # 左部件: 希望右边缘靠右
            return max_x, f'max_x={max_x} w={w}'
        else:  # 右部件: 希望左边缘靠左
            return 200 - min_x, f'min_x={min_x} w={w}'

    elif op_cp == 0x2FF1:  # ⿱ 上下
        if position == 0:  # 上部件: 希望下边缘靠下
            return max_y, f'max_y={max_y} h={h}'
        else:  # 下部件: 希望上边缘靠上
            return 200 - min_y, f'min_y={min_y} h={h}'

    # 包围/重叠/三分: 通用面积分
    return area, f'area={area}'


def score_surround_outer(name, op, glyphs):
    """围外框评分: 优先能包裹住内部件的变体"""
    data = glyphs.get(name)
    if not data:
        return -1, '无数据'
    bbox = compute_bbox(data, glyphs)
    if not bbox:
        return 0, '无笔画'
    min_x, min_y, max_x, max_y = bbox

    op_cp = ord(op)
    # 不同包围类型，期望的外框延伸方向不同
    if op_cp == 0x2FF9:  # ⿹ 右上包: 外框应向右下延伸，左边留空
        return min_x + max_y, f'left_gap={min_x} bot={max_y}'
    elif op_cp == 0x2FFA:  # ⿺ 左下包: 外框应向右上延伸，上边留空
        return max_x + (200 - min_y), f'right={max_x} top_gap={200-min_y}'
    elif op_cp == 0x2FF8:  # ⿸ 左上包: 外框应向右下延伸
        return max_x + max_y, f'right={max_x} bot={max_y}'
    elif op_cp == 0x2FF5:  # ⿵ 上三包: 外框应宽且向下延伸
        return max_x + max_y, f'right={max_x} bot={max_y}'
    elif op_cp == 0x2FF6:  # ⿶ 下三包: 外框应宽且向上
        return max_x + (200 - min_y), f'right={max_x} top_gap={200-min_y}'
    elif op_cp == 0x2FF7:  # ⿷ 左三包: 外框应向下延伸
        return max_y + max_x, f'bot={max_y} right={max_x}'
    elif op_cp == 0x2FFC:  # ⿼ 右三包: 外框应向下延伸
        return max_y + (200 - min_x), f'bot={max_y} left_gap={200-min_x}'
    elif op_cp == 0x2FF4:  # ⿴ 全包: 最大面积
        w = max_x - min_x or 1; h = max_y - min_y or 1
        return w * h, f'area={w*h}'
    # 默认面积
    w = max_x - min_x or 1; h = max_y - min_y or 1
    return w * h, f'area={w*h}'


def select_variant(char, position, op, glyphs):
    """为叶子字符选择最佳变体 (基于包围盒评分)"""
    cp = ord(char)
    h = f'{cp:04x}'
    suffix = position_suffix(position, op)

    # 包围外框: 尝试多个后缀候选
    if op in SURROUND_OPS and position == 0:
        candidates = []
        seen = set()
        for suf in surround_outer_suffixes(op):
            for pfx in ['-g', '-']:
                c = f'u{h}{pfx}{suf}'
                if c not in seen:
                    candidates.append(c)
                    seen.add(c)
        # 确保基础形式也在候选里
        for c in [f'u{h}-j', f'u{h}']:
            if c not in seen:
                candidates.append(c)
                seen.add(c)

        best = None
        best_score = -1
        best_reason = ''
        for c in candidates:
            if c not in glyphs:
                continue
            score, reason = score_surround_outer(c, op, glyphs)
            if score > best_score:
                best_score = score
                best = c
                best_reason = reason

        if best:
            return best, best_score, best_reason
        # 回退到普通查找
        return select_variant_fallback(char, position, op, glyphs)

    # 普通查找
    return select_variant_fallback(char, position, op, glyphs)


def select_variant_fallback(char, position, op, glyphs):
    """标准变体查找"""
    cp = ord(char)
    h = f'{cp:04x}'
    suffix = position_suffix(position, op)

    candidates = [
        f'u{h}-g{suffix}',
        f'u{h}-{suffix}',
        f'u{h}-j',
        f'u{h}',
    ]

    best = None
    best_score = -1
    best_reason = ''
    for c in candidates:
        if c not in glyphs:
            continue
        score, reason = score_variant(c, position, op, glyphs)
        if score > best_score:
            best_score = score
            best = c
            best_reason = reason

    return best, best_score, best_reason


# ============================================================
# 4. 复合构建
# ============================================================

def op_name(op):
    names = {0x2FF0:'⿰',0x2FF1:'⿱',0x2FF2:'⿲',0x2FF3:'⿳',
             0x2FF4:'⿴',0x2FF5:'⿵',0x2FF6:'⿶',0x2FF7:'⿷',
             0x2FF8:'⿸',0x2FF9:'⿹',0x2FFA:'⿺',0x2FFB:'⿻',0x31EF:'㇯'}
    return names.get(ord(op), op)

# 包围矩形参数（0-200 坐标空间）
def surround_rects(op, outer_name=None, composites=None, glyphs=None):
    """返回 [(x1,y1,x2,y2), ...] for (outer, inner)。

    外框永远占全画布(0,0,200,200)以形成完整包裹形态。
    内部件根据外框 bbox 定位到开口区域。"""
    op_cp = ord(op) if op else 0
    M = 8  # 通用边距

    # 先获取外框 bbox
    outer_bbox = None
    if outer_name and composites is not None and glyphs is not None:
        outer_bbox = get_component_bbox(outer_name, composites, glyphs)

    if not outer_bbox:
        # 无 bbox 时的静态回退
        fb = {
            0x2FF4: [(0, 0, 200, 200), (40, 35, 160, 165)],   # ⿴
            0x2FF5: [(0, 0, 200, 200), (25, 40, 175, 197)],   # ⿵
            0x2FF6: [(0, 0, 200, 200), (25, 3, 175, 90)],     # ⿶
            0x2FF7: [(0, 0, 200, 200), (100, 25, 197, 175)],  # ⿷
            0x2FF8: [(0, 0, 200, 200), (100, 100, 197, 197)], # ⿸
            0x2FF9: [(0, 0, 200, 200), (3, 35, 155, 197)],    # ⿹
            0x2FFA: [(0, 0, 200, 200), (55, 3, 197, 170)],    # ⿺
            0x2FFC: [(0, 0, 200, 200), (3, 25, 100, 175)],    # ⿼
        }
        return fb.get(op_cp)

    omin_x, omin_y, omax_x, omax_y = outer_bbox
    outer = (0, 0, 200, 200)  # 外框全画布

    # 根据包围类型计算内部件位置
    if op_cp == 0x2FF7:  # ⿷ 左三包: 开口在右侧, 内部件在 bbox 内偏右
        inner = (omin_x + 28, omin_y + M,
                 min(omax_x, 197), omax_y - M)

    elif op_cp == 0x2FFC:  # ⿼ 右三包: 开口在左侧
        inner = (max(omin_x, 3), omin_y + M,
                 omax_x - 28, omax_y - M)

    elif op_cp == 0x2FF5:  # ⿵ 上三包: 开口在下方, 内部件从 bbox 顶部开始
        inner_y1 = int(omin_y + (omax_y - omin_y) * 0.08)
        inner = (omin_x + M, max(inner_y1, 15),
                 omax_x - M, 197)

    elif op_cp == 0x2FF6:  # ⿶ 下三包: 开口在上方
        inner_y2 = int(omin_y + (omax_y - omin_y) * 0.45)
        inner = (omin_x + M, 3,
                 omax_x - M, min(inner_y2, 130))

    elif op_cp == 0x2FF4:  # ⿴ 全包: 内部件居中缩放在 bbox 内
        cx, cy = (omin_x + omax_x) / 2, (omin_y + omax_y) / 2
        iw = (omax_x - omin_x) * 0.55
        ih = (omax_y - omin_y) * 0.55
        inner = (cx - iw/2, cy - ih/2, cx + iw/2, cy + ih/2)

    elif op_cp == 0x2FF8:  # ⿸ 左上包: 开口在右下, 内部件在 bbox 外右下
        if omax_x > 140 or omax_y > 140:
            inner = (95, 95, 197, 197)
        else:
            inner = (omax_x + M, omax_y + M, 197, 197)

    elif op_cp == 0x2FF9:  # ⿹ 右上包: 开口在左下, 内部件在左下半区
        if omin_x < 60 or omax_y > 140:
            inner = (3, 35, 155, 197)
        else:
            inner_x2 = min(omin_x - M, 85)
            inner_y1 = int(omax_y * 0.40)
            inner = (3, inner_y1, inner_x2, 197)

    elif op_cp == 0x2FFA:  # ⿺ 左下包: 开口在右上
        if omax_x > 140 or omin_y < 60:
            inner = (55, 3, 197, 180)
        else:
            inner = (int(omax_x * 0.5), 3, 197, int(omin_y + (200 - omin_y) * 0.6))

    else:
        inner = (M, M, 200-M, 200-M)

    # 钳制到有效范围
    def clamp_rect(r):
        x1, y1, x2, y2 = r
        x1 = max(3, min(x1, 197))
        y1 = max(3, min(y1, 197))
        x2 = max(x1 + 10, min(x2, 197))
        y2 = max(y1 + 10, min(y2, 197))
        return (int(x1), int(y1), int(x2), int(y2))

    return [outer, clamp_rect(inner)]


def get_component_bbox(name, composites, glyphs):
    """获取部件的包围盒 (查阅复合数据和原始字形)"""
    data = composites.get(name) or glyphs.get(name, '')
    if data:
        return compute_bbox(data, glyphs)
    return None


def compute_dynamic_overlap(op, child_names, composites, glyphs):
    """根据子部件包围盒，计算额外的重叠量。
    部件内边缘空白越多 → 重叠越大 → 部件靠得更近。
    返回 overlap (px), 用于 ⿰ 的左右重叠和 ⿱ 的上下重叠。"""
    bboxes = [get_component_bbox(n, composites, glyphs) for n in child_names]
    valid = [b for b in bboxes if b]
    if len(valid) < 2:
        return 6  # 默认重叠

    op_cp = ord(op)
    (_, _, lx2, _) = bboxes[0]  # 第一位 (左/上) 内容右/下边界
    (rx1, _, _, _) = bboxes[1]  # 第二位 (右/下) 内容左/上边界

    if op_cp == 0x2FF0:  # ⿰: 左部件右空白 + 右部件左空白
        left_gap = 200 - lx2   # 左部件右侧空了多少
        right_gap = rx1        # 右部件左侧空了多少
    else:  # ⿱: 上部件下空白 + 下部件上空白
        left_gap = 200 - lx2   # 上部件下方空了多少
        right_gap = rx1        # 下部件上方空了多少

    extra = int((left_gap + right_gap) * 0.22)
    overlap = min(6 + extra, 60)  # 6~60px
    return overlap


def count_horizontal_segments(comp_name, composites, glyphs, visited=None):
    """估算部件的水平结构数量。

    递归展开 type-99 引用，统计水平笔画（类型1）的 Y 坐标聚类数。
    这对于 ⿻[a:b] 修饰符中的水平段计数是必需的。"""
    if visited is None:
        visited = set()
    if comp_name in visited:
        return 1
    visited.add(comp_name)

    data = composites.get(comp_name) or glyphs.get(comp_name, '')
    if not data:
        return 1

    ys = []

    for stroke in data.split('$'):
        parts = stroke.strip().split(':')
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            ref = parts[7]
            base = ref.split('@')[0]
            n = count_horizontal_segments(base, composites, glyphs, visited)
            if n > 0:
                # 将子部件的水平段均匀分布到目标矩形
                x1, y1 = int(parts[3]), int(parts[4])
                x2, y2 = int(parts[5]), int(parts[6])
                for i in range(n):
                    frac = i / max(n - 1, 1)
                    ys.append(y1 + (y2 - y1) * frac)
        elif kind == 1:  # 横笔画
            coords = [int(p) for p in parts[3:] if p.lstrip('-').isdigit()]
            if coords:
                stroke_ys = [coords[i+1] for i in range(0, len(coords)-1, 2)]
                ys.append(sum(stroke_ys) / len(stroke_ys))

    if not ys:
        return 1
    # 按 Y 聚类 (容差 8px)，避免把同一个横的数段计为多段
    ys.sort()
    clusters = []
    for y in ys:
        if not clusters or y - clusters[-1] > 8:
            clusters.append(y)
    return len(clusters)


def get_horizontal_segment_ys(comp_name, n_segments, composites, glyphs, visited=None):
    """获取水平段的具体 Y 坐标。

    n_segments 由 count_horizontal_segments 提供。
    返回包含 n_segments 个 Y 坐标的列表（0-200）。"""
    if visited is None:
        visited = set()
    if comp_name in visited:
        return [0, 200][:n_segments]
    visited.add(comp_name)

    data = composites.get(comp_name) or glyphs.get(comp_name, '')
    if not data:
        return [i * 200 / max(n_segments - 1, 1) for i in range(n_segments)]

    ys = []

    for stroke in data.split('$'):
        parts = stroke.strip().split(':')
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            ref = parts[7]
            base = ref.split('@')[0]
            x1, y1 = int(parts[3]), int(parts[4])
            x2, y2 = int(parts[5]), int(parts[6])
            sub_n = count_horizontal_segments(base, composites, glyphs, set())
            if sub_n > 0:
                for i in range(sub_n):
                    frac = i / max(sub_n - 1, 1)
                    ys.append(y1 + (y2 - y1) * frac)
        elif kind == 1:  # 横笔画
            coords = [int(p) for p in parts[3:] if p.lstrip('-').isdigit()]
            if coords:
                stroke_ys = [coords[i+1] for i in range(0, len(coords)-1, 2)]
                ys.append(sum(stroke_ys) / len(stroke_ys))

    if not ys:
        return [i * 200 / max(n_segments - 1, 1) for i in range(n_segments)]

    ys.sort()
    # 聚为 n_segments 类
    clusters = [ys[0]]
    for y in ys[1:]:
        if y - clusters[-1] > 10:
            clusters.append(y)
        else:
            clusters[-1] = (clusters[-1] + y) / 2  # 均值
        if len(clusters) >= n_segments:
            break

    # 补齐或截断
    while len(clusters) < n_segments:
        # 用均匀分布补齐
        clusters.append(clusters[-1] + (200 - clusters[-1]) / (n_segments - len(clusters) + 1))
    return clusters[:n_segments]


def apply_overlap_modifier(child_name_0, child_name_1, modifier, composites, glyphs):
    """根据 ⿻[a:b] 速成版修饰符计算字₁ (纵向件) 的 Y 范围。

    modifier: "a:b" 或 ":b" 或 "a:" 或 "a" 等
    返回 (y1, y2) for child 0 (vertical), 或 None 表示使用默认全重叠。"""
    if not modifier:
        return None

    # 先结算子部件，确保可以从 composites 获取它们的 composite 数据
    n_seg = count_horizontal_segments(child_name_1, composites, glyphs, set())
    if n_seg < 1:
        return None

    seg_ys = get_horizontal_segment_ys(child_name_1, n_seg, composites, glyphs, set())
    if not seg_ys:
        return None

    parts = modifier.split(':')
    a_str = parts[0].strip() if len(parts) > 0 else ''
    b_str = parts[1].strip() if len(parts) > 1 else ''

    # 解析 a (纵向件顶部在第 a 横之下，即接触在第 a+1 横上方)
    if a_str == '':
        top_y = 3  # 从顶部开始
    else:
        a = int(a_str)
        if a < 0:
            a = len(seg_ys) + a
        a = max(0, min(a, len(seg_ys) - 1))
        # 顶部在 seg_ys[a] 之下一点点
        top_y = seg_ys[a] + 6

    # 解析 b (纵向件底部在第 b 横之上)
    if b_str == '':
        bottom_y = 197  # 延伸到底部
    else:
        b = int(b_str)
        if b < 0:
            b = len(seg_ys) + b
        b = max(0, min(b, len(seg_ys) - 1))
        bottom_y = seg_ys[b] - 6

    # 确保合理范围
    top_y = max(3, min(top_y, 197))
    bottom_y = max(3, min(bottom_y, 197))
    if bottom_y <= top_y:
        bottom_y = top_y + 10
    return (top_y, bottom_y)


def build_composite(node, parent_op, position, glyphs, counter, composites):
    """递归构建 KAGE 复合数据。"""
    kind = node[0]

    if kind == 'leaf':
        char = node[1]
        variant, score, reason = select_variant(char, position, parent_op, glyphs)
        node[2] = variant
        node.append((score, reason))
        return variant, None, [variant] if variant else []

    # 内部节点: 先递归解析所有子节点
    op = node[1]
    children = node[3]
    arity = len(children)
    op_cp = ord(op)
    is_surround = op in SURROUND_OPS
    # 提取 ⿻ 修饰符 (node[4] 如果存在)
    overlap_mod = node[4] if len(node) > 4 and node[4] else None

    # 第一遍: 递归处理所有子节点, 收集名字
    child_names = []
    all_deps = []
    for child in children:
        child_name, _, deps = build_composite(child, op, child_names.__len__(), glyphs, counter, composites)
        if child_name is None:
            return None, None, []
        child_names.append(child_name)
        all_deps.extend(deps)

    # ⿰⿱ 的动态重叠计算
    dyn_overlap = None
    if op_cp in (0x2FF0, 0x2FF1):
        dyn_overlap = compute_dynamic_overlap(op, child_names, composites, glyphs)

    # ⿻ 重叠修饰符
    overlap_y = None  # (y1, y2) for child 0 (vertical)
    if op_cp == 0x2FFB and overlap_mod:
        overlap_y = apply_overlap_modifier(child_names[0], child_names[1],
                                            overlap_mod, composites, glyphs)

    # 第二遍: 根据调整结果分配矩形
    child_infos = []
    for i in range(arity):
        child_name = child_names[i]
        x1, y1, x2, y2 = 0, 0, 200, 200

        if is_surround:
            rects = surround_rects(op, child_names[0] if child_names else None,
                                    composites, glyphs)
            if rects and i < len(rects):
                x1, y1, x2, y2 = rects[i]
        elif arity == 3:
            if op_cp == 0x2FF2:
                w = 200 // 3
                x1, x2 = i * w + 1, (i+1) * w + 1
                y1, y2 = 3, 197
            else:
                h = 200 // 3
                y1, y2 = i * h + 1, (i+1) * h + 1
                x1, x2 = 3, 197
        elif op_cp == 0x2FFB:  # ⿻
            if overlap_y and i == 0:
                x1, x2 = 3, 197
                y1, y2 = overlap_y
            else:
                x1, y1, x2, y2 = 0, 0, 200, 200
        elif op_cp == 0x2FF0:  # ⿰
            o = dyn_overlap if dyn_overlap else 6
            mid = 100
            if i == 0: x1, x2 = 3, mid + o // 2
            else:      x1, x2 = mid - o // 2, 197
            y1, y2 = 3, 197
        elif op_cp == 0x2FF1:  # ⿱
            o = dyn_overlap if dyn_overlap else 6
            mid = 100
            if i == 0: y1, y2 = 3, mid + o // 2
            else:      y1, y2 = mid - o // 2, 197
            x1, x2 = 3, 197
        else:
            x1, y1, x2, y2 = 0, 0, 200, 200

        child_infos.append((child_name, x1, y1, x2, y2))

    # 生成复合名和数据
    next_id[0] += 1
    comp_name = f'_c{next_id[0]}'
    strokes = []
    for cn, x1, y1, x2, y2 in child_infos:
        strokes.append(f'99:0:0:{x1}:{y1}:{x2}:{y2}:{cn}:0:0:0')
    comp_data = '$'.join(strokes)

    node[2] = comp_name
    node.append(comp_data)  # node[4] = data, 不覆盖 node[3] children
    composites[comp_name] = comp_data  # 收集所有中间复合
    return comp_name, comp_data, all_deps


# ============================================================
# 5. 生成 HTML
# ============================================================

def generate_html(ids, root, comp_data, all_glyph_data, bundle_js):
    """生成可打开的 HTML 渲染文件"""
    # 装入 JS 需要的字形数据
    js_loads = []
    for name, data in all_glyph_data.items():
        # 转义 JS 字符串
        escaped = data.replace('\\', '\\\\').replace("'", "\\'")
        js_loads.append(f"loadGlyph('{name}', '{escaped}');")

    # 装载复合数据
    if comp_data:
        escaped_comp = comp_data.replace('\\', '\\\\').replace("'", "\\'")
        root_name = root[2]
        js_loads.append(f"loadGlyph('{root_name}', '{escaped_comp}');")

    js_load_str = '\n    '.join(js_loads)
    root_name = root[2]

    # 解析树结构为可视化文本
    def tree_text(node, indent=0):
        prefix = '  ' * indent
        kind = node[0]
        if kind == 'leaf':
            ch = node[1]
            v = node[2] or '?'
            info = ''
            if len(node) > 4 and node[4]:
                score, reason = node[4]
                info = f'  [{reason}]'
            return f"{prefix}├─ '{ch}' → {v}{info}"
        op = op_name(node[1])
        name = node[2] or '?'
        mod_info = ''
        if len(node) > 4 and node[4] and isinstance(node[4], str):
            mod_info = f' [{node[4]}]'
        lines = [f"{prefix}├─ {op}{mod_info} [{name}]"]
        for c in node[3]:
            lines.append(tree_text(c, indent + 1))
        return '\n'.join(lines)

    tree = tree_text(root)

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>KAGE 渲染 - {ids}</title>
<style>
  body {{ font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #eee; }}
  h2 {{ color: #e94560; }}
  .grid {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .card {{ background: #f5f5f5; border-radius: 8px; padding: 16px; text-align: center; }}
  .card img {{ background: white; border-radius: 4px; }}
  .card .label {{ font-size: 12px; color: #555; margin-top: 8px; }}
  pre {{ background: #0f3460; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; }}
</style></head><body>
<h2>表外字 KAGE 渲染验证</h2>
<p>IDS: <b style="font-size:24px;color:#e94560">{ids}</b></p>

<h3>选中的变体</h3>
<pre>{tree}</pre>

<h3>渲染结果</h3>
<div class="grid">
  <div class="card">
    <div id="composite"></div>
    <div class="label">合成结果 ({root_name})</div>
  </div>
</div>
<div class="grid" id="components"></div>

<script>
// KAGE bundle
{bundle_js}

// 装载字形数据
{js_load_str}

// 渲染合成结果
try {{
  var svg = renderGlyph('{root_name}', false);
  document.getElementById('composite').innerHTML = svg;
}} catch(e) {{
  document.getElementById('composite').innerHTML = '<p style="color:red">渲染错误: ' + e.message + '</p>';
}}
</script>
</body></html>'''


# ============================================================
# Main
# ============================================================

next_id = [0]

def main():
    if not os.path.exists(DUMP_PATH):
        print(f"错误: dump 不存在 {DUMP_PATH}")
        return
    if not os.path.exists(BUNDLE_PATH):
        print(f"错误: kage-bundle.js 不存在 {BUNDLE_PATH}")
        return

    glyphs = load_dump(DUMP_PATH)

    with open(BUNDLE_PATH, 'r', encoding='utf-8') as f:
        bundle_js = f.read()

    tests = [
        "⿰石另",
        "⿱⿰亻山木",
        "⿵冂⿱乂乂",
        "⿺辶律",
        "⿹勹巳","⿴口山","⿹𠃌口","勹"
    ]

    for ids in tests:
        next_id[0] = 0
        print(f"\n{'='*60}")
        print(f"渲染: {ids}")
        print(f"{'='*60}")

        root, end = parse_ids(ids)
        if root is None or end != len(ids):
            print(f"  解析失败")
            continue

        composites = {}
        comp_name, comp_data, dep_names = build_composite(root, None, 0, glyphs, next_id, composites)

        if comp_name is None:
            print(f"  构建失败（有缺失部件）")
            continue

        print(f"  根名: {comp_name}")
        print(f"  中间复合: {len(composites)} 个")
        print(f"  叶子依赖: {len(set(dep_names))} 个")

        # 收集所有需要的字形数据
        all_data = dict(composites)  # 包含所有中间复合!
        for name in set(dep_names):
            if name in glyphs:
                all_data[name] = glyphs[name]
            else:
                print(f"  警告: {name} 数据缺失")

        # 递归展开 type-99 依赖
        expanded = set()
        queue = list(all_data.keys())
        while queue:
            name = queue.pop()
            if name in expanded:
                continue
            expanded.add(name)
            data = all_data.get(name, '')
            for stroke in data.split('$'):
                if stroke.startswith('99:'):
                    parts = stroke.split(':')
                    if len(parts) >= 8:
                        ref = parts[7]
                        # 去除 @N 后缀
                        at = ref.find('@')
                        if at > 0:
                            ref_base = ref[:at]
                        else:
                            ref_base = ref
                        if ref_base not in all_data and ref_base in glyphs:
                            all_data[ref_base] = glyphs[ref_base]
                            queue.append(ref_base)
                        elif ref not in all_data and ref in glyphs:
                            all_data[ref] = glyphs[ref]
                            queue.append(ref)

        print(f"  总字形: {len(all_data)} (含递归依赖)")

        # 生成 HTML
        html = generate_html(ids, root, comp_data, all_data, bundle_js)
        out_path = f'D:/2026harucpp/scripts/render_{ids.replace(chr(0x2FF0),"LR").replace(chr(0x2FF1),"TB")}.html'
        # 简化文件名
        safe = ids
        for c in '⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻[]:':
            safe = safe.replace(c, '_')
        out_path = f'D:/2026harucpp/scripts/render_{safe}.html'

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  输出: {out_path}")

    print(f"\n{'='*60}")
    print("完成! 在浏览器中打开 HTML 文件查看渲染结果。")


if __name__ == '__main__':
    main()
