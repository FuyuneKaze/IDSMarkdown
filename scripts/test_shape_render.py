#!/usr/bin/env python3
"""
形状匹配 + KAGE 渲染验证
选择变体 → 合成 → 生成 HTML 直观对比
"""

import sys, os, math, json
from collections import defaultdict

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

DUMP_PATH = r'D:\KAGE_GLYPH\dump_newest_only.txt'
BUNDLE_PATH = r'D:\2026harucpp\scripts\kage-bundle.js'

SURROUND_OP_CODES = {0x2FF4,0x2FF5,0x2FF6,0x2FF7,0x2FF8,0x2FF9,0x2FFA,0x2FFC}

# ============================================================
# 1. 加载 & 变体索引 (从 test_shape_match.py)
# ============================================================

def extract_base(name):
    if not name.startswith('u'): return None
    end = 1
    while end < len(name) and name[end] in '0123456789abcdef':
        end += 1
    if end <= 1: return None
    return name[:end]

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
    return glyphs

def build_variant_index(glyphs):
    idx = defaultdict(list)
    for name in glyphs:
        base = extract_base(name)
        if base: idx[base].append(name)
    return idx

def region_variants(char_hex, variant_idx, region='g'):
    base = 'u' + char_hex
    all_vars = variant_idx.get(base, [])
    if not all_vars: return []
    def tier(name):
        suffix = name[len(base):]
        if not suffix: return 0
        if suffix.startswith('-' + region): return 1
        if suffix.startswith('-j'): return 2
        if suffix.startswith('-') and len(suffix) > 1 and suffix[1].isdigit(): return 3
        if suffix.startswith('-var-'): return 4
        return 6
    def exclude(name):
        suffix = name[len(base):]
        return suffix.startswith('-k') or suffix.startswith('-t') or suffix.startswith('-h')
    candidates = [n for n in all_vars if not exclude(n)]
    candidates.sort(key=tier)
    return candidates

# ============================================================
# 2. Bbox & 位置
# ============================================================

def compute_bbox(data, glyphs, visited=None):
    if visited is None: visited = set()
    if not data: return None
    mx, my, Mx, My = 200, 200, 0, 0
    for stroke in data.split('$'):
        stroke = stroke.strip()
        if not stroke: continue
        parts = stroke.split(':')
        try: kind = int(parts[0])
        except: continue
        if kind == 99 and len(parts) >= 8:
            x1,y1,x2,y2 = int(parts[3]),int(parts[4]),int(parts[5]),int(parts[6])
            ref = parts[7].split('@')[0]
            if ref not in visited and ref in glyphs:
                visited.add(ref)
                rb = compute_bbox(glyphs[ref], glyphs, visited)
                if rb:
                    mx = min(mx, x1+(x2-x1)*rb[0]/200)
                    my = min(my, y1+(y2-y1)*rb[1]/200)
                    Mx = max(Mx, x1+(x2-x1)*rb[2]/200)
                    My = max(My, y1+(y2-y1)*rb[3]/200)
        else:
            coords = [int(p) for p in parts[3:] if p.lstrip('-').isdigit()]
            for i in range(0, len(coords)-1, 2):
                mx, my = min(mx, coords[i]), min(my, coords[i+1])
                Mx, My = max(Mx, coords[i]), max(My, coords[i+1])
    return (mx, my, Mx, My) if mx <= Mx else None

def bbox_of(name, glyphs, cache):
    if name in cache: return cache[name]
    data = glyphs.get(name, '')
    bb = compute_bbox(data, glyphs) if data else None
    cache[name] = bb
    return bb

def extract_position_code(sfx):
    if not sfx: return ''
    var_idx = sfx.find('-var-')
    core = sfx[:var_idx] if var_idx > 0 else sfx
    if len(core) >= 2 and core[-2:].isdigit(): return core[-2:]
    if len(core) >= 1 and core[-1].isdigit(): return core[-1]
    if len(core) >= 1 and core[-1].isalpha(): return core[-1]
    return core

def position_suffix(position, op_cp):
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
    if op_cp == 0x2FF2: return ['01','01','02'][min(position,2)]
    if op_cp == 0x2FF3: return ['03','03','04'][min(position,2)]
    return '01'

# ============================================================
# 3. 空间分配 & 形状评分
# ============================================================

