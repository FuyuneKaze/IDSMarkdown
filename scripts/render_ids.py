"""
IDS → KAGE → SVG 渲染脚本 (v2 — 支持嵌套 IDS, 默认明朝体)
用法: python render_ids.py "⿰⿱甲乙丙" [--gothic] [--size N]
输出: SVG 字符串到 stdout
"""
import sys
import csv
import svgwrite
from kage import Kage
from kage.font.sans import Sans
from kage.font.serif import Serif

# ---- IDS 操作符 → 部件坐标映射 (200×200 画布) ----
# 格式: [(x1, y1, x2, y2), ...] 每个部件在画布中的矩形区域

LAYOUTS = {
    # arity 2
    0x2FF0: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ⿰ 左右
    0x2FF1: [(0, 0, 200, 100), (0, 100, 200, 200)],       # ⿱ 上下
    0x2FF4: [(0, 0, 200, 200), (40, 40, 160, 160)],       # ⿴ 全包围
    0x2FF5: [(0, 0, 200, 200), (40, 60, 160, 200)],       # ⿵ 上包围
    0x2FF6: [(0, 0, 200, 200), (40, 0, 160, 140)],        # ⿶ 下包围
    0x2FF7: [(0, 0, 200, 200), (50, 40, 200, 160)],       # ⿷ 左包围
    0x2FF8: [(0, 0, 200, 200), (60, 60, 200, 200)],       # ⿸ 左上包围
    0x2FF9: [(0, 0, 200, 200), (0, 60, 140, 200)],        # ⿹ 右上包围
    0x2FFA: [(0, 0, 200, 200), (60, 0, 200, 140)],        # ⿺ 左下包围
    0x2FFB: [(0, 0, 200, 200), (0, 0, 200, 200)],         # ⿻ 重叠
    0x2FFC: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ⿼ 扩展
    0x2FFD: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ⿽ 扩展
    0x2FFE: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ⿾ 扩展
    0x2FFF: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ⿿ 扩展
    0x31EF: [(0, 0, 100, 200), (100, 0, 200, 200)],       # ㇯ 扩展
    # arity 3
    0x2FF2: [(0, 0, 66, 200), (66, 0, 133, 200), (133, 0, 200, 200)],  # ⿲ 左中右
    0x2FF3: [(0, 0, 200, 66), (0, 66, 200, 133), (0, 133, 200, 200)],  # ⿳ 上中下
}


def is_ids_op(ch: str) -> bool:
    cp = ord(ch)
    return (0x2FF0 <= cp <= 0x2FFF) or cp == 0x31EF


def ids_arity(op: str) -> int:
    cp = ord(op)
    return 3 if cp in (0x2FF2, 0x2FF3) else 2


# ---- 递归 IDS 解析 ----

def parse_ids_tree(ids: str, pos: int = 0):
    """
    递归解析 IDS 字符串，返回 (consumed, tree | leaf_char)
    tree = (operator, [children...])
    leaf_char = 单个非 IDS 操作符字符
    如果格式不完整返回 (0, None)
    """
    if pos >= len(ids):
        return 0, None

    ch = ids[pos]
    if not is_ids_op(ch):
        return 1, ch  # 叶子节点: 单个字符

    op = ch
    arity = ids_arity(op)
    consumed = 1  # 操作符自身
    children = []

    for _ in range(arity):
        sub_consumed, child = parse_ids_tree(ids, pos + consumed)
        if sub_consumed == 0 or child is None:
            return 0, None  # 部件不足
        consumed += sub_consumed
        children.append(child)

    return consumed, (op, children)


def tree_to_str(tree) -> str:
    """将解析树转回 IDS 字符串"""
    if isinstance(tree, str):
        return tree
    op, children = tree
    return op + ''.join(tree_to_str(c) for c in children)


# ---- KAGE 合成 ----

def char_to_name(ch: str) -> str:
    return f'u{ord(ch):04x}'


