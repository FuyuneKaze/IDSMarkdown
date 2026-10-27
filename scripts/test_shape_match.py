#!/usr/bin/env python3
"""
形状匹配变体选择 — 原型验证
思路: 区域锁定 → bbox空间分配 → 形状匹配评分
"""

import sys, os, math
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DUMP_PATH = r'D:\KAGE_GLYPH\dump_newest_only.txt'

# ⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻
SURROUND_OPS = set('⿴⿵⿶⿷⿸⿹⿺')

# ---- 位置后缀映射 (从已验证的 C++ 算法) ----

def extract_position_code(sfx):
    """从后缀中提取位置码 (最后的两位数字, 跳过 -var-NNN)

    '-g04' → '04'
    '-03-var-004' → '03'  (var之前的部分)
    '-j' → 'j'
    '' → '' (基础形)
    """
    if not sfx: return ''
    # 去掉尾部的 -var-NNN
    var_idx = sfx.find('-var-')
    core = sfx[:var_idx] if var_idx > 0 else sfx
    # 找最后两位数字
    if len(core) >= 2 and core[-2:].isdigit():
        return core[-2:]
    if len(core) >= 1 and core[-1].isdigit():
        return core[-1]
    # 可能只有地区码: '-g', '-j' 等
    if len(core) >= 1 and core[-1].isalpha():
        return core[-1]
    return core


def position_suffix(position, op_cp):
    """返回该位置期望的后缀"""
    if op_cp in SURROUND_OP_CODES:
        if position == 0:
            m = {0x2FF4:'j',0x2FF5:'01',0x2FF6:'04',0x2FF7:'01',
                 0x2FF8:'j',0x2FF9:'j',0x2FFA:'04',0x2FFC:'02'}
            return m.get(op_cp, 'j')
        else:
            m = {0x2FF8:'04',0x2FF9:'04',0x2FFA:'03'}
            return m.get(op_cp, '01')
    if op_cp == 0x2FF0: return '01' if position == 0 else '02'
    if op_cp == 0x2FF1: return '03' if position == 0 else '04'
    if op_cp == 0x2FF2: return ['01','01','02'][position] if position < 3 else '01'
    if op_cp == 0x2FF3: return ['03','03','04'][position] if position < 3 else '04'
    return '01'


SURROUND_OP_CODES = {0x2FF4,0x2FF5,0x2FF6,0x2FF7,0x2FF8,0x2FF9,0x2FFA,0x2FFC}

# ============================================================
# 1. 加载 & 变体索引
# ============================================================

def load_dump(path):
    glyphs = {}
    with open(path, 'r', encoding='utf-8') as f:
        f.readline(); f.readline()
        for line in f:
            if line[0] != ' ': continue
            pipe1 = line.find(' | ')
            if pipe1 < 0: continue
            name = line[1:pipe1].strip()
            pipe2 = line.find(' | ', pipe1 + 3)
            if pipe2 < 0: continue
            data = line[pipe2 + 3:].strip()
            if data: glyphs[name] = data
    print(f"  加载 {len(glyphs)} 个字形")
    return glyphs


def extract_base(name):
    """从变体名提取基础字形名。u79be-01-var-001 → u79be, u215d7 → u215d7"""
    if not name.startswith('u'): return None
    # 在 u 之后找第一个非 hex 字符位置
    end = 1
    while end < len(name) and name[end] in '0123456789abcdef':
        end += 1
    if end <= 1: return None
    return name[:end]


def build_variant_index(glyphs):
    """为每个 Unicode 字符建立变体列表索引 u<hex> → [variant_names]"""
    idx = defaultdict(list)
    for name in glyphs:
        base = extract_base(name)
        if base:
            idx[base].append(name)
    print(f"  变体索引: {len(idx)} 个字符")
    return idx


