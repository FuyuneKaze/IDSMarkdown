"""
精进版 ⿰/⿱ 部件比例分析 v3

改进:
1. 验证部件引用与IDS一致性 (支持多IDS变体择优)
2. 放宽部件解析 (1个type-99引用+笔画也提取)
3. 每行一字, 两部件数据:
   - type-99部件: 变体名 + 原bbox(200x200) + 伸缩后bbox + 笔画数
   - 笔画部件: 空变体名 + bbox(父坐标系) + 笔画数
"""

import sys, io, os, math, csv
from collections import defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from test_bbox_alloc import resolve_kage, BBox, CHAR_TO_KEYS

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"
IDS_FILE = "D:/2026harucpp/data/ids/ids_lv1.txt"
OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

STROKE_PAD = 4


# ============================================================
# CJK 过滤
# ============================================================
def _is_cjk(cp: int) -> bool:
    return (
        (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or
        (0x20000 <= cp <= 0x2A6DF) or (0x2A700 <= cp <= 0x2B73F) or
        (0x2B740 <= cp <= 0x2B81F) or (0x2B820 <= cp <= 0x2CEAF) or
        (0x2CEB0 <= cp <= 0x2EBEF) or (0x30000 <= cp <= 0x3134F) or
        (0x31350 <= cp <= 0x323AF) or (0xF900 <= cp <= 0xFAFF) or
        (0x2F800 <= cp <= 0x2FA1F)
    )


# ============================================================
# dump 索引 + BFS 加载
# ============================================================
def build_offset_index(dump_path):
    print("建立 dump 索引...", flush=True)
    index = {}
    with open(dump_path, 'rb') as f:
        f.readline(); f.readline()
        while True:
            offset = f.tell()
            line = f.readline()
            if not line: break
            if line[:2] != b' u': continue
            try: line_str = line.decode('utf-8')
            except UnicodeDecodeError: continue
            p = line_str.find(' | ')
            if p < 0: continue
            index[line_str[:p].strip()] = offset
    print(f"  索引: {len(index)} 条目", flush=True)
    return index


def read_entries(index, dump_path, names):
    result = {}
    with open(dump_path, 'rb') as f:
        for name in names:
            off = index.get(name)
            if off is None: continue
            f.seek(off)
            line = f.readline().decode('utf-8')
            cols = line.split(' | ')
            if len(cols) < 3: continue
            data = cols[2].strip()
            deps = []
            for seg in data.split('$'):
                seg = seg.strip()
                if seg.startswith('99:'):
                    p = seg.split(':')
                    if len(p) >= 8:
                        deps.append(p[7].split('@')[0])
            result[name] = (data, deps)
    return result


def load_transitive(index, dump_path, initial_names, verbose=True):
    all_data = {}
    pending = list(initial_names)
    seen = set()
    it = 0
    while pending:
        it += 1
        targets = [n for n in pending if n not in seen]
        if not targets: break
        for n in targets: seen.add(n)
        entries = read_entries(index, dump_path, targets)
        new_deps = []
        for name, (data, deps) in entries.items():
            all_data[name] = data
            for d in deps:
                if d not in seen: new_deps.append(d)
        if verbose:
            print(f"  pass {it}: {len(targets)}→{len(entries)}, +{len(new_deps)} deps", flush=True)
        pending = new_deps
    if verbose: print(f"  总计: {len(all_data)} 条目", flush=True)
    return all_data


# ============================================================
# 部件名工具
# ============================================================
def find_names_for_char(char):
    if len(char) != 1: return []
    cp = ord(char)
    if not _is_cjk(cp): return []
    names = []
    keys = CHAR_TO_KEYS.get(char, {})
    for k in ('base', 'pos0', 'pos1'):
        if k in keys: names.append(keys[k])
    hex_name = f"u{cp:x}"
    for suffix in ('', '-j', '-k', '-v'):
        n = hex_name + suffix
        if n not in names: names.append(n)
    return names


def variant_matches_char(variant_name, char):
    """检查变体名是否对应该字符"""
    candidates = find_names_for_char(char)
    if variant_name in candidates:
        return True
    base = variant_name
    for sep in ('-', '@'):
        idx = base.find(sep)
        if idx > 0:
            base = base[:idx]
            break
    for c in candidates:
        c_base = c
        for sep in ('-', '@'):
            idx = c_base.find(sep)
            if idx > 0:
                c_base = c_base[:idx]
                break
        if base == c_base:
            return True
    return False


# ============================================================
# IDS 解析 (保留所有变体)
# ============================================================
def parse_ids_all_variants(file_path):
    """提取所有 ⿰/⿱ 变体, 返回 {char: [(op, c1, c2), ...]}"""
    ops = {'⿰', '⿱'}
    result = defaultdict(list)

    def extract_two_comps(ids_str):
        rest = ids_str[1:]
        comps = []
        i = 0
        while i < len(rest) and len(comps) < 2:
            ch = rest[i]
            cp = ord(ch)
            if 0x2FF0 <= cp <= 0x2FFF:
                j = i + 1; pending = 2
                while j < len(rest) and pending > 0:
                    ocp = ord(rest[j])
                    if 0x2FF0 <= ocp <= 0x2FFF: pending += 2
                    else: pending -= 1
                    j += 1
                i = j
            else:
                comps.append(ch); i += 1
        return comps if len(comps) == 2 else None

    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('\t')
            if len(parts) < 2: continue
            char = parts[0]
            if not _is_cjk(ord(char)): continue

            for ids in parts[1:]:
                ids = ids.strip()
                if len(ids) < 3: continue
                op = ids[0]
                if op not in ops: continue
                comps = extract_two_comps(ids)
                if comps is None: continue
                c1, c2 = comps
                if not _is_cjk(ord(c1)) or not _is_cjk(ord(c2)): continue
                result[char].append((op, c1, c2))

    print(f"  IDS变体: {len(result)} 字符, {sum(len(v) for v in result.values())} 变体",
          flush=True)
    return dict(result)


# ============================================================
# 部件解析
# ============================================================
def resolve_components_flexible(data_str, glyph_db, depth=0, max_depth=10):
    """
    追踪 type-99 链。

    返回: {
        'children': [(x1,y1,x2,y2, variant_name, stretch), ...]
        'has_strokes': bool
        'parts_list': [seg_str, ...]  顶层所有 $ 分段
    }
    """
    if depth > max_depth:
        return {'children': [], 'has_strokes': False, 'parts_list': []}

    parts_list = [s.strip() for s in data_str.split('$') if s.strip()]
    children = []
    has_strokes = False

    for seg in parts_list:
        seg = seg.strip()
        if not seg: continue
        seg_parts = seg.split(':')
        try: kind = int(seg_parts[0])
        except ValueError: continue

        if kind == 99 and len(seg_parts) >= 8:
            x1, y1 = int(seg_parts[3]), int(seg_parts[4])
            x2, y2 = int(seg_parts[5]), int(seg_parts[6])
            ref_name = seg_parts[7].split('@')[0]
            stretch = []
            for i in range(8, min(len(seg_parts), 12)):
                try: stretch.append(int(seg_parts[i]))
                except ValueError: stretch.append(0)
            while len(stretch) < 4: stretch.append(0)
            children.append((x1, y1, x2, y2, ref_name, tuple(stretch)))
        elif kind in range(1, 9) or kind == 12:
            has_strokes = True

    # 单个 type-99 子部件, 尝试继续追踪
    if not has_strokes and len(children) == 1:
        child_name = children[0][4]
        child_data = glyph_db.get(child_name, '')
        if child_data:
            deeper = resolve_components_flexible(child_data, glyph_db, depth + 1, max_depth)
            if deeper['children']:
                return deeper
        return {'children': children, 'has_strokes': False, 'parts_list': parts_list}

    return {'children': children, 'has_strokes': has_strokes, 'parts_list': parts_list}


# ============================================================
# bbox 计算
# ============================================================
def compute_visual_bbox(data_str, glyph_db):
    """字形在 200x200 空间的视觉 bbox (含笔画粗细补偿)"""
    pts = resolve_kage(data_str, glyph_db, set())
    if not pts: return BBox()
    bb = BBox()
    for x, y in pts: bb.expand(int(x), int(y))
    if bb.valid():
        bb.x1 = max(0, bb.x1 - STROKE_PAD); bb.y1 = max(0, bb.y1 - STROKE_PAD)
        bb.x2 = min(200, bb.x2 + STROKE_PAD); bb.y2 = min(200, bb.y2 + STROKE_PAD)
    return bb


def compute_stretched_bbox(variant_data, glyph_db, rect, stretch):
    """
    位置变体经 stretch+placement 后在父坐标系中的实际视觉 bbox。

    返回: (x1, y1, x2, y2, w, h) 或 None
    """
    pts = resolve_kage(variant_data, glyph_db, set())
    if not pts: return None

    rx1, ry1, rx2, ry2 = rect
    rw, rh = rx2 - rx1, ry2 - ry1
    if rw <= 0 or rh <= 0: return None
    sx, sy, sx2, sy2 = stretch

    mapped = []
    # 与 kage-bundle.js 的 getEachStrokesOfBuhin 对齐:
    #   缝=(sx2,sy2)+100, 目标=(sx,sy)+100; sx>100 时 sx-=200, 否则缝归中心。
    #   是否拉伸只看调整后的 (sx,sy) —— sx=200,sy=0 会被折成 (0,0), KAGE 就不拉伸了。
    if sx != 0 or sy != 0:
        if sx > 100:
            sx -= 200
        else:
            sx2 = 0
            sy2 = 0
    has_stretch = (sx != 0 or sy != 0)

    if has_stretch:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        bx1, by1 = min(xs), min(ys); bx2, by2 = max(xs), max(ys)
        ax, ay = sx2 + 100, sy2 + 100
        dx, dy = sx + 100, sy + 100

        for x, y in pts:
            if x < ax:
                x0 = bx1 + (x - bx1) * (dx - bx1) / (ax - bx1) if ax != bx1 else dx
            elif x > ax:
                x0 = dx + (x - ax) * (bx2 - dx) / (bx2 - ax) if bx2 != ax else dx
            else:
                x0 = dx
            if y < ay:
                y0 = by1 + (y - by1) * (dy - by1) / (ay - by1) if ay != by1 else dy
            elif y > ay:
                y0 = dy + (y - ay) * (by2 - dy) / (by2 - ay) if by2 != ay else dy
            else:
                y0 = dy
            mx = rx1 + (x0 / 200.0) * rw
            my = ry1 + (y0 / 200.0) * rh
            mapped.append((mx, my))
    else:
        for x, y in pts:
            mx = rx1 + (x / 200.0) * rw
            my = ry1 + (y / 200.0) * rh
            mapped.append((mx, my))

    if not mapped: return None
    mx1 = min(p[0] for p in mapped); my1 = min(p[1] for p in mapped)
    mx2 = max(p[0] for p in mapped); my2 = max(p[1] for p in mapped)
    return (mx1, my1, mx2, my2, mx2 - mx1, my2 - my1)


def compute_strokes_bbox(stroke_parts):
    """
    从笔画 $ 分段列表计算 bbox (坐标已在父空间)。

    stroke_parts: ["1:2:0:75:50:155:50", "2:2:0:75:180:155:180", ...]
    返回: (x1, y1, x2, y2, w, h) 或 None
    """
    all_pts = []
    for seg in stroke_parts:
        seg = seg.strip()
        if not seg: continue
        seg_parts = seg.split(':')
        try: kind = int(seg_parts[0])
        except ValueError: continue
        if kind not in range(1, 9) and kind != 12: continue
        for i in range(3, len(seg_parts), 2):
            if i + 1 < len(seg_parts):
                try:
                    x = int(seg_parts[i]); y = int(seg_parts[i+1])
                    all_pts.append((x, y))
                except ValueError: pass
    if not all_pts: return None
    xs = [p[0] for p in all_pts]; ys = [p[1] for p in all_pts]
    x1, y1 = min(xs), min(ys)
    x2, y2 = max(xs), max(ys)
    return (x1, y1, x2, y2, x2 - x1, y2 - y1)


def count_strokes_recursive(data_str, glyph_db, visited=None):
    """递归统计叶子笔画数 (穿透 type-99 链), 与 resolve_kage 遍历方式一致"""
    if visited is None:
        visited = set()
    count = 0
    for seg in data_str.split('$'):
        seg = seg.strip()
        if not seg: continue
        parts = seg.split(':')
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
                count += count_strokes_recursive(glyph_db[base], glyph_db, visited)
        elif kind in range(1, 9) or kind == 12:
            count += 1
    return count


# ============================================================
# 输出部件数据到 row dict
# ============================================================
def dump_component_fields(row, prefix, variant, orig_bbox, str_bbox, strokes):
    """将部件数据填入 row dict, 带前缀 (c1_ 或 c2_)"""
    if orig_bbox:
        row[f'{prefix}_orig_x1'] = orig_bbox[0]
        row[f'{prefix}_orig_y1'] = orig_bbox[1]
        row[f'{prefix}_orig_x2'] = orig_bbox[2]
        row[f'{prefix}_orig_y2'] = orig_bbox[3]
        row[f'{prefix}_orig_w'] = orig_bbox[4]
        row[f'{prefix}_orig_h'] = orig_bbox[5]
    else:
        for f in ('x1','y1','x2','y2','w','h'):
            row[f'{prefix}_orig_{f}'] = ''

    if str_bbox:
        row[f'{prefix}_str_x1'] = round(str_bbox[0], 1)
        row[f'{prefix}_str_y1'] = round(str_bbox[1], 1)
        row[f'{prefix}_str_x2'] = round(str_bbox[2], 1)
        row[f'{prefix}_str_y2'] = round(str_bbox[3], 1)
        row[f'{prefix}_str_w'] = round(str_bbox[4], 1)
        row[f'{prefix}_str_h'] = round(str_bbox[5], 1)
    else:
        for f in ('x1','y1','x2','y2','w','h'):
            row[f'{prefix}_str_{f}'] = ''

    row[f'{prefix}_variant'] = variant or ''
    row[f'{prefix}_strokes'] = strokes if strokes >= 0 else ''


# ============================================================
# 主分析
# ============================================================
def main():
    # ---- 1. IDS ----
    print("\n=== 解析 IDS (所有变体) ===", flush=True)
    ids_variants = parse_ids_all_variants(IDS_FILE)

    # ---- 2. dump 索引 + BFS ----
    print("\n=== 建立索引 ===", flush=True)
    index = build_offset_index(DUMP)

    print("\n=== BFS 加载 ===", flush=True)
    initial_names = set()
    for char, variants in ids_variants.items():
        for n in find_names_for_char(char): initial_names.add(n)
        for op, c1, c2 in variants:
            for n in find_names_for_char(c1): initial_names.add(n)
            for n in find_names_for_char(c2): initial_names.add(n)

    initial_names = {n for n in initial_names if n in index}
    print(f"  初始 {len(initial_names)} 有效 key ({len(ids_variants)} 主字)", flush=True)
    glyph_db = load_transitive(index, DUMP, initial_names)

    # ---- 3. 逐字解析 ----
    print("\n=== 解析 + 验证部件引用 ===", flush=True)
    rows = []
    stats = {'ok_both':0, 'ok_one_ref':0, 'ok_all_strokes':0,
             'no_dump':0, 'no_match':0, 'skip':0}

    for char, variants in ids_variants.items():
        # 找 char 在 dump 里的数据
        char_names = find_names_for_char(char)
        char_data = None
        for cn in char_names:
            if cn in glyph_db:
                char_data = glyph_db[cn]
                break
        if char_data is None:
            stats['no_dump'] += 1; continue

        # 尝试每个 IDS 变体直到部件对得上
        best = None  # (case, children, parts_list, has_strokes, op, c1, c2)

        for op, c1, c2 in variants:
            res = resolve_components_flexible(char_data, glyph_db)
            children = res['children']
            has_strokes = res['has_strokes']
            parts_list = res['parts_list']

            if len(children) == 2:
                v0, v1 = children[0][4], children[1][4]
                if variant_matches_char(v0, c1) and variant_matches_char(v1, c2):
                    best = ('both', children, parts_list, has_strokes, op, c1, c2); break
                if variant_matches_char(v0, c2) and variant_matches_char(v1, c1):
                    c1, c2 = c2, c1  # swap
                    best = ('both', children, parts_list, has_strokes, op, c1, c2); break

            elif len(children) == 1 and has_strokes:
                vname = children[0][4]
                if variant_matches_char(vname, c1):
                    best = ('ref_is_c1', children, parts_list, has_strokes, op, c1, c2); break
                if variant_matches_char(vname, c2):
                    best = ('ref_is_c2', children, parts_list, has_strokes, op, c1, c2); break

            elif len(children) == 0 and has_strokes:
                # 全是笔画, 没有 type-99 引用 — 仍可提取两边的 bbox 和笔画数
                best = ('all_strokes', children, parts_list, has_strokes, op, c1, c2); break

        if best is None:
            stats['no_match'] += 1; continue

        case, children, parts_list, has_strokes, op, c1, c2 = best

        row = {
            'char': char, 'op': op, 'c1_char': c1, 'c2_char': c2,
            'pos1_label': '左' if op == '⿰' else '上',
            'pos2_label': '右' if op == '⿰' else '下',
        }

        # 分割 parts_list: type-99 段 vs 笔画段
        ref_parts = []   # [(seg_idx, child_tuple)]
        stroke_parts = []
        for si, seg in enumerate(parts_list):
            try: kind = int(seg.split(':')[0])
            except ValueError: continue
            if kind == 99:
                # 找到对应的 child
                for ch in children:
                    if len(seg.split(':')) >= 7:
                        ch_x1 = int(seg.split(':')[3])
                        if ch[0] == ch_x1:  # 用 x1 匹配
                            ref_parts.append((si, ch))
                            break
                else:
                    ref_parts.append((si, None))
            elif kind in range(1, 9) or kind == 12:
                stroke_parts.append(seg)

        if case == 'both':
            stats['ok_both'] += 1
            # c1 ← children[0], c2 ← children[1]
            for idx, comp_char in enumerate([c1, c2]):
                prefix = f'c{idx+1}'
                child = children[idx]
                x1, y1, x2, y2, vname, stretch = child

                if vname in glyph_db:
                    var_data = glyph_db[vname]
                    orig_bb = compute_visual_bbox(var_data, glyph_db)
                    if orig_bb.valid():
                        o = (orig_bb.x1, orig_bb.y1, orig_bb.x2, orig_bb.y2,
                             orig_bb.width(), orig_bb.height())
                    else:
                        o = None
                    s = compute_stretched_bbox(var_data, glyph_db, (x1,y1,x2,y2), stretch)
                    sc = count_strokes_recursive(var_data, glyph_db)
                else:
                    o = None; s = None; sc = -1

                dump_component_fields(row, prefix, vname, o, s, sc)

        elif case in ('ref_is_c1', 'ref_is_c2'):
            stats['ok_one_ref'] += 1
            ref_child = children[0]
            x1, y1, x2, y2, vname, stretch = ref_child

            # 确定哪个是 type-99, 哪个是笔画
            if case == 'ref_is_c1':
                ref_prefix, stroke_prefix = 'c1', 'c2'
                ref_comp, stroke_comp = c1, c2
            else:
                ref_prefix, stroke_prefix = 'c2', 'c1'
                ref_comp, stroke_comp = c2, c1

            # type-99 部件
            if vname in glyph_db:
                var_data = glyph_db[vname]
                orig_bb = compute_visual_bbox(var_data, glyph_db)
                if orig_bb.valid():
                    o = (orig_bb.x1, orig_bb.y1, orig_bb.x2, orig_bb.y2,
                         orig_bb.width(), orig_bb.height())
                else:
                    o = None
                s = compute_stretched_bbox(var_data, glyph_db, (x1,y1,x2,y2), stretch)
                sc = count_strokes_recursive(var_data, glyph_db)
            else:
                o = None; s = None; sc = -1
            dump_component_fields(row, ref_prefix, vname, o, s, sc)

            # 笔画部件
            if stroke_parts:
                sb = compute_strokes_bbox(stroke_parts)
                n_strokes = len(stroke_parts)
            else:
                sb = None; n_strokes = 0
            dump_component_fields(row, stroke_prefix, '', sb, sb, n_strokes)

        elif case == 'all_strokes':
            stats['ok_all_strokes'] += 1
            # 全是笔画 — 无法分离两个部件, 只输出整体
            # 这里尝试用笔画坐标范围粗略分左右/上下
            if not stroke_parts:
                stats['skip'] += 1; continue

            # 收集所有笔画坐标
            all_pts = []
            for seg in stroke_parts:
                sp = seg.split(':')
                try: kind = int(sp[0])
                except ValueError: continue
                if kind not in range(1, 9) and kind != 12: continue
                for i in range(3, len(sp), 2):
                    if i+1 < len(sp):
                        try: all_pts.append((int(sp[i]), int(sp[i+1])))
                        except ValueError: pass
            if not all_pts:
                stats['skip'] += 1; continue

            xs = [p[0] for p in all_pts]; ys = [p[1] for p in all_pts]
            mid_x = (min(xs) + max(xs)) / 2.0
            mid_y = (min(ys) + max(ys)) / 2.0

            if op == '⿰':
                # 按 x 坐标中点分左右
                c1_pts = [(x,y) for x,y in all_pts if x < mid_x]
                c2_pts = [(x,y) for x,y in all_pts if x >= mid_x]
                c1_stroke_parts = [seg for seg in stroke_parts
                                   if _seg_mid_x(seg) < mid_x]
                c2_stroke_parts = [seg for seg in stroke_parts
                                   if _seg_mid_x(seg) >= mid_x]
            else:
                # 按 y 坐标中点分上下
                c1_pts = [(x,y) for x,y in all_pts if y < mid_y]
                c2_pts = [(x,y) for x,y in all_pts if y >= mid_y]
                c1_stroke_parts = [seg for seg in stroke_parts
                                   if _seg_mid_y(seg) < mid_y]
                c2_stroke_parts = [seg for seg in stroke_parts
                                   if _seg_mid_y(seg) >= mid_y]

            for idx, (pt_list, sp_list) in enumerate(
                [(c1_pts, c1_stroke_parts), (c2_pts, c2_stroke_parts)]):
                prefix = f'c{idx+1}'
                if pt_list:
                    x1 = min(p[0] for p in pt_list); y1 = min(p[1] for p in pt_list)
                    x2 = max(p[0] for p in pt_list); y2 = max(p[1] for p in pt_list)
                    bb = (x1, y1, x2, y2, x2-x1, y2-y1)
                    sc = len(sp_list)
                else:
                    bb = None; sc = 0
                dump_component_fields(row, prefix, '', bb, bb, sc)
        else:
            stats['skip'] += 1; continue

        rows.append(row)

    print(f"\n  匹配: 两type-99={stats['ok_both']}, 单ref+笔画={stats['ok_one_ref']}, "
          f"全笔画={stats['ok_all_strokes']}")
    print(f"  跳过: 无dump={stats['no_dump']}, 无匹配={stats['no_match']}, "
          f"其他={stats['skip']}", flush=True)

    # ---- 4. 输出 ----
    csv_path = os.path.join(OUT_DIR, "composition_v3.csv")
    if rows:
        fieldnames = list(rows[0].keys())
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"\n输出: {csv_path} ({len(rows)} 行)", flush=True)

    # 按操作符统计
    by_op = defaultdict(int)
    for r in rows: by_op[r['op']] += 1
    for k, v in sorted(by_op.items()):
        print(f"  {k}: {v}")


def _seg_mid_x(seg):
    """笔画段的 x 中点"""
    sp = seg.split(':')
    xs = []
    for i in range(3, len(sp), 2):
        if i+1 < len(sp):
            try: xs.append(int(sp[i]))
            except ValueError: pass
    return sum(xs)/len(xs) if xs else 100


def _seg_mid_y(seg):
    """笔画段的 y 中点"""
    sp = seg.split(':')
    ys = []
    for i in range(4, len(sp), 2):
        if i+1 < len(sp):
            try: ys.append(int(sp[i]))
            except ValueError: pass
    return sum(ys)/len(ys) if ys else 100


if __name__ == "__main__":
    main()
