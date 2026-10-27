"""
验证改进的 bbox/矩形分配算法原型
纯数据层面——不做实际渲染，只计算矩 + 分配

用法: python scripts/test_bbox_alloc.py
"""
import sys, io, math, json

# ============================================================
# 1. KAGE 数据解析 & 矩计算
# ============================================================

class BBox:
    __slots__ = ('x1', 'y1', 'x2', 'y2')
    def __init__(self):
        self.x1 = self.y1 = 200
        self.x2 = self.y2 = 0
    def valid(self): return self.x1 <= self.x2 and self.y1 <= self.y2
    def width(self): return max(0, self.x2 - self.x1) if self.valid() else 0
    def height(self): return max(0, self.y2 - self.y1) if self.valid() else 0
    def expand(self, x, y):
        self.x1 = min(self.x1, x); self.x2 = max(self.x2, x)
        self.y1 = min(self.y1, y); self.y2 = max(self.y2, y)
    def __repr__(self):
        return f"BBox({self.x1},{self.y1}-{self.x2},{self.y2})"

class MomentInfo:
    """从 KAGE 笔画坐标计算的结构化统计量"""
    __slots__ = ('cx', 'cy', 'sx', 'sy', 'bbox', 'x_profile', 'y_profile', 'n_points')
    def __init__(self):
        self.cx = 100.0; self.cy = 100.0   # 质心
        self.sx = 0.0; self.sy = 0.0        # 标准差 (散布)
        self.bbox = BBox()
        self.x_profile = []   # 横向密度投影 (10px/桶, 20桶)
        self.y_profile = []   # 纵向密度投影
        self.n_points = 0

    def edge_left(self):   return self.bbox.x1
    def edge_right(self):  return self.bbox.x2
    def edge_top(self):    return self.bbox.y1
    def edge_bottom(self): return self.bbox.y2

    def describe(self):
        return (f"μ=({self.cx:.0f},{self.cy:.0f}) σ=({self.sx:.0f},{self.sy:.0f}) "
                f"bbox=({self.bbox.x1},{self.bbox.y1}-{self.bbox.x2},{self.bbox.y2}) "
                f"W={self.bbox.width()} H={self.bbox.height()}")

def parse_kage_strokes(data_str):
    """将 KAGE 数据字符串解析为 (type, [x1,y1,...]) 列表"""
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
        coords = []
        for p in parts[1:]:
            try: coords.append(int(p))
            except ValueError: coords.append(0)
        strokes.append((kind, coords))
    return strokes

def resolve_kage(data_str, glyph_db, visited=None):
    """递归展开 type-99, 返回纯笔画坐标点列表 [(x,y), ...]"""
    if visited is None: visited = set()
    points = []

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
            # type-99: 递归解析
            ref_name = parts[7]
            at_idx = ref_name.find('@')
            base = ref_name[:at_idx] if at_idx > 0 else ref_name
            if base not in visited and base in glyph_db:
                visited.add(base)
                sx1 = int(parts[3]); sy1 = int(parts[4])
                sx2 = int(parts[5]); sy2 = int(parts[6])
                sub_pts = resolve_kage(glyph_db[base], glyph_db, visited)
                # 坐标映射到目标矩形
                for (x, y) in sub_pts:
                    mx = sx1 + (x / 200.0) * (sx2 - sx1)
                    my = sy1 + (y / 200.0) * (sy2 - sy1)
                    points.append((mx, my))
        elif kind >= 0 and kind <= 8:
            # 普通笔画: 坐标从 parts[3] 开始 (跳过 a2, a3)
            for i in range(3, len(parts), 2):
                if i + 1 < len(parts):
                    try:
                        x = int(parts[i])
                        y = int(parts[i+1])
                        points.append((x, y))
                    except ValueError:
                        pass
    return points