def region_variants(char_hex, variant_idx, glyphs, region='g'):
    """返回某字符在指定区域标准下的所有候选变体。"""
    base = 'u' + char_hex
    all_vars = variant_idx.get(base, [])
    if not all_vars:
        return []

    def tier(name):
        """排序权重: 地区匹配 > 日标 > 位置数字 > var > 基础形"""
        suffix = name[len(base):]  # 去掉 uXXXX 后的部分
        if not suffix:
            return 0  # 基础形 uXXXX
        if suffix.startswith('-' + region):
            return 1  # -g, -g01, -g05, ...
        if suffix.startswith('-j'):
            return 2  # 日标 fallback
        if suffix.startswith('-') and len(suffix) > 1 and suffix[1].isdigit():
            return 3  # 纯位置变体 -01, -02, ...
        if suffix.startswith('-var-'):
            return 4
        if suffix.startswith('-itaiji-'):
            return 5
        return 6  # -k, -t, -h 等

    # 过滤: 排除明确的其他地区标准
    def exclude_region(name):
        suffix = name[len(base):]
        return suffix.startswith('-k') or suffix.startswith('-t') or suffix.startswith('-h')

    candidates = [n for n in all_vars if not exclude_region(n)]
    candidates.sort(key=tier)
    return candidates


# ============================================================
# 2. Bbox 计算
# ============================================================

def compute_bbox(data, glyphs, visited=None):
    if visited is None: visited = set()
    if not data: return None
    min_x, min_y, max_x, max_y = 200, 200, 0, 0

    for stroke in data.split('$'):
        stroke = stroke.strip()
        if not stroke: continue
        parts = stroke.split(':')
        try: kind = int(parts[0])
        except: continue

        if kind == 99 and len(parts) >= 8:
            x1, y1 = int(parts[3]), int(parts[4])
            x2, y2 = int(parts[5]), int(parts[6])
            ref = parts[7].split('@')[0]
            if ref not in visited and ref in glyphs:
                visited.add(ref)
                rb = compute_bbox(glyphs[ref], glyphs, visited)
                if rb:
                    rx1, ry1, rx2, ry2 = rb
                    min_x = min(min_x, x1 + (x2-x1) * rx1 / 200)
                    min_y = min(min_y, y1 + (y2-y1) * ry1 / 200)
                    max_x = max(max_x, x1 + (x2-x1) * rx2 / 200)
                    max_y = max(max_y, y1 + (y2-y1) * ry2 / 200)
        else:
            coords = [int(p) for p in parts[3:] if p.lstrip('-').isdigit()]
            for i in range(0, len(coords)-1, 2):
                min_x = min(min_x, coords[i])
                min_y = min(min_y, coords[i+1])
                max_x = max(max_x, coords[i])
                max_y = max(max_y, coords[i+1])

    return (min_x, min_y, max_x, max_y) if min_x <= max_x else None


def bbox_of(name, glyphs, cache):
    if name in cache: return cache[name]
    data = glyphs.get(name, '')
    if data:
        bb = compute_bbox(data, glyphs)
        cache[name] = bb
        return bb
    cache[name] = None
    return None


def bbox_aspect(bb):
    """返回 (w, h, aspect_ratio)"""
    if not bb: return 0, 0, 1.0
    w = bb[2] - bb[0] or 1
    h = bb[3] - bb[1] or 1
    return w, h, w / h


# ============================================================
# 3. 空间分配 (复杂度驱动)
# ============================================================

def stroke_count(data, glyphs, visited=None):
    """估算笔画数 (用于复杂度)"""
    if visited is None: visited = set()
    if not data: return 0
    count = 0
    for stroke in data.split('$'):
        stroke = stroke.strip()
        if not stroke: continue
        parts = stroke.split(':')
        try: kind = int(parts[0])
        except: continue
        if kind == 99 and len(parts) >= 8:
            ref = parts[7].split('@')[0]
            if ref not in visited and ref in glyphs:
                visited.add(ref)
                count += stroke_count(glyphs[ref], glyphs, visited)
        else:
            count += 1
    return count


