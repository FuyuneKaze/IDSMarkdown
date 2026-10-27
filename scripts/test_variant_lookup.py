"""
验证 IDS 变体查找算法
不依赖 C++ 编译，纯 Python 原型
"""

import sys
import os
from collections import defaultdict

# Windows 下强制 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============================================================
# 1. 加载 dump 索引（只记名字，不加载完整数据）
# ============================================================

def load_dump_index(dump_path):
    """返回 set: dump 中所有可用的字形名"""
    names = set()
    print(f"加载 dump 索引: {dump_path}")
    with open(dump_path, 'r', encoding='utf-8') as f:
        f.readline()  # 表头
        f.readline()  # 分隔线
        for i, line in enumerate(f):
            if line[0] != ' ': continue
            # name 列: 第一个 | 之前
            pipe = line.find(' | ')
            if pipe < 0: continue
            name = line[1:pipe].strip()
            names.add(name)
            if (i+1) % 500000 == 0:
                print(f"  {i+1} 行... ({len(names)} 个有效名)")
    print(f"  完成: {len(names)} 个字形名")
    return names


# ============================================================
# 2. IDS 操作符识别
# ============================================================

# U+2FF0 ~ U+2FFF
IDS_OPS = set(chr(c) for c in range(0x2FF0, 0x3000))
IDS_OPS.add(chr(0x31EF))  # 扩展

BINARY_OPS  = {chr(c) for c in [0x2FF0, 0x2FF1, 0x2FF4, 0x2FF5, 0x2FF6,
                                 0x2FF7, 0x2FF8, 0x2FF9, 0x2FFA, 0x2FFB,
                                 0x2FFC, 0x2FFD, 0x2FFE, 0x2FFF, 0x31EF]}
TERNARY_OPS = {chr(0x2FF2), chr(0x2FF3)}  # ⿲ ⿳

OP_NAMES = {
    0x2FF0: '⿰', 0x2FF1: '⿱', 0x2FF2: '⿲', 0x2FF3: '⿳',
    0x2FF4: '⿴', 0x2FF5: '⿵', 0x2FF6: '⿶', 0x2FF7: '⿷',
    0x2FF8: '⿸', 0x2FF9: '⿹', 0x2FFA: '⿺', 0x2FFB: '⿻',
    0x2FFC: '⿼', 0x2FFD: '⿽', 0x2FFE: '⿾', 0x2FFF: '⿿',
    0x31EF: '㇯',
}

def op_name(op):
    return OP_NAMES.get(ord(op), f'U+{ord(op):04X}')

def is_ids_op(ch):
    return ord(ch) in range(0x2FF0, 0x3000) or ord(ch) == 0x31EF

def is_binary(op):
    return op in BINARY_OPS

def is_ternary(op):
    return op in TERNARY_OPS

# 包围操作符: outer 是全区域框架, inner 嵌在里面
SURROUND_OPS = {chr(c) for c in [0x2FF4, 0x2FF5, 0x2FF6, 0x2FF7,
                                  0x2FF8, 0x2FF9, 0x2FFA]}


# ============================================================
# 3. IDS 解析为树
# ============================================================

class IDSNode:
    def __init__(self, op=None, children=None, char=None):
        self.op = op          # 操作符字符 (None 表示叶子)
        self.children = children or []  # 子节点列表
        self.char = char      # 叶子字符 (仅叶子有值)
        self.position = None  # 在父节点中的位置 (0-based)
        self.depth = 0        # 距离根的操作符层数

    def is_leaf(self):
        return self.op is None

    def __repr__(self):
        if self.is_leaf():
            return f"Leaf({self.char!r} pos={self.position})"
        return f"Node({op_name(self.op)} {self.children})"


def parse_ids(ids, pos=0, depth=0):
    """递归解析 IDS 字符串为树，返回 (node, new_pos)"""
    if pos >= len(ids):
        return None, pos

    ch = ids[pos]
    if not is_ids_op(ch):
        # 叶子节点 (普通字符)
        node = IDSNode(char=ch)
        node.depth = depth
        return node, pos + 1

    # 内部节点 (操作符)
    op = ch
    arity = 3 if is_ternary(op) else 2
    pos += 1

    node = IDSNode(op=op)
    node.depth = depth
    for k in range(arity):
        if pos >= len(ids): break
        child, pos = parse_ids(ids, pos, depth + 1)
        if child:
            child.position = k
            node.children.append(child)

    return node, pos


# ============================================================
# 4. 变体查找核心逻辑
# ============================================================