def compute_moments(data_str, glyph_db):
    """从 KAGE 数据计算矩信息"""
    points = resolve_kage(data_str, glyph_db, set())
    info = MomentInfo()
    info.n_points = len(points)
    if info.n_points == 0:
        return info

    # 一阶矩: 质心
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    info.cx = sum_x / info.n_points
    info.cy = sum_y / info.n_points

    # 二阶矩: 标准差
    var_x = sum((p[0] - info.cx) ** 2 for p in points) / info.n_points
    var_y = sum((p[1] - info.cy) ** 2 for p in points) / info.n_points
    info.sx = math.sqrt(var_x)
    info.sy = math.sqrt(var_y)

    # bbox
    for (x, y) in points:
        info.bbox.expand(int(x), int(y))

    # 密度投影 (20桶 × 20桶，每桶10px)
    BINS = 20
    x_hist = [0] * BINS
    y_hist = [0] * BINS
    for (x, y) in points:
        bx = min(int(x / 10), BINS - 1)
        by = min(int(y / 10), BINS - 1)
        x_hist[bx] += 1
        y_hist[by] += 1
    info.x_profile = [c / info.n_points for c in x_hist]  # 归一化
    info.y_profile = [c / info.n_points for c in y_hist]
    return info


# ============================================================
# 2. 弱势偏旁表
# ============================================================

# 格式: {字符: {(操作符, 位置): 建议占有率}}
# 占有率指该部件在主要方向上的占比
# ⿰ pos=0(左): 占比 = 部件宽度 / 总宽
# ⿱ pos=0(上): 占比 = 部件高度 / 总高
WEAK_RADICAL_TABLE = {
    # ⿰ 窄左旁
    '亻': {('⿰', 0): 0.22},
    '刂': {('⿰', 0): 0.20},
    '口': {('⿰', 0): 0.25},
    '日': {('⿰', 0): 0.28},
    '月': {('⿰', 0): 0.30},
    '氵': {('⿰', 0): 0.24},
    '扌': {('⿰', 0): 0.26},
    '忄': {('⿰', 0): 0.22},
    '王': {('⿰', 0): 0.30},
    '石': {('⿰', 0): 0.32},
    '土': {('⿰', 0): 0.28},
    '火': {('⿰', 0): 0.30},
    '木': {('⿰', 0): 0.32},
    '水': {('⿰', 0): 0.32},
    '言': {('⿰', 0): 0.35},
    # ⿱ 矮上旁
    '艹': {('⿱', 0): 0.18},
    '日': {('⿱', 0): 0.30},
    '口': {('⿱', 0): 0.25},
}

def lookup_weak_radical(ch, op_cp, position):
    op_name = {0x2FF0: '⿰', 0x2FF1: '⿱'}.get(op_cp, '?')
    entry = WEAK_RADICAL_TABLE.get(ch, {})
    return entry.get((op_name, position), None)


# ============================================================
# 3. 矩形分配算法
# ============================================================

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def compute_seam_overlap(L_moment, R_moment, split, op_cp):
    """
    在 split 线两侧 ±15px 带状区域内检测密度
    返回建议的重叠量 (正=加大重叠, 负=拉开)
    """
    HALF_BAND = 15  # 检测带宽
    BINS = 20       # 200/10

    # 获取密度投影
    if op_cp == 0x2FF0:  # ⿰ 左右
        L_prof = L_moment.x_profile
        R_prof = R_moment.x_profile
    else:  # ⿱ 上下
        L_prof = L_moment.y_profile
        R_prof = R_moment.y_profile

    # 将 split 映射到桶索引
    split_bin = split / 10  # 0-20

    # 左/上侧 密度: split 附近的 L 部件密度
    L_band_start = int(max(0, split_bin - HALF_BAND / 10))
    L_band_end = int(min(BINS, split_bin))
    L_density = sum(L_prof[L_band_start:L_band_end]) if L_band_end > L_band_start else 0

    # 右/下侧 密度: split 附近的 R 部件密度
    R_band_start = int(max(0, split_bin))
    R_band_end = int(min(BINS, split_bin + HALF_BAND / 10))
    R_density = sum(R_prof[R_band_start:R_band_end]) if R_band_end > R_band_start else 0

    # 密度均衡判断
    total_density = L_density + R_density
    if total_density < 0.05:
        # 两侧都稀疏 → 可以加大重叠
        base_overlap = 18
    elif L_density > 0.15 and R_density > 0.15:
        # 两侧都密集 → 笔画可能碰撞，拉开
        base_overlap = 4
    elif L_density > R_density * 3:
        # L密集 R稀疏 → 让L退让
        base_overlap = 6
    elif R_density > L_density * 3:
        # R密集 L稀疏 → 让R退让
        base_overlap = 6
    else:
        # 正常: 按密度差线性插值
        base_overlap = 12 - (L_density + R_density) * 20

    return clamp(int(base_overlap), 2, 30)