def allocate_slots(op_cp, child_bboxes, child_names, glyphs):
    """分配矩形空间。返回 [(x1,y1,x2,y2), ...]

    初版: ⿰⿱ 按自然 bbox 比例分配, ⿸⿹⿺ 外框全画布 + 内部件 bbox 驱动
    """
    n = len(child_bboxes)

    if op_cp == 0x2FF0:  # ⿰ 左右: 按自然宽度比例
        widths = []
        for bb in child_bboxes:
            if bb: widths.append(bb[2] - bb[0])
            else: widths.append(50)
        total_w = sum(widths) or 1
        slots = []
        cx = 3
        for i in range(n):
            w = max(30, int(194 * widths[i] / total_w))
            if i == n - 1: w = 197 - cx
            slots.append((cx, 3, cx + w, 197))
            cx += w
        return slots

    elif op_cp == 0x2FF1:  # ⿱ 上下: 按自然高度比例
        heights = []
        for bb in child_bboxes:
            if bb: heights.append(bb[3] - bb[1])
            else: heights.append(50)
        total_h = sum(heights) or 1
        slots = []
        cy = 3
        for i in range(n):
            h = max(25, int(194 * heights[i] / total_h))
            if i == n - 1: h = 197 - cy
            slots.append((3, cy, 197, cy + h))
            cy += h
        return slots

    elif op_cp in SURROUND_OP_CODES:
        # 包围: 外框全画布, 内部件位置用固定比例 (bbox 只用来判断外框是窄靠型还是全宽型)
        outer_bb = child_bboxes[0] if child_bboxes else None

        if op_cp == 0x2FF8:  # ⿸ 左上包: 内部在右下 ~45%区域
            inner = (85, 100, 197, 197)
        elif op_cp == 0x2FF9:  # ⿹ 右上包: 内部在左下半区
            inner = (3, 40, 150, 197)
        elif op_cp == 0x2FFA:  # ⿺ 左下包: 内部在右上
            inner = (55, 3, 197, 170)
        elif op_cp == 0x2FF5:  # ⿵ 上三包
            if outer_bb:
                inner_y1 = max(outer_bb[1] + 12, 20)
                ox1, oy1, ox2, oy2 = outer_bb
                inner = (ox1 + 8, inner_y1, ox2 - 8, 197)
            else:
                inner = (20, 30, 180, 197)
        elif op_cp == 0x2FF6:  # ⿶ 下三包
            inner = (20, 3, 180, 100)
        elif op_cp == 0x2FF7:  # ⿷ 左三包
            if outer_bb:
                inner = (outer_bb[0] + 28, outer_bb[1] + 8,
                         min(outer_bb[2], 180), outer_bb[3] - 8)
            else:
                inner = (50, 15, 180, 185)
        elif op_cp == 0x2FFC:  # ⿼ 右三包 (少见)
            inner = (3, 15, 120, 185)
        elif op_cp == 0x2FF4:  # ⿴ 全包
            if outer_bb:
                cx, cy = (outer_bb[0]+outer_bb[2])/2, (outer_bb[1]+outer_bb[3])/2
                iw, ih = (outer_bb[2]-outer_bb[0])*0.55, (outer_bb[3]-outer_bb[1])*0.55
                inner = (cx-iw/2, cy-ih/2, cx+iw/2, cy+ih/2)
            else:
                inner = (40, 35, 160, 165)
        else:
            inner = (30, 30, 170, 170)

        def clamp(r):
            x1,y1,x2,y2 = r
            return (max(3,min(x1,197)), max(3,min(y1,197)),
                    max(x1+10,min(x2,197)), max(y1+10,min(y2,197)))
        return [(0,0,200,200), clamp(inner)]

    else:
        return [(0,0,200,200)] * n


# ============================================================
# 4. 形状匹配评分
# ============================================================

