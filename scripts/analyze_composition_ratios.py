"""
分析 ⿰/⿱ 部件组合的比例分布

从 IDS 数据提取二部件组合字, 在 KAGE dump 中追踪 type-99 链,
计算每个部件在其分配矩形中的 visual scale 和扭曲率。

高性能版: 先建 name→文件偏移 索引, 再按需 seek 读取。
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
# 0. CJK 范围判断
# ============================================================

def _is_cjk(cp: int) -> bool:
    return (
        (0x4E00 <= cp <= 0x9FFF) or
        (0x3400 <= cp <= 0x4DBF) or
        (0x20000 <= cp <= 0x2A6DF) or
        (0x2A700 <= cp <= 0x2B73F) or
        (0x2B740 <= cp <= 0x2B81F) or
        (0x2B820 <= cp <= 0x2CEAF) or
        (0x2CEB0 <= cp <= 0x2EBEF) or
        (0x30000 <= cp <= 0x3134F) or
        (0x31350 <= cp <= 0x323AF) or
        (0xF900 <= cp <= 0xFAFF) or
        (0x2F800 <= cp <= 0x2FA1F)
    )


# ============================================================
# 1. 建立 name → 文件偏移 索引 (一次扫描)
# ============================================================

def build_offset_index(dump_path):
    """扫描 dump, 建立 {name: file_offset} 索引"""
    print("建立 dump 索引 (name → offset)...", flush=True)
    index = {}
    with open(dump_path, 'rb') as f:
        f.readline(); f.readline()  # skip headers
        while True:
            offset = f.tell()
            line = f.readline()
            if not line:
                break
            if line[:2] != b' u':  # 只索引以 " u" 开头的行
                continue
            try:
                line_str = line.decode('utf-8')
            except UnicodeDecodeError:
                continue
            # 提取 name (第一个 | 之前)
            pipe1 = line_str.find(' | ')
            if pipe1 < 0:
                continue
            name = line_str[:pipe1].strip()
            index[name] = offset
    print(f"  索引完成: {len(index)} 个条目", flush=True)
    return index


def read_entries(index, dump_path, names):
    """按名 seek 读取条目, 返回 {name: (data, deps)}"""
    result = {}
    with open(dump_path, 'rb') as f:
        for name in names:
            offset = index.get(name)
            if offset is None:
                continue
            f.seek(offset)
            line = f.readline().decode('utf-8')
            cols = line.split(' | ')
            if len(cols) < 3:
                continue
            data = cols[2].strip()
            # 收集 type-99 依赖
            deps = []
            for seg in data.split('$'):
                seg = seg.strip()
                if seg.startswith('99:'):
                    p = seg.split(':')
                    if len(p) >= 8:
                        deps.append(p[7].split('@')[0])
            result[name] = (data, deps)
    return result


# ============================================================
# 2. BFS 传递闭包加载
# ============================================================

def load_transitive(index, dump_path, initial_names, verbose=True):
    """BFS 迭代加载, 直到所有 type-99 依赖都加载完毕"""
    all_data = {}
    pending = list(initial_names)
    seen = set()
    iteration = 0

    while pending:
        iteration += 1
        targets = [n for n in pending if n not in seen]
        if not targets:
            break
        for n in targets:
            seen.add(n)

        entries = read_entries(index, dump_path, targets)
        new_deps = []
        for name, (data, deps) in entries.items():
            all_data[name] = data
            for d in deps:
                if d not in seen:
                    new_deps.append(d)

        if verbose:
            print(f"  pass {iteration}: 请求 {len(targets)} → 命中 {len(entries)}, "
                  f"新依赖 {len(new_deps)}", flush=True)
        pending = new_deps

    if verbose:
        print(f"  总计: {len(all_data)} 个条目 ({iteration} 轮)", flush=True)
    return all_data


# ============================================================
# 3. type-99 链追踪 + bbox 计算
# ============================================================

def resolve_to_leaf_components(glyph_name, glyph_db, depth=0, max_depth=10):
    """
    追踪 type-99 链, 返回最底层二部件的列表。
    只处理纯 type-99 节点 (无其他笔画类型)。
    返回: [(x1,y1,x2,y2, variant_name, stretch_tuple), ...]
    """
    if depth > max_depth:
        return []
    data = glyph_db.get(glyph_name, '')
    if not data:
        return []

    children = []
    has_leaf_strokes = False

    for seg in data.split('$'):
        seg = seg.strip()
        if not seg: continue
        parts = seg.split(':')
        try:
            kind = int(parts[0])
        except ValueError:
            continue

        if kind == 99 and len(parts) >= 8:
            x1, y1 = int(parts[3]), int(parts[4])
            x2, y2 = int(parts[5]), int(parts[6])
            ref_name = parts[7].split('@')[0]
            stretch = []
            for i in range(8, min(len(parts), 12)):
                try:
                    stretch.append(int(parts[i]))
                except ValueError:
                    stretch.append(0)
            while len(stretch) < 4:
                stretch.append(0)
            children.append((x1, y1, x2, y2, ref_name, tuple(stretch)))
        elif kind in range(1, 9) or kind == 12:
            has_leaf_strokes = True

    if not has_leaf_strokes and len(children) == 1:
        return resolve_to_leaf_components(children[0][4], glyph_db, depth + 1, max_depth)
    if not has_leaf_strokes and len(children) == 2:
        return children
    return []


def compute_visual_bbox(data_str, glyph_db):
    pts = resolve_kage(data_str, glyph_db, set())
    if not pts:
        return BBox()
    bb = BBox()
    for x, y in pts:
        bb.expand(int(x), int(y))
    if bb.valid():
        bb.x1 = max(0, bb.x1 - STROKE_PAD)
        bb.y1 = max(0, bb.y1 - STROKE_PAD)
        bb.x2 = min(200, bb.x2 + STROKE_PAD)
        bb.y2 = min(200, bb.y2 + STROKE_PAD)
    return bb


# ============================================================
# 4. IDS 解析
# ============================================================

def parse_ids_file(file_path):
    """提取 CJK ⿰/⿱ 二部件组合"""
    results = []
    skipped_non_cjk = 0
    skipped_multi = 0
    ops = {'⿰', '⿱'}

    with open(file_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            parts = line.split('\t')
            if len(parts) < 2: continue
            char, ids = parts[0], parts[1]
            if len(ids) < 3: continue
            op = ids[0]
            if op not in ops: continue

            if not _is_cjk(ord(char)):
                skipped_non_cjk += 1
                continue

            rest = ids[1:]
            comps = []
            i = 0
            while i < len(rest) and len(comps) < 2:
                ch = rest[i]
                cp = ord(ch)
                if 0x2FF0 <= cp <= 0x2FFF:
                    # 嵌套 IDS: 跳过整个子表达式
                    j = i + 1  # 跳过操作符, 进入子表达式
                    # 对于二操作数: 消耗 2 个顶层元素
                    # 简化处理: 每遇到非操作符就 count--, 每遇到操作符 count+=arity
                    pending = 2  # ⿰/⿱ 都是二操作数
                    while j < len(rest) and pending > 0:
                        ocp = ord(rest[j])
                        if 0x2FF0 <= ocp <= 0x2FFF:
                            pending += 2  # 嵌套操作符引入2个新操作数
                        else:
                            pending -= 1
                        j += 1
                    i = j  # 跳过整个嵌套子表达式
                else:
                    comps.append(ch)
                    i += 1

            if len(comps) != 2:
                skipped_multi += 1
                continue
            c1, c2 = comps[0], comps[1]
            if len(c1) != 1 or len(c2) != 1:
                skipped_multi += 1
                continue
            if not _is_cjk(ord(c1)) or not _is_cjk(ord(c2)):
                skipped_non_cjk += 1
                continue

            results.append((char, op, c1, c2))

    print(f"  解析: {len(results)} CJK ⿰/⿱, "
          f"跳过 {skipped_non_cjk} 非CJK, {skipped_multi} 多组件", flush=True)
    return results


# ============================================================
# 5. 字符 → dump 候选名
# ============================================================

def find_names_for_char(char):
    if len(char) != 1:
        return []
    cp = ord(char)
    if not _is_cjk(cp):
        return []

    names = []
    keys = CHAR_TO_KEYS.get(char, {})
    for k in ('base', 'pos0', 'pos1'):
        if k in keys:
            names.append(keys[k])

    hex_name = f"u{cp:x}"
    for suffix in ('', '-j', '-k', '-v'):
        n = hex_name + suffix
        if n not in names:
            names.append(n)
    return names


def find_neutral_name(char):
    """返回字符的中立变体名 (非位置特化的标准形)"""
    if len(char) != 1:
        return None
    # CHAR_TO_KEYS 的 'base' 键就是中立形
    keys = CHAR_TO_KEYS.get(char, {})
    if 'base' in keys:
        return keys['base']
    # 否则用 uXXXX-j 或 uXXXX
    cp = ord(char)
    return f"u{cp:x}-j"


# ============================================================
# 6. 主分析
# ============================================================

def main():
    # ---- 6a. IDS 解析 ----
    print("\n=== 解析 IDS ===", flush=True)
    ids_pairs = parse_ids_file(IDS_FILE)

    # ---- 6b. 建立 dump 偏移索引 ----
    print("\n=== 建立索引 ===", flush=True)
    index = build_offset_index(DUMP)

    # ---- 6c. 收集初始 names + 预加载 ----
    print("\n=== BFS 加载 ===", flush=True)
    initial_names = set()
    char_candidates = {}

    for char, op, c1, c2 in ids_pairs:
        names = find_names_for_char(char)
        if names:
            char_candidates[char] = names
            for n in names:
                initial_names.add(n)
        for comp in (c1, c2):
            for n in find_names_for_char(comp):
                initial_names.add(n)
            # 也加载中立变体 (用于三层对比)
            neu = find_neutral_name(comp)
            if neu:
                initial_names.add(neu)

    initial_names = {n for n in initial_names if n in index}  # 只保留索引中存在的
    print(f"  初始 {len(initial_names)} 个有效 key ({len(char_candidates)} 主字)", flush=True)
    glyph_db = load_transitive(index, DUMP, initial_names)

    # ---- 6d. 遍历分析 ----
    print("\n=== 分析比例 ===", flush=True)
    rows = []
    no_dump = 0; no_comp = 0; no_bbox = 0

    for char, op, c1, c2 in ids_pairs:
        candidates = char_candidates.get(char, [])
        comps = []
        for name in candidates:
            if name not in glyph_db:
                continue
            comps = resolve_to_leaf_components(name, glyph_db)
            if len(comps) == 2:
                break
        if len(comps) != 2:
            no_comp += 1
            continue

        r1, r2 = comps[0], comps[1]
        vname1, vname2 = r1[4], r2[4]

        if vname1 not in glyph_db or vname2 not in glyph_db:
            no_comp += 1
            continue

        bb1 = compute_visual_bbox(glyph_db[vname1], glyph_db)
        bb2 = compute_visual_bbox(glyph_db[vname2], glyph_db)
        if not bb1.valid() or not bb2.valid():
            no_bbox += 1
            continue

        # 中立变体 bbox (三层对比用)
        neu_name1 = find_neutral_name(c1)
        neu_name2 = find_neutral_name(c2)
        nbb1 = compute_visual_bbox(glyph_db.get(neu_name1 or '', ''), glyph_db) if neu_name1 else BBox()
        nbb2 = compute_visual_bbox(glyph_db.get(neu_name2 or '', ''), glyph_db) if neu_name2 else BBox()

        rw1, rh1 = r1[2] - r1[0], r1[3] - r1[1]
        rw2, rh2 = r2[2] - r2[0], r2[3] - r2[1]
        bw1, bh1 = bb1.width(), bb1.height()
        bw2, bh2 = bb2.width(), bb2.height()
        nw1 = nbb1.width() if nbb1.valid() and nbb1.width() > 0 else 0
        nh1 = nbb1.height() if nbb1.valid() and nbb1.height() > 0 else 0
        nw2 = nbb2.width() if nbb2.valid() and nbb2.width() > 0 else 0
        nh2 = nbb2.height() if nbb2.valid() and nbb2.height() > 0 else 0
        if bw1 <= 0 or bh1 <= 0 or bw2 <= 0 or bh2 <= 0:
            no_bbox += 1
            continue

        # 位置变体 vs 分配矩形
        # 真正的伸缩: type-99 将 (0,200) 坐标系映射到目标矩形
        # stretch = rect_size / 200, 对变体内所有点一视同仁
        vsx1, vsy1 = round(rw1 / 200.0, 4), round(rh1 / 200.0, 4)
        vsx2, vsy2 = round(rw2 / 200.0, 4), round(rh2 / 200.0, 4)
        dist1 = round(vsx1 / vsy1, 4) if vsy1 > 0 else 0
        dist2 = round(vsx2 / vsy2, 4) if vsy2 > 0 else 0

        # 三层对比: 中立变体bbox → 位置变体bbox → 伸缩后视觉尺寸
        def three_layer(nw, bw, rw, nh, bh, rh, sx, sy):
            # 位置变体的视觉大小占中立变体的比例
            compress_x = round(bw / nw, 4) if nw > 0 else 0
            compress_y = round(bh / nh, 4) if nh > 0 else 0
            # 伸缩后: 变体bbox × 坐标系缩放
            stretched_w = bw * sx  # 伸缩后的视觉宽
            stretched_h = bh * sy  # 伸缩后的视觉高
            # 伸缩比 (=坐标系缩放, 这是真正关心的指标)
            stretch_x = sx
            stretch_y = sy
            # 净效果: 伸缩后视觉尺寸 vs 中立变体
            net_x = round(stretched_w / nw, 4) if nw > 0 else 0
            net_y = round(stretched_h / nh, 4) if nh > 0 else 0
            return compress_x, compress_y, stretch_x, stretch_y, net_x, net_y, stretched_w, stretched_h

        t1 = three_layer(nw1, bw1, rw1, nh1, bh1, rh1, vsx1, vsy1)
        t2 = three_layer(nw2, bw2, rw2, nh2, bh2, rh2, vsx2, vsy2)

        if op == '⿰':
            pos1, pos2 = 'left', 'right'
        else:
            pos1, pos2 = 'top', 'bottom'

        def make_row(char, op, comp, pos, vname, rw, rh, bw, bh, nw, nh, tup, stretch):
            return {
                'char': char, 'op': op, 'comp': comp, 'pos': pos,
                'variant': vname,
                'rect_w': rw, 'rect_h': rh,
                'bbox_w': bw, 'bbox_h': bh,
                'neutral_w': nw, 'neutral_h': nh,
                'compress_x': tup[0], 'compress_y': tup[1],
                'stretch_x': tup[2], 'stretch_y': tup[3],
                'net_x': tup[4], 'net_y': tup[5],
                'stretched_w': round(tup[6], 1), 'stretched_h': round(tup[7], 1),
                'distortion': round(tup[2] / tup[3], 4) if tup[3] > 0 else 0,
                'stretch_params': ','.join(str(s) for s in stretch),
            }

        rows.append(make_row(char, op, c1, pos1, vname1,
                             rw1, rh1, bw1, bh1, nw1, nh1, t1, r1[5]))
        rows.append(make_row(char, op, c2, pos2, vname2,
                             rw2, rh2, bw2, bh2, nw2, nh2, t2, r2[5]))

    print(f"  成功: {len(rows)//2} 字, {len(rows)} 条记录", flush=True)
    print(f"  跳过: {no_comp} 非二部件, {no_bbox} 无bbox", flush=True)

    # ---- 6e. 汇总统计 ----
    print("\n=== 汇总统计 ===", flush=True)
    # 按 (部件, 位置) 分组, 收集 stretch_x (=分配拉伸比)
    # 用户关心: stretch_x 的方差 → 大的 = 弱势部件 (分配不稳定)
    stats = defaultdict(list)
    stats_detail = defaultdict(list)  # 完整记录用于详细分析
    for r in rows:
        key = (r['comp'], r['pos'])
        stats[key].append(r['stretch_x'])
        stats_detail[key].append(r)

    stat_rows = []
    for (comp, pos), sx_vals in sorted(stats.items(), key=lambda x: -len(x[1])):
        n = len(sx_vals)
        sx_sorted = sorted(sx_vals)

        mean = sum(sx_sorted) / n
        var = sum((x - mean)**2 for x in sx_sorted) / n
        std = math.sqrt(var)
        cv = std / mean if mean > 0 else 0  # 变异系数

        # 也统计 compress_x 和 net_x
        cx_vals = sorted([r['compress_x'] for r in stats_detail[(comp, pos)] if r['compress_x'] > 0])
        nx_vals = sorted([r['net_x'] for r in stats_detail[(comp, pos)] if r['net_x'] > 0])

        def st(arr):
            if not arr: return {'mean': 0, 'std': 0}
            m = sum(arr) / len(arr)
            v = sum((x - m)**2 for x in arr) / len(arr)
            return {'mean': round(m, 4), 'std': round(math.sqrt(v), 4)}

        cx_st = st(cx_vals); nx_st = st(nx_vals)

        stat_rows.append({
            'comp': comp, 'pos': pos, 'n': n,
            'stretch_x_mean': round(mean, 4),
            'stretch_x_std': round(std, 4),
            'stretch_x_cv': round(cv, 4),  # 变异系数: std/mean, 越大越不稳定
            'stretch_x_min': round(sx_sorted[0], 4),
            'stretch_x_max': round(sx_sorted[-1], 4),
            'stretch_x_p25': round(sx_sorted[n//4], 4),
            'stretch_x_p50': round(sx_sorted[n//2], 4),
            'stretch_x_p75': round(sx_sorted[3*n//4], 4),
            'compress_x_mean': cx_st['mean'],
            'compress_x_std': cx_st['std'],
            'net_x_mean': nx_st['mean'],
            'net_x_std': nx_st['std'],
        })

    # ---- 6f. 输出 ----
    csv_path = os.path.join(OUT_DIR, "composition_ratios_v2.csv")
    if rows:
        with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"\n逐字明细: {csv_path} ({len(rows)} 行)", flush=True)

    stat_path = os.path.join(OUT_DIR, "composition_ratios_stats_v2.csv")
    if stat_rows:
        with open(stat_path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=stat_rows[0].keys())
            w.writeheader()
            w.writerows(stat_rows)
        print(f"汇总统计: {stat_path} ({len(stat_rows)} 组)", flush=True)

    # 控制台: 按 stretch_x_cv 降序 (弱势部件优先)
    if stat_rows:
        ranked = sorted(stat_rows, key=lambda r: -r['stretch_x_cv'])
        print(f"\n=== 弱势部件排行 (按 stretch_x 变异系数 CV 降序) ===")
        print(f"{'部件':<6} {'位':<6} {'N':>5} "
              f"{'str_mean':>8} {'str_std':>7} {'str_CV':>7} "
              f"{'cmp_mean':>8} {'net_mean':>8}")
        print("-" * 72)
        for r in ranked[:50]:
            print(f"{r['comp']:<6} {r['pos']:<6} {r['n']:>5} "
                  f"{r['stretch_x_mean']:>8.3f} {r['stretch_x_std']:>7.3f} {r['stretch_x_cv']:>7.3f} "
                  f"{r['compress_x_mean']:>8.3f} {r['net_x_mean']:>8.3f}")

    print(f"\n共 {len(stat_rows)} 种 (部件,位置) 组合", flush=True)


if __name__ == "__main__":
    main()