def allocate_slots(op_cp, child_bboxes):
    n = len(child_bboxes)
    if op_cp == 0x2FF0:
        widths = [bb[2]-bb[0] if bb else 50 for bb in child_bboxes]
        total_w = sum(widths) or 1
        slots, cx = [], 3
        for i in range(n):
            w = max(30, int(194 * widths[i] / total_w))
            if i == n-1: w = 197 - cx
            slots.append((cx, 3, cx+w, 197)); cx += w
        return slots
    elif op_cp == 0x2FF1:
        heights = [bb[3]-bb[1] if bb else 50 for bb in child_bboxes]
        total_h = sum(heights) or 1
        slots, cy = [], 3
        for i in range(n):
            h = max(25, int(194 * heights[i] / total_h))
            if i == n-1: h = 197 - cy
            slots.append((3, cy, 197, cy+h)); cy += h
        return slots
    elif op_cp in SURROUND_OP_CODES:
        outer_bb = child_bboxes[0]
        if op_cp == 0x2FF8: inner = (85, 100, 197, 197)
        elif op_cp == 0x2FF9: inner = (3, 40, 150, 197)
        elif op_cp == 0x2FFA: inner = (55, 3, 197, 170)
        elif op_cp == 0x2FF5:
            if outer_bb: inner = (outer_bb[0]+8, max(outer_bb[1]+12,20), outer_bb[2]-8, 197)
            else: inner = (20, 30, 180, 197)
        elif op_cp == 0x2FF6: inner = (20, 3, 180, 100)
        elif op_cp == 0x2FF7:
            if outer_bb: inner = (outer_bb[0]+28, outer_bb[1]+8, min(outer_bb[2],180), outer_bb[3]-8)
            else: inner = (50, 15, 180, 185)
        elif op_cp == 0x2FFC: inner = (3, 15, 120, 185)
        elif op_cp == 0x2FF4:
            if outer_bb:
                cx,cy = (outer_bb[0]+outer_bb[2])/2, (outer_bb[1]+outer_bb[3])/2
                iw,ih = (outer_bb[2]-outer_bb[0])*0.55, (outer_bb[3]-outer_bb[1])*0.55
                inner = (cx-iw/2, cy-ih/2, cx+iw/2, cy+ih/2)
            else: inner = (40, 35, 160, 165)
        else: inner = (30, 30, 170, 170)
        def clamp(r):
            x1,y1,x2,y2 = r
            return (max(3,min(x1,197)), max(3,min(y1,197)),
                    max(x1+10,min(x2,197)), max(y1+10,min(y2,197)))
        return [(0,0,200,200), clamp(inner)]
    else:
        return [(0,0,200,200)] * n

def shape_match_score(variant_name, slot, glyphs, bbox_cache):
    bb = bbox_of(variant_name, glyphs, bbox_cache)
    if not bb: return 0, ''
    vw = (bb[2]-bb[0]) or 1; vh = (bb[3]-bb[1]) or 1
    sw = slot[2]-slot[0]; sh = slot[3]-slot[1]
    area_ratio = min(vw*vh, sw*sh) / max(vw*vh, sw*sh)
    aspect_ratio = min(vw/vh, sw/sh) / max(vw/vh, sw/sh) if sw and sh else 0
    return area_ratio*0.3 + aspect_ratio*0.7, f'{vw}×{vh}→{sw}×{sh}'

# ============================================================
# 4. IDS 解析 + 变体选择 + 复合构建
# ============================================================

def parse_ids(ids, pos=0):
    if pos >= len(ids): return None, pos
    ch = ids[pos]
    if not ((0x2FF0 <= ord(ch) <= 0x2FFF) or ord(ch) == 0x31EF):
        return ('leaf', ch), pos + 1
    op = ch; pos += 1
    arity = 3 if ch in '⿲⿳' else 2
    children = []
    for _ in range(arity):
        if pos >= len(ids): break
        c, pos = parse_ids(ids, pos)
        if c: children.append(c)
    return ('node', op, children), pos