def allocate_rectangle_horizontal(L_data, R_data, L_char, R_char, glyph_db):
    """
    ⿰ 左右结构矩形分配
    返回: (left_rect, right_rect, split, overlap, debug_info)
    """
    L = compute_moments(L_data, glyph_db)
    R = compute_moments(R_data, glyph_db)

    if L.n_points == 0 or R.n_points == 0:
        return (3, 3, 100, 200), (100, 3, 200, 200), 100, 12, "no_data"

    debug = []

    # ---- 第一层: 弱势偏旁表 ----
    table_L = lookup_weak_radical(L_char, 0x2FF0, 0)
    table_R = lookup_weak_radical(R_char, 0x2FF0, 1)

    if table_L is not None:
        w1_share = table_L
        debug.append(f"表-L={table_L:.2f}")
    elif table_R is not None:
        w1_share = 1.0 - table_R
        debug.append(f"表-R(反推)={w1_share:.2f}")
    else:
        # bbox + 散布修正
        L_eff = L.bbox.width() * (0.7 + 0.3 * max(1, L.sx / 50))
        R_eff = R.bbox.width() * (0.7 + 0.3 * max(1, R.sx / 50))
        w1_share = clamp(L_eff / (L_eff + R_eff), 0.15, 0.85)
        debug.append(f"bbox W_L={L.bbox.width()} W_R={R.bbox.width()}→{w1_share:.2f}")

    # ---- 第一遍: 初始 split ----
    split = int(3 + 194 * w1_share)
    split = clamp(split, 25, 175)
    debug.append(f"split0={split}")

    # ---- 第二层: 重心居中调整 ----
    # 将部件质心映射到分配矩形内, 检查是否偏离中心
    L_rect_w = split - 3
    R_rect_w = 200 - split

    if L.bbox.width() > 0:
        L_mapped_cx = 3 + L_rect_w * (L.cx - L.bbox.x1) / L.bbox.width()
    else:
        L_mapped_cx = 3 + L_rect_w / 2
    L_mapped_cx = clamp(L_mapped_cx, 3, split)

    if R.bbox.width() > 0:
        R_mapped_cx = split + R_rect_w * (R.cx - R.bbox.x1) / R.bbox.width()
    else:
        R_mapped_cx = split + R_rect_w / 2
    R_mapped_cx = clamp(R_mapped_cx, split, 200)

    L_center = (3 + split) / 2
    R_center = (split + 200) / 2

    L_offset = L_mapped_cx - L_center  # >0 偏右, <0 偏左
    R_offset = R_mapped_cx - R_center

    # 偏移方向一致则同步调整
    adjust = (L_offset + R_offset) * 0.35
    split = int(split + adjust)
    split = clamp(split, 25, 175)
    debug.append(f"L_off={L_offset:+.0f} R_off={R_offset:+.0f} adj={adjust:+.0f} split1={split}")

    # ---- 第三层: 接缝密度检测 ----
    overlap = compute_seam_overlap(L, R, split, 0x2FF0)
    debug.append(f"overlap={overlap}")

    # ---- 生成矩形 ----
    L_rect = (3, 3, split + overlap // 2, 200)
    R_rect = (split - overlap // 2, 3, 200, 200)

    debug_str = " | ".join(debug)
    return L_rect, R_rect, split, overlap, debug_str


def allocate_rectangle_vertical(T_data, B_data, T_char, B_char, glyph_db):
    """
    ⿱ 上下结构矩形分配
    """
    T = compute_moments(T_data, glyph_db)
    B = compute_moments(B_data, glyph_db)

    if T.n_points == 0 or B.n_points == 0:
        return (3, 3, 200, 100), (3, 100, 200, 200), 100, 6, "no_data"

    debug = []

    # ---- 第一层: 弱势偏旁表 ----
    table_T = lookup_weak_radical(T_char, 0x2FF1, 0)
    table_B = lookup_weak_radical(B_char, 0x2FF1, 1)

    if table_T is not None:
        h1_share = table_T
        debug.append(f"表-T={h1_share:.2f}")
    elif table_B is not None:
        h1_share = 1.0 - table_B
        debug.append(f"表-B(反推)={h1_share:.2f}")
    else:
        T_eff = T.bbox.height() * (0.7 + 0.3 * max(1, T.sy / 50))
        B_eff = B.bbox.height() * (0.7 + 0.3 * max(1, B.sy / 50))
        h1_share = clamp(T_eff / (T_eff + B_eff), 0.12, 0.88)
        debug.append(f"bbox H_T={T.bbox.height()} H_B={B.bbox.height()}→{h1_share:.2f}")

    # ---- 第一遍: 初始 split ----
    split = int(3 + 194 * h1_share)
    split = clamp(split, 20, 180)
    debug.append(f"split0={split}")

    # ---- 第二层: 重心居中调整 ----
    T_rect_h = split - 3
    B_rect_h = 200 - split

    if T.bbox.height() > 0:
        T_mapped_cy = 3 + T_rect_h * (T.cy - T.bbox.y1) / T.bbox.height()
    else:
        T_mapped_cy = 3 + T_rect_h / 2
    T_mapped_cy = clamp(T_mapped_cy, 3, split)

    if B.bbox.height() > 0:
        B_mapped_cy = split + B_rect_h * (B.cy - B.bbox.y1) / B.bbox.height()
    else:
        B_mapped_cy = split + B_rect_h / 2
    B_mapped_cy = clamp(B_mapped_cy, split, 200)

    T_center = (3 + split) / 2
    B_center = (split + 200) / 2

    T_offset = T_mapped_cy - T_center
    B_offset = B_mapped_cy - B_center

    adjust = (T_offset + B_offset) * 0.35
    split = int(split + adjust)
    split = clamp(split, 20, 180)
    debug.append(f"T_off={T_offset:+.0f} B_off={B_offset:+.0f} adj={adjust:+.0f} split1={split}")

    # ---- 第三层: 接缝密度检测 ----
    overlap = compute_seam_overlap(T, B, split, 0x2FF1)
    debug.append(f"overlap={overlap}")

    # ---- 生成矩形 ----
    T_rect = (3, 3, 200, split + overlap // 2)
    B_rect = (3, split - overlap // 2, 200, 200)

    debug_str = " | ".join(debug)
    return T_rect, B_rect, split, overlap, debug_str


# ============================================================
# 4. 当前算法 (对比基准)
# ============================================================

def current_allocate_horizontal(L_data, R_data, glyph_db):
    """模拟当前 C++ buildComposite 的 ⿰ 分配逻辑"""
    L = compute_moments(L_data, glyph_db)
    R = compute_moments(R_data, glyph_db)

    w1 = L.bbox.width() if (L.bbox.valid() and L.bbox.width() < 170) else 100
    w2 = R.bbox.width() if (R.bbox.valid() and R.bbox.width() < 170) else 100
    if w1 < 5: w1 = 5
    if w2 < 5: w2 = 5
    split = 3 + (194 * w1 // (w1 + w2))
    split = clamp(split, 20, 180)

    # 当前动态重叠
    if L.bbox.valid() and R.bbox.valid():
        gap1 = 200 - L.bbox.x2
        gap2 = R.bbox.x1
        extra = int((gap1 + gap2) * 0.60)
        overlap = clamp(6 + extra, 10, 100)
    else:
        overlap = 12

    L_rect = (3, 3, split + overlap // 2, 200)
    R_rect = (split - overlap // 2, 3, 200, 200)
    return L_rect, R_rect, split, overlap


def current_allocate_vertical(T_data, B_data, glyph_db):
    """模拟当前 C++ 的 ⿱ 分配逻辑"""
    T = compute_moments(T_data, glyph_db)
    B = compute_moments(B_data, glyph_db)

    h1 = T.bbox.height() if (T.bbox.valid() and T.bbox.height() < 170) else 100
    h2 = B.bbox.height() if (B.bbox.valid() and B.bbox.height() < 170) else 100
    if h1 < 5: h1 = 5
    if h2 < 5: h2 = 5
    prop = 3 + (200 * h1 // (h1 + h2))
    split = (prop + 100 * 3) // 4
    split = clamp(split, 68, 132)

    if T.bbox.valid() and B.bbox.valid():
        gap1 = 200 - T.bbox.y2
        gap2 = B.bbox.y1
        extra = int((gap1 + gap2) * 0.80)
        overlap = clamp(6 + extra, 6, 90)
    else:
        overlap = 6

    T_rect = (3, 3, 200, split + overlap // 2)
    B_rect = (3, split - overlap // 2, 200, 200)
    return T_rect, B_rect, split, overlap


# ============================================================
# 5. 加载数据 & 运行测试
# ============================================================

def load_glyph_db(dump_path, targets):
    """从 dump 文件加载指定字形名及其 type-99 依赖的 KAGE 数据"""
    # 第一遍: 找直接目标
    found = {}
    deps = set()
    with open(dump_path, encoding='utf-8') as f:
        f.readline(); f.readline()  # skip headers
        for line in f:
            if not line.startswith(' u'): continue
            cols = line.split(' | ')
            if len(cols) < 3: continue
            name = cols[0].strip()
            if name in targets:
                data = cols[2].strip()
                found[name] = data
                # 收集 type-99 依赖
                for seg in data.split('$'):
                    seg = seg.strip()
                    if seg.startswith('99:'):
                        p = seg.split(':')
                        if len(p) >= 8:
                            ref = p[7].split('@')[0]
                            if ref not in targets:
                                deps.add(ref)

    # 第二遍: 加载依赖
    all_targets = set(targets) | deps
    with open(dump_path, encoding='utf-8') as f:
        f.readline(); f.readline()
        for line in f:
            if not line.startswith(' u'): continue
            cols = line.split(' | ')
            if len(cols) < 3: continue
            name = cols[0].strip()
            if name in all_targets and name not in found:
                found[name] = cols[2].strip()
    return found


# ============================================================
# 字符 → KAGE 键名映射 (模块级别)
# base: 独立使用, pos0: 左/上位置, pos1: 右/下位置
# ============================================================
CHAR_TO_KEYS = {
    '亻': {'base': 'u4ebb-j', 'pos0': 'u4ebb-01'},
    '尔': {'base': 'u5c14-j', 'pos1': 'u5c14-02'},
    '木': {'base': 'u6728-j', 'pos0': 'u6728-01', 'pos1': 'u6728-02'},
    '子': {'base': 'u5b50-j', 'pos0': 'u5b50-01', 'pos1': 'u5b50-04'},
    '口': {'base': 'u53e3-j', 'pos0': 'u53e3-01'},
    '日': {'base': 'u65e5-j', 'pos0': 'u65e5-01'},
    '月': {'base': 'u6708-j', 'pos0': 'u6708-01'},
    '人': {'base': 'u4eba-j'},
    '言': {'base': 'u8a00-j'},
    '水': {'base': 'u6c34-j', 'pos0': 'u6c34-01'},
    '火': {'base': 'u706b-j', 'pos0': 'u706b-01'},
    '土': {'base': 'u571f-j', 'pos0': 'u571f-01'},
    '艹': {'base': 'u8279-j', 'pos0': 'u8279-03'},
    '朋': {'base': 'u670b-j'},
}

def get_variant_key(ch, pos_idx):
    """根据在结构中的位置获取正确的变体键名"""
    info = CHAR_TO_KEYS.get(ch, {})
    pos_key = 'pos0' if pos_idx == 0 else 'pos1'
    return info.get(pos_key, info.get('base', ''))


def run_tests(dump_path):
    """运行测试用例"""

    # 测试用例: (描述, IDS操作符, 左/上字符, 右/下字符)
    test_cases = [
        # ⿰ 左右
        ("⿰亻尔",  0x2FF0, '亻', '尔'),
        ("⿰口口",  0x2FF0, '口', '口'),
        ("⿰口木",  0x2FF0, '口', '木'),
        ("⿰木子",  0x2FF0, '木', '子'),
        ("⿰木木",  0x2FF0, '木', '木'),
        ("⿰火火",  0x2FF0, '火', '火'),
        ("⿰土土",  0x2FF0, '土', '土'),
        ("⿰日月",  0x2FF0, '日', '月'),
        ("⿰人言",  0x2FF0, '人', '言'),
        ("⿰水水",  0x2FF0, '水', '水'),
        ("⿰亻言",  0x2FF0, '亻', '言'),
        # ⿱ 上下
        ("⿱日木",  0x2FF1, '日', '木'),
        ("⿱艹朋",  0x2FF1, '艹', '朋'),
        ("⿱口木",  0x2FF1, '口', '木'),
        ("⿱日日",  0x2FF1, '日', '日'),
    ]

    # 收集所有需要的 KAGE 名
    all_keys = set()
    for _, _, c1, c2 in test_cases:
        for pos_idx, c in enumerate([c1, c2]):
            k = get_variant_key(c, pos_idx)
            if k: all_keys.add(k)

    print(f"加载 {len(all_keys)} 个字形数据...")
    glyph_db = load_glyph_db(dump_path, all_keys)
    print(f"实际加载: {len(glyph_db)} 个\n")

    # 运行对比
    dash = "-" * 108
    header = f"{'IDS':<10} {'部件矩 (L/T)':<40} {'部件矩 (R/B)':<40} {'现split':>6} {'新split':>6} {'调试信息'}"
    print(header)
    print(dash)

    for desc, op_cp, c1, c2 in test_cases:
        k1 = get_variant_key(c1, 0)
        k2 = get_variant_key(c2, 1)
        d1 = glyph_db.get(k1, '')
        d2 = glyph_db.get(k2, '')

        if not d1 or not d2:
            print(f"{desc:<10} 跳过 (缺数据)")
            continue

        if op_cp == 0x2FF0:
            # 当前
            _, _, cur_split, cur_ol = current_allocate_horizontal(d1, d2, glyph_db)
            # 新
            _, _, new_split, new_ol, debug_str = allocate_rectangle_horizontal(
                d1, d2, c1, c2, glyph_db)
        else:
            _, _, cur_split, cur_ol = current_allocate_vertical(d1, d2, glyph_db)
            _, _, new_split, new_ol, debug_str = allocate_rectangle_vertical(
                d1, d2, c1, c2, glyph_db)

        # 矩信息 (短版)
        Lm = compute_moments(d1, glyph_db)
        Rm = compute_moments(d2, glyph_db)

        L_short = f"W={Lm.bbox.width():>3} H={Lm.bbox.height():>3} cx={Lm.cx:>5.0f} cy={Lm.cy:>5.0f}"
        R_short = f"W={Rm.bbox.width():>3} H={Rm.bbox.height():>3} cx={Rm.cx:>5.0f} cy={Rm.cy:>5.0f}"

        split_str = f"{cur_split}+{cur_ol:>2}"
        new_str  = f"{new_split}+{new_ol:>2}"

        marker = ""
        if abs(new_split - cur_split) > 10:
            marker = " <<<"

        print(f"{desc:<10} {L_short:<40} {R_short:<40} {split_str:>9} {new_str:>9}  {debug_str}{marker}")

    print(dash)
    print()

    # 详细矩信息
    print("=" * 80)
    print("详细矩信息")
    print("=" * 80)
    for ch in sorted(CHAR_TO_KEYS.keys()):
        info = CHAR_TO_KEYS[ch]
        k = info.get('base', '')
        d = glyph_db.get(k, '')
        if not d: continue
        if not d: continue
        m = compute_moments(d, glyph_db)
        print(f"  {ch} ({k}): {m.describe()}")
        prof_str = "  X密度: " + "".join(
            f"{'█' if v > 0.08 else '▄' if v > 0.04 else '·'}" for v in m.x_profile
        )
        print(prof_str)
        prof_str = "  Y密度: " + "".join(
            f"{'█' if v > 0.08 else '▄' if v > 0.04 else '·'}" for v in m.y_profile
        )
        print(prof_str)


if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    run_tests("D:/KAGE_GLYPH/dump_newest_only.txt")