def position_suffix(position, op, arity):
    """
    根据操作符和孩子序号返回期望的位置后缀。
    position: 0-based
    """
    op_cp = ord(op)

    # 包围结构
    if op in SURROUND_OPS:
        if position == 0:  # outer
            return 'j'  # 包围外框优先日式变体
        else:  # inner
            # inner 的位置取决于包围类型
            if op_cp in [0x2FF8]:  # ⿸ 左上包: inner 在右下
                return '04'
            elif op_cp in [0x2FF9]:  # ⿹ 右上包: inner 在左下
                return '04'
            elif op_cp in [0x2FFA]:  # ⿺ 左下包: inner 在右上
                return '03'
            else:  # 全包/上包/下包/左包: inner 居中
                return '01'

    # 重叠
    if op_cp == 0x2FFB:  # ⿻
        return '01' if position == 0 else '01'

    # ⿰ 左右
    if op_cp == 0x2FF0:
        return '01' if position == 0 else '02'

    # ⿱ 上下
    if op_cp == 0x2FF1:
        return '03' if position == 0 else '04'

    # ⿲ 左中右
    if op_cp == 0x2FF2:
        return ['01', '01', '02'][position] if position < 3 else '01'

    # ⿳ 上中下
    if op_cp == 0x2FF3:
        return ['03', '03', '04'][position] if position < 3 else '04'

    # 扩展操作符: 默认
    return '01'


def select_variant(char, position, op, arity, names_set):
    """为叶子字符查找最佳变体名"""
    cp = ord(char)
    hex_str = f'{cp:04x}'
    suffix = position_suffix(position, op, arity)

    candidates = [
        f'u{hex_str}-g{suffix}',      # 中国+位置
        f'u{hex_str}-{suffix}',       # 纯位置
        f'u{hex_str}-j',              # 日式
        f'u{hex_str}',                 # 标准
    ]

    for c in candidates:
        if c in names_set:
            # 标记是否精确命中(前两个候选)还是兜底
            precise = (c == candidates[0] or c == candidates[1])
            return c, precise

    # 完全没找到
    return None, False


# ============================================================
# 5. 树遍历 + 变体选择
# ============================================================

def analyze_tree(node, op, position, names_set, results, depth=0):
    """递归遍历 IDS 树，为每个叶子选择变体"""
    indent = "  " * depth

    if node.is_leaf():
        variant, precise = select_variant(node.char, position, op, 2, names_set)
        hex_str = f'{ord(node.char):04X}'
        status = "✓精确" if precise else ("○兜底" if variant else "✗缺失")
        results.append({
            'char': node.char,
            'hex': hex_str,
            'position': position,
            'depth': depth,
            'variant': variant,
            'precise': precise,
        })
        print(f"{indent}叶子 U+{hex_str} '{node.char}' pos={position} depth={depth} → {variant or 'NOT FOUND'} {status}")
        return variant is not None

    # 内部节点: 递归处理子节点
    arity = len(node.children)
    print(f"{indent}{op_name(node.op)} (arity={arity}, depth={depth})")
    all_ok = True
    for i, child in enumerate(node.children):
        ok = analyze_tree(child, node.op, i, names_set, results, depth + 1)
        if not ok:
            all_ok = False
    return all_ok


# ============================================================
# 6. 测试
# ============================================================

def test_case(name, ids, names_set):
    print(f"\n{'='*60}")
    print(f"测试: {name}  ({ids})")
    print(f"{'='*60}")

    root, end = parse_ids(ids, 0)
    if root is None or end != len(ids):
        print(f"  解析失败! pos={end}/{len(ids)}")
        return

    results = []
    # 根节点自身不是叶子，用虚拟操作符 context
    all_ok = analyze_tree(root, None, 0, names_set, results)

    # 汇总
    print(f"\n  汇总: {'全部找到' if all_ok else '有缺失'}")
    for r in results:
        print(f"    U+{r['hex']} '{r['char']}' → {r['variant']} ({'精确' if r['precise'] else '兜底'})")
    return results


if __name__ == '__main__':
    dump_path = r'D:\KAGE_GLYPH\dump_newest_only.txt'

    if not os.path.exists(dump_path):
        print(f"dump 文件不存在: {dump_path}")
        print("跳过 dump 加载，仅测试 IDS 解析...")
        names_set = set()
    else:
        names_set = load_dump_index(dump_path)

    # ---- 已知字验证 ----
    test_case('鸠', '⿰九鸟', names_set)
    test_case('秋', '⿰禾火', names_set)
    test_case('李', '⿱木子', names_set)
    test_case('国', '⿴囗玉', names_set)
    test_case('僻', '⿰亻辟', names_set)  # 两字符简化

    # ---- 表外字测试 ----
    test_case('表外_⿰石另', '⿰石另', names_set)
    test_case('表外_⿱⿰亻山木', '⿱⿰亻山木', names_set)

    print(f"\n{'='*60}")
    print("验证完成")