def process_and_build(ids, region, glyphs, variant_idx, counter):
    """形状匹配选变体 + 构建复合 KAGE 数据。返回 (root_name, composite_data, all_deps)"""
    root, end = parse_ids(ids)
    if root is None or end != len(ids): return None, None, []
    bbox_cache = {}
    composites = {}

    def process(node, parent_op=None, position=0):
        kind = node[0]
        if kind == 'leaf':
            ch = node[1]
            return {'char': ch, 'hex': f'{ord(ch):04x}',
                    'candidates': region_variants(f'{ord(ch):04x}', variant_idx, region)}

        op = node[1]; op_cp = ord(op)
        children = node[2]

        # 递归子节点
        child_results = [process(c, op, i) for i, c in enumerate(children)]

        # 默认变体 (取地区前缀或基础形)
        default_names = []
        for res in child_results:
            cands = res.get('candidates', [])
            name = None
            for c in cands:
                base_c = extract_base(c)
                sfx = c[len(base_c):] if base_c else c
                if sfx.startswith('-' + region) or sfx.startswith('-j') or not sfx:
                    name = c; break
            if not name and cands: name = cands[-1]
            default_names.append(name or '?')

        # 计算 bbox + 分配 slot
        child_bboxes = [bbox_of(n, glyphs, bbox_cache) for n in default_names]
        slots = allocate_slots(op_cp, child_bboxes)

        # 位置过滤 + 形状匹配
        selected_names = []
        for i, (res, slot) in enumerate(zip(child_results, slots)):
            cands = res.get('candidates', [])
            exp_sfx = position_suffix(i, op_cp)

            if op_cp in SURROUND_OP_CODES and i == 0:
                pos_filtered = cands
            else:
                pos_filtered = [c for c in cands
                    if extract_position_code(c[len(extract_base(c) or ''):]) in ('', exp_sfx)]
                if not pos_filtered: pos_filtered = cands

            best_name = None; best_score = -1
            for c in pos_filtered:
                score, _ = shape_match_score(c, slot, glyphs, bbox_cache)
                if score > best_score: best_score = score; best_name = c
            selected_names.append(best_name or default_names[i])

        # ---- 构建 KAGE 复合数据 ----
        counter[0] += 1
        comp_name = f'_c{counter[0]}'
        strokes = []
        for i, (sn, slot) in enumerate(zip(selected_names, slots)):
            x1,y1,x2,y2 = slot
            strokes.append(f'99:0:0:{x1}:{y1}:{x2}:{y2}:{sn}:0:0:0')

        comp_data = '$'.join(strokes)
        composites[comp_name] = comp_data
        glyphs[comp_name] = comp_data  # 加入 glyphs 供递归展开

        # 收集叶子依赖
        all_deps = list(selected_names)
        # 递归收集子节点的 deps
        for cr in child_results:
            if 'comp_name' in cr:
                all_deps.append(cr['comp_name'])

        result = {
            'char': op, 'op_cp': op_cp,
            'comp_name': comp_name, 'comp_data': comp_data,
            'selected_names': selected_names,
            'slots': slots,
            'children': child_results,
        }
        return result

    result = process(root)
    if not result or 'comp_name' not in result:
        return None, None, []

    # 收集所有依赖的字形数据
    def collect_deps(comp_name, collected):
        if comp_name in collected: return
        collected.add(comp_name)
        data = composites.get(comp_name) or glyphs.get(comp_name, '')
        for stroke in data.split('$'):
            if stroke.startswith('99:'):
                parts = stroke.split(':')
                if len(parts) >= 8:
                    ref = parts[7]
                    # 剥离 @N
                    base = ref.split('@')[0]
                    if base in glyphs:
                        collect_deps(base, collected)
                    # 也尝试原始名称
                    if ref in glyphs:
                        collect_deps(ref, collected)

    all_deps = set()
    collect_deps(result['comp_name'], all_deps)

    return result['comp_name'], result['comp_data'], all_deps, result


# ============================================================
# 5. HTML 生成
# ============================================================

OP_NAMES = {
    0x2FF0:'⿰',0x2FF1:'⿱',0x2FF2:'⿲',0x2FF3:'⿳',
    0x2FF4:'⿴',0x2FF5:'⿵',0x2FF6:'⿶',0x2FF7:'⿷',
    0x2FF8:'⿸',0x2FF9:'⿹',0x2FFA:'⿺',0x2FFB:'⿻',0x31EF:'㇯'
}