def shape_match_score(variant_name, slot, glyphs, bbox_cache):
    """评分变体 bbox 与目标 slot 的匹配度。

    返回 (score, reason) — score 越高越好，范围 0~1
    综合考虑: 面积适配 + 宽高比适配
    """
    bb = bbox_of(variant_name, glyphs, bbox_cache)
    if not bb:
        return 0, '无bbox'

    vx1, vy1, vx2, vy2 = bb
    vw = (vx2 - vx1) or 1
    vh = (vy2 - vy1) or 1
    v_area = vw * vh
    v_aspect = vw / vh

    sx1, sy1, sx2, sy2 = slot
    sw = sx2 - sx1
    sh = sy2 - sy1
    s_area = sw * sh
    s_aspect = sw / sh if sh else 1

    # 面积匹配: 变体面积 / slot 面积, 越接近 1 越好
    # 但要惩罚变体比 slot 大太多 (会溢出)
    area_ratio = min(v_area, s_area) / max(v_area, s_area)

    # 宽高比匹配: 形状越接近越好
    aspect_ratio = min(v_aspect, s_aspect) / max(v_aspect, s_aspect) if max(v_aspect, s_aspect) > 0 else 0

    # 综合分: 面积权重 0.3, 宽高比权重 0.7 (形状比大小更重要)
    score = area_ratio * 0.3 + aspect_ratio * 0.7

    return score, f'area={area_ratio:.2f} aspect={aspect_ratio:.2f} v={vw}×{vh} s={sw}×{sh}'


# ============================================================
# 5. 主流程
# ============================================================

def is_ids_op(ch):
    return (0x2FF0 <= ord(ch) <= 0x2FFF) or ord(ch) == 0x31EF


def parse_ids(ids, pos=0):
    if pos >= len(ids): return None, pos
    ch = ids[pos]
    if not is_ids_op(ch):
        return ('leaf', ch, []), pos + 1
    op = ch; pos += 1
    arity = 3 if ch in '⿲⿳' else 2
    children = []
    for _ in range(arity):
        if pos >= len(ids): break
        c, pos = parse_ids(ids, pos)
        if c: children.append(c)
    return ('node', op, children), pos


def process_ids(ids, region='g', glyphs=None, variant_idx=None):
    """用形状匹配算法处理一条 IDS，返回选中的变体信息。"""
    root, end = parse_ids(ids)
    if root is None or end != len(ids):
        return None, "解析失败"

    bbox_cache = {}

    def process_node(node, parent_op=None, position=0):
        kind = node[0]
        if kind == 'leaf':
            ch = node[1]
            h = f'{ord(ch):04x}'
            candidates = region_variants(h, variant_idx, glyphs, region)
            return {'char': ch, 'hex': h, 'candidates': candidates}, candidates

        op = node[1]; op_cp = ord(op)
        children = node[2]

        # 先处理子节点
        child_results = []
        for i, c in enumerate(children):
            res, _ = process_node(c, op, i)
            child_results.append(res)

        # 取子节点的默认变体(候选列表的第一个,地区优先)
        default_names = []
        for res in child_results:
            cands = res.get('candidates', [])
            name = None
            for c in cands:
                base_c = extract_base(c)
                suffix = c[len(base_c):] if base_c else c
                if suffix.startswith('-' + region) or suffix.startswith('-j') or not suffix:
                    name = c; break
            if not name and cands:
                name = cands[-1]  # 基础形 uXXXX
            default_names.append(name or '?')

        # 计算 bbox
        child_bboxes = [bbox_of(n, glyphs, bbox_cache) for n in default_names]

        # 分配 slot
        slots = allocate_slots(op_cp, child_bboxes, default_names, glyphs)

        # 对每个 slot 做: 位置过滤 → 形状匹配
        selections = []
        for i, (res, slot) in enumerate(zip(child_results, slots)):
            cands = res.get('candidates', [])
            # ---- 位置过滤 ----
            expected_suffix = position_suffix(i, op_cp)
            if op_cp in SURROUND_OP_CODES and i == 0:
                # 包围外框: 用多候选 bbox 评分, 不硬过滤
                pos_filtered = cands
            else:
                pos_filtered = []
                for c in cands:
                    base_c = extract_base(c)
                    sfx = c[len(base_c):] if base_c else c
                    pc = extract_position_code(sfx)
                    # 基础形(无后缀)总是允许; 位置码匹配的也允许
                    if pc == '' or pc == expected_suffix:
                        pos_filtered.append(c)
                    # 对于地区前缀 + 位置码的情况: -g04 的 pc='04', -g03 的 pc='03'
                    # extract_position_code 已经正确提取了

            if not pos_filtered:
                pos_filtered = cands  # 没有匹配的，fallback

            print(f"    DEBUG slot[{i}]: {res.get('char','?')} pos={i} "
                  f"exp_sfx={expected_suffix} cands#={len(cands)}→{len(pos_filtered)}")

            best_name = None; best_score = -1; best_reason = ''
            for c in pos_filtered:
                score, reason = shape_match_score(c, slot, glyphs, bbox_cache)
                if score > best_score:
                    best_score = score; best_name = c; best_reason = reason
            selections.append({
                'char': res.get('char', '?'),
                'default': default_names[i],
                'selected': best_name,
                'score': best_score,
                'reason': best_reason,
                'slot': slots[i],
                'slot_w': slots[i][2] - slots[i][0],
                'slot_h': slots[i][3] - slots[i][1],
                'all_scores': [(c, *shape_match_score(c, slot, glyphs, bbox_cache))
                               for c in cands[:8]]  # 只取前8个
            })

        result = {
            'op': op,
            'children': child_results,
            'selections': selections,
            'slots': slots,
        }
        return result, None

    result, _ = process_node(root)
    return result, None