def resolve_kage_name(ch: str, kage: Kage) -> str | None:
    """查找字符对应的 KAGE glyph 名称，尝试多个变体后缀"""
    base = char_to_name(ch)
    if kage.components.search(base):
        return base
    for suffix in ['', '-j', '-01', '-02', '-jv', '-jn']:
        name = base + suffix
        if kage.components.search(name):
            return name
    return None


def build_kage_composites(tree, kage: Kage, counter: list) -> str | None:
    """
    自底向上为 IDS 语法树生成 KAGE 合成数据。
    叶子节点 → KAGE glyph 名称
    内部节点 → 生成 type-99 合成数据, 注册为临时部件, 返回临时名称
    返回顶层部件的 KAGE 名称, 或 None 表示失败
    """
    if isinstance(tree, str):
        # 叶子: 单字 → 查找 KAGE glyph
        name = resolve_kage_name(tree, kage)
        if name is None:
            print(f'Warning: glyph not found for {tree} (U+{ord(tree):04X})', file=sys.stderr)
            return None
        return name

    op, children = tree
    layouts = LAYOUTS.get(ord(op))
    if layouts is None:
        return None

    # 先递归编译子节点
    child_names = []
    for child in children:
        cname = build_kage_composites(child, kage, counter)
        if cname is None:
            return None
        child_names.append(cname)

    # 生成当前节点的 KAGE 合成数据
    strokes = []
    for i, cname in enumerate(child_names):
        x1, y1, x2, y2 = layouts[i]
        # KAGE type 99: 99:sx:sy:x1:y1:x2:y2:name:sx2:sy2
        strokes.append(f'99:0:0:{x1}:{y1}:{x2}:{y2}:{cname}')

    kage_data = '$'.join(strokes)

    # 注册为临时部件
    tmp_name = f'_k{len(counter)}'
    counter.append(1)
    kage.components.push(tmp_name, kage_data)
    return tmp_name


# ---- 主渲染函数 ----

def render_ids(ids: str, use_gothic: bool = False, size: int = 200) -> str | None:
    # 1. 解析 IDS → 语法树
    consumed, tree = parse_ids_tree(ids, 0)
    if consumed == 0 or tree is None:
        print(f'ERROR: failed to parse IDS: {ids}', file=sys.stderr)
        return None
    if consumed < len(ids):
        print(f'Warning: trailing chars after IDS: {ids[consumed:]}', file=sys.stderr)

    # 2. 初始化 KAGE 引擎 (默认明朝体/Mincho)
    k = Kage(ignore_component_version=True)
    k.font = Sans() if use_gothic else Serif()

    # 3. 加载 KAGE 数据库
    with open('D:/KAGE_GLYPH/dump_newest_only.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    lines = csv.reader(lines, delimiter='|')
    for line in lines:
        if len(line) < 3:
            continue
        row = [s.strip() for s in line]
        if row[0].startswith('-') or not row[0]:
            continue
        k.components.push(row[0], row[2])

    # 4. 自底向上生成 KAGE 合成数据
    root_name = build_kage_composites(tree, k, [])
    if root_name is None:
        print('ERROR: KAGE composition failed', file=sys.stderr)
        return None

    # 5. 渲染
    canvas = svgwrite.Drawing(size=(str(size), str(size)))
    result = k.make_glyph_with_data(canvas, k.components.search(root_name))
    if result is None:
        return None
    return result.tostring()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python render_ids.py <IDS> [--gothic] [--size N]')
        sys.exit(1)

    ids = sys.argv[1]
    use_gothic = '--gothic' in sys.argv
    size = 200
    for i, arg in enumerate(sys.argv):
        if arg == '--size' and i + 1 < len(sys.argv):
            size = int(sys.argv[i + 1])

    svg = render_ids(ids, use_gothic, size)
    if svg:
        print(svg)
    else:
        print(f'ERROR: failed to render {ids}', file=sys.stderr)
        sys.exit(1)