def generate_html(ids, root_name, comp_data, all_glyphs, bundle_js, result_tree):
    # JS 加载代码
    js_loads = []
    for name, data in all_glyphs.items():
        esc = data.replace('\\', '\\\\').replace("'", "\\'")
        js_loads.append(f"loadGlyph('{name}', '{esc}');")
    js_load_str = '\n    '.join(js_loads)

    # 生成分析树
    def tree_str(node, indent=0):
        pref = '  ' * indent
        if 'selected_names' in node:
            op = OP_NAMES.get(node.get('op_cp', 0), node.get('char', '?'))
            lines = [f"{pref}{op} [{node.get('comp_name', '?')}]"]
            for i, (sn, slot) in enumerate(zip(node['selected_names'], node['slots'])):
                lines.append(f"{pref}  #{i}: {sn} @ slot({slot[0]},{slot[1]},{slot[2]},{slot[3]})")
            for c in node.get('children', []):
                lines.append(tree_str(c, indent + 1))
            return '\n'.join(lines)
        elif 'char' in node:
            return f"{pref}{node['char']}"
        return pref + '?'

    tree = tree_str(result_tree)

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Shape Match - {ids}</title>
<style>
  body {{ font-family: sans-serif; padding: 20px; background: #1a1a2e; color: #eee; }}
  h2 {{ color: #e94560; }}
  .grid {{ display: flex; gap: 24px; flex-wrap: wrap; align-items: start; }}
  .card {{ background: #f5f5f5; border-radius: 8px; padding: 16px; text-align: center; min-width: 200px; }}
  .card svg {{ background: white; border-radius: 4px; }}
  .label {{ font-size: 13px; color: #555; margin-top: 8px; font-weight: bold; }}
  pre {{ background: #0f3460; padding: 16px; border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5; }}
</style></head><body>
<h2>形状匹配 - {ids}</h2>
<h3>选中的变体</h3>
<pre>{tree}</pre>
<h3>渲染结果</h3>
<div class="grid">
  <div class="card">
    <div id="composite"></div>
    <div class="label">合成 ({root_name})</div>
  </div>
</div>
<script>
// KAGE bundle
{bundle_js}
// 装载字形
{js_load_str}
// 渲染
try {{
  var svg = renderGlyph('{root_name}', false);
  document.getElementById('composite').innerHTML = svg;
}} catch(e) {{
  document.getElementById('composite').innerHTML = '<p style="color:red">Error: ' + e.message + '</p>';
}}
</script>
</body></html>'''


# ============================================================
# Main
# ============================================================

def main():
    print("加载数据...")
    glyphs = load_dump(DUMP_PATH)
    variant_idx = build_variant_index(glyphs)
    print(f"  {len(glyphs)} glyphs, {len(variant_idx)} chars")

    with open(BUNDLE_PATH, 'r', encoding='utf-8') as f:
        bundle_js = f.read()
    print(f"  KAGE bundle: {len(bundle_js)} bytes")

    tests = [
        "⿱𡗬禾",   # 秦
        "⿸麻鬼",   # 魔
        "⿱山鬼",   # 嵬
        "⿸麻木",   # 麿
        "⿸麻么",   # 麽
    ]

    for ids in tests:
        counter = [0]
        print(f"\n{'='*60}")
        print(f"  {ids}")
        print(f"{'='*60}")

        root_name, comp_data, deps, result_tree = process_and_build(
            ids, 'g', glyphs, variant_idx, counter)

        if root_name is None:
            print(f"  构建失败!")
            continue

        # 收集所有需要的字形
        all_glyphs = {}
        for name in deps:
            if name in glyphs:
                all_glyphs[name] = glyphs[name]
            elif name in glyphs:  # already in composites
                pass
        all_glyphs[root_name] = comp_data

        # 展开 type-99 依赖
        queue = list(deps)
        expanded = set()
        while queue:
            name = queue.pop()
            if name in expanded: continue
            expanded.add(name)
            data = all_glyphs.get(name, '')
            for stroke in data.split('$'):
                if stroke.startswith('99:'):
                    parts = stroke.split(':')
                    if len(parts) >= 8:
                        ref = parts[7]
                        base = ref.split('@')[0]
                        if base not in all_glyphs and base in glyphs:
                            all_glyphs[base] = glyphs[base]
                            queue.append(base)

        print(f"  root: {root_name}, deps: {len(all_glyphs)}")

        # 生成 HTML
        html = generate_html(ids, root_name, comp_data, all_glyphs, bundle_js, result_tree)
        safe = ids
        for c in '⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻':
            safe = safe.replace(c, '_')
        out_path = f'D:/2026harucpp/scripts/render_shape_{safe}.html'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  输出: {out_path}")

        # 打印选择
        def print_sel(node, indent=0):
            pref = '  ' * indent
            if 'selected_names' in node:
                op = OP_NAMES.get(node.get('op_cp', 0), '?')
                print(f"{pref}{op}:")
                for sn in node['selected_names']:
                    print(f"{pref}  → {sn}")
                for c in node.get('children', []):
                    print_sel(c, indent + 1)
        print_sel(result_tree)

    print(f"\n完成! 打开 HTML 文件查看渲染。")


if __name__ == '__main__':
    main()
