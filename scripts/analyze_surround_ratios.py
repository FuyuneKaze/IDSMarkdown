"""
分析包围二部件 (⿸⿺⿹⿽⿵⿷⿶⿼⿴) 的伸缩比例

收集:
  外围部件: 变体名 / stretch锚点(sx,sy,sx2,sy2) / bbox中心点
  内围部件: 变体名 / rect→坐标系伸缩比 / bbox中心点
  附带: D:X1:Y1:X2:Y2:S 紧凑记录
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

# 包围 IDS 操作符
SURROUND_OPS = {'⿸', '⿺', '⿹', '⿽', '⿵', '⿷', '⿶', '⿼', '⿴'}
# ⿸=左上包围 ⿺=左下包围 ⿹=右上包围 ⿽=右下包围
# ⿵=上包围 ⿷=左包围 ⿶=下包围 ⿼=右包围 ⿴=全包围


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
# type-99 链追踪
# ============================================================
def resolve_to_leaf_components(glyph_name, glyph_db, depth=0, max_depth=10):
    if depth > max_depth: return []
    data = glyph_db.get(glyph_name, '')
    if not data: return []
    children = []
    has_leaf = False
    for seg in data.split('$'):
        seg = seg.strip()
        if not seg: continue
        parts = seg.split(':')
        try: kind = int(parts[0])
        except ValueError: continue
        if kind == 99 and len(parts) >= 8:
            x1, y1 = int(parts[3]), int(parts[4])
            x2, y2 = int(parts[5]), int(parts[6])
            ref_name = parts[7].split('@')[0]
            stretch = []
            for i in range(8, min(len(parts), 12)):
                try: stretch.append(int(parts[i]))
                except ValueError: stretch.append(0)
            while len(stretch) < 4: stretch.append(0)
            children.append((x1, y1, x2, y2, ref_name, tuple(stretch)))
        elif kind in range(1, 9) or kind == 12:
            has_leaf = True
    if not has_leaf and len(children) == 1:
        return resolve_to_leaf_components(children[0][4], glyph_db, depth+1, max_depth)
    if not has_leaf and len(children) == 2:
        return children
    return []


def compute_visual_bbox(data_str, glyph_db):
    pts = resolve_kage(data_str, glyph_db, set())
    if not pts: return BBox()
    bb = BBox()
    for x, y in pts: bb.expand(int(x), int(y))
    if bb.valid():
        bb.x1 = max(0, bb.x1-STROKE_PAD); bb.y1 = max(0, bb.y1-STROKE_PAD)
        bb.x2 = min(200, bb.x2+STROKE_PAD); bb.y2 = min(200, bb.y2+STROKE_PAD)
    return bb


# ============================================================
# IDS 解析
# ============================================================
def parse_surround_ids(file_path):
    """提取包围二部件组合"""
    results = []
    skipped_non_cjk = 0; skipped_multi = 0
    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('\t')
            if len(parts) < 2: continue
            char, ids = parts[0], parts[1]
            if len(ids) < 3: continue
            op = ids[0]
            if op not in SURROUND_OPS: continue
            if not _is_cjk(ord(char)):
                skipped_non_cjk += 1; continue

            rest = ids[1:]
            comps = []
            i = 0
            while i < len(rest) and len(comps) < 2:
                ch = rest[i]
                cp = ord(ch)
                if 0x2FF0 <= cp <= 0x2FFF:
                    j = i + 1
                    pending = 2
                    while j < len(rest) and pending > 0:
                        ocp = ord(rest[j])
                        if 0x2FF0 <= ocp <= 0x2FFF: pending += 2
                        else: pending -= 1
                        j += 1
                    i = j
                else:
                    comps.append(ch); i += 1

            if len(comps) != 2: skipped_multi += 1; continue
            c1, c2 = comps[0], comps[1]
            if len(c1) != 1 or len(c2) != 1: skipped_multi += 1; continue
            if not _is_cjk(ord(c1)) or not _is_cjk(ord(c2)):
                skipped_non_cjk += 1; continue

            results.append((char, op, c1, c2))

    print(f"  解析: {len(results)} 包围组合, "
          f"跳过 {skipped_non_cjk} 非CJK, {skipped_multi} 多组件", flush=True)
    return results


# ============================================================
# 字符 → dump 候选名
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


# ============================================================
# 主分析
# ============================================================
def main():
    print("\n=== 解析 IDS (包围) ===", flush=True)
    ids_pairs = parse_surround_ids(IDS_FILE)

    print("\n=== 建立索引 ===", flush=True)
    index = build_offset_index(DUMP)

    print("\n=== BFS 加载 ===", flush=True)
    initial_names = set()
    char_candidates = {}
    for char, op, c1, c2 in ids_pairs:
        names = find_names_for_char(char)
        if names:
            char_candidates[char] = names
            for n in names: initial_names.add(n)
        for comp in (c1, c2):
            for n in find_names_for_char(comp): initial_names.add(n)

    initial_names = {n for n in initial_names if n in index}
    print(f"  初始 {len(initial_names)} 有效 key ({len(char_candidates)} 主字)", flush=True)
    glyph_db = load_transitive(index, DUMP, initial_names)

    print("\n=== 分析包围比例 ===", flush=True)
    rows = []
    no_comp = 0; no_bbox = 0

    for char, op, c1, c2 in ids_pairs:
        candidates = char_candidates.get(char, [])
        comps = []
        for name in candidates:
            if name not in glyph_db: continue
            comps = resolve_to_leaf_components(name, glyph_db)
            if len(comps) == 2: break
        if len(comps) != 2: no_comp += 1; continue

        r_outer, r_inner = comps[0], comps[1]  # (x1,y1,x2,y2,vname,stretch)
        vname_o, vname_i = r_outer[4], r_inner[4]
        if vname_o not in glyph_db or vname_i not in glyph_db:
            no_comp += 1; continue

        bb_o = compute_visual_bbox(glyph_db[vname_o], glyph_db)
        bb_i = compute_visual_bbox(glyph_db[vname_i], glyph_db)
        if not bb_o.valid() or not bb_i.valid():
            no_bbox += 1; continue

        # 外围
        rwo = r_outer[2] - r_outer[0]; rho = r_outer[3] - r_outer[1]
        bwo = bb_o.width(); bho = bb_o.height()
        # 内围
        rwi = r_inner[2] - r_inner[0]; rhi = r_inner[3] - r_inner[1]
        bwi = bb_i.width(); bhi = bb_i.height()
        if bwo<=0 or bho<=0 or bwi<=0 or bhi<=0: no_bbox += 1; continue

        # 伸缩比 (坐标系缩放)
        str_o_x = round(rwo/200.0, 4); str_o_y = round(rho/200.0, 4)
        str_i_x = round(rwi/200.0, 4); str_i_y = round(rhi/200.0, 4)

        # bbox 中心点
        ctr_o_x = round((bb_o.x1 + bb_o.x2) / 2.0, 1)
        ctr_o_y = round((bb_o.y1 + bb_o.y2) / 2.0, 1)
        ctr_i_x = round((bb_i.x1 + bb_i.x2) / 2.0, 1)
        ctr_i_y = round((bb_i.y1 + bb_i.y2) / 2.0, 1)

        # stretch 锚点
        sx_o, sy_o, sx2_o, sy2_o = r_outer[5]
        sx_i, sy_i, sx2_i, sy2_i = r_inner[5]

        # D:X1:Y1:X2:Y2:S 紧凑格式
        def d_format(vname, rect, stretch):
            return f"{vname}:{rect[0]}:{rect[1]}:{rect[2]}:{rect[3]}:" \
                   f"{stretch[0]}:{stretch[1]}:{stretch[2]}:{stretch[3]}"

        rows.append({
            'char': char, 'op': op,
            'outer_char': c1, 'inner_char': c2,
            'outer_variant': vname_o,
            'inner_variant': vname_i,
            # 外围 rect
            'outer_rect_x1': r_outer[0], 'outer_rect_y1': r_outer[1],
            'outer_rect_x2': r_outer[2], 'outer_rect_y2': r_outer[3],
            'outer_rect_w': rwo, 'outer_rect_h': rho,
            # 外围 bbox
            'outer_bbox_w': bwo, 'outer_bbox_h': bho,
            'outer_center_x': ctr_o_x, 'outer_center_y': ctr_o_y,
            # 外围 stretch 锚点
            'outer_sx': sx_o, 'outer_sy': sy_o,
            'outer_sx2': sx2_o, 'outer_sy2': sy2_o,
            # 外围伸缩
            'outer_stretch_x': str_o_x, 'outer_stretch_y': str_o_y,
            # 内围 rect
            'inner_rect_x1': r_inner[0], 'inner_rect_y1': r_inner[1],
            'inner_rect_x2': r_inner[2], 'inner_rect_y2': r_inner[3],
            'inner_rect_w': rwi, 'inner_rect_h': rhi,
            # 内围 bbox
            'inner_bbox_w': bwi, 'inner_bbox_h': bhi,
            'inner_center_x': ctr_i_x, 'inner_center_y': ctr_i_y,
            # 内围 stretch 锚点
            'inner_sx': sx_i, 'inner_sy': sy_i,
            'inner_sx2': sx2_i, 'inner_sy2': sy2_i,
            # 内围伸缩
            'inner_stretch_x': str_i_x, 'inner_stretch_y': str_i_y,
            # 紧凑格式
            'outer_d_fmt': d_format(vname_o, (r_outer[0],r_outer[1],r_outer[2],r_outer[3]),
                                   r_outer[5]),
            'inner_d_fmt': d_format(vname_i, (r_inner[0],r_inner[1],r_inner[2],r_inner[3]),
                                   r_inner[5]),
        })

    print(f"  成功: {len(rows)} 字, "
          f"跳过 {no_comp} 非二部件, {no_bbox} 无bbox", flush=True)

    # ---- 输出 ----
    csv_path = os.path.join(OUT_DIR, "surround_ratios.csv")
    if rows:
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"\n明细: {csv_path} ({len(rows)} 行)", flush=True)

    # ---- 统计: 按 (部件, 包围类型) 分组 ----
    stat_outer = defaultdict(list)
    stat_inner = defaultdict(list)
    for r in rows:
        # 外围: stretch_x 分布
        stat_outer[(r['outer_char'], r['op'])].append(r['outer_stretch_x'])
        # 内围: stretch_x 分布
        stat_inner[(r['inner_char'], r['op'])].append(r['inner_stretch_x'])

    def build_stats(stats_dict, label):
        stat_rows = []
        for (comp, op), vals in sorted(stats_dict.items(), key=lambda x: -len(x[1])):
            n = len(vals)
            if n < 2: continue  # 至少2个样本
            a = sorted(vals)
            m = sum(a)/n
            v = sum((x-m)**2 for x in a)/n
            cv = math.sqrt(v)/m if m>0 else 0
            stat_rows.append({
                'comp': comp, 'op': op, 'n': n,
                'mean': round(m,4), 'std': round(math.sqrt(v),4),
                'cv': round(cv,4),
                'min': round(a[0],4), 'max': round(a[-1],4),
                'p50': round(a[n//2],4),
            })
        return sorted(stat_rows, key=lambda r: -r['cv'])

    outer_stats = build_stats(stat_outer, 'outer')
    inner_stats = build_stats(stat_inner, 'inner')

    stat_path = os.path.join(OUT_DIR, "surround_stats.csv")

    # 外围统计
    print(f"\n=== 外围部件 stretch_x CV 排行 (top 30) ===")
    print(f"{'部件':<6} {'包围':<6} {'N':>5} {'mean':>8} {'std':>7} {'CV':>7}")
    print("-" * 50)
    for r in outer_stats[:30]:
        print(f"{r['comp']:<6} {r['op']:<6} {r['n']:>5} "
              f"{r['mean']:>8.3f} {r['std']:>7.3f} {r['cv']:>7.3f}")

    print(f"\n=== 内围部件 stretch_x CV 排行 (top 30) ===")
    print(f"{'部件':<6} {'包围':<6} {'N':>5} {'mean':>8} {'std':>7} {'CV':>7}")
    print("-" * 50)
    for r in inner_stats[:30]:
        print(f"{r['comp']:<6} {r['op']:<6} {r['n']:>5} "
              f"{r['mean']:>8.3f} {r['std']:>7.3f} {r['cv']:>7.3f}")

    # 保存
    all_stats = []
    for r in outer_stats: r['role'] = 'outer'; all_stats.append(r)
    for r in inner_stats: r['role'] = 'inner'; all_stats.append(r)
    all_stats.sort(key=lambda r: -r['cv'])

    if all_stats:
        with open(stat_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=all_stats[0].keys())
            w.writeheader()
            w.writerows(all_stats)
        print(f"\n统计: {stat_path} ({len(all_stats)} 组)", flush=True)


if __name__ == "__main__":
    main()