# ============================================================
# 6. 主函数
# ============================================================

def main():
    glyphs = load_dump(DUMP_PATH)
    variant_idx = build_variant_index(glyphs)
    print(f"  变体索引: {len(variant_idx)} 个字符")

    tests = [
        "⿱𡗬禾",   # 秦
        "⿸麻鬼",   # 魔
        "⿱山鬼",   # 嵬
        "⿸麻木",   # 麿 (麻+吕)
        "⿸麻么",   # 麽
    ]

    for ids in tests:
        print(f"\n{'='*70}")
        print(f"  {ids}")
        print(f"{'='*70}")

        result, err = process_ids(ids, 'g', glyphs, variant_idx)
        if err:
            print(f"  错误: {err}")
            continue

        def print_selections(node, indent=0):
            pref = '  ' * indent
            if 'selections' in node:
                for sel in node['selections']:
                    ch = sel['char']
                    bb = bbox_of(sel['selected'], glyphs, {})
                    bb_str = f' bbox=({bb[0]},{bb[1]})-({bb[2]},{bb[3]})' if bb else ''
                    slot = sel['slot']
                    print(f"{pref}'{ch}' → {sel['selected']}")
                    print(f"{pref}  slot=({slot[0]},{slot[1]},{slot[2]},{slot[3]}) "
                          f"w={sel['slot_w']} h={sel['slot_h']}")
                    print(f"{pref}  score={sel['score']:.3f} {sel['reason']}")
                    if bb:
                        vw = bb[2]-bb[0]; vh = bb[3]-bb[1]
                        s_aspect = sel['slot_w']/max(sel['slot_h'],1)
                        v_aspect = vw/max(vh,1)
                        print(f"{pref}  variant: {vw}×{vh} (ar={v_aspect:.2f}) "
                              f"slot: {sel['slot_w']}×{sel['slot_h']} (ar={s_aspect:.2f})")
                    # 显示备选评分
                    top5 = sorted(sel['all_scores'], key=lambda x: -x[1])[:5]
                    print(f"{pref}  top5: " +
                          ', '.join(f"{n}={s:.2f}" for n, s, r in top5))

            if 'children' in node:
                for c in node['children']:
                    print_selections(c, indent + 1)

        print_selections(result)

    print(f"\n{'='*70}")
    print("完成!")


if __name__ == '__main__':
    main()
