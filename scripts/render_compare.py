#!/usr/bin/env python3
"""生成形状匹配 vs Ground Truth 对比 HTML"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')

DUMP_PATH = r'D:\KAGE_GLYPH\dump_newest_only.txt'
BUNDLE_PATH = r'D:\2026harucpp\scripts\kage-bundle.js'

# ---- 加载 ----
glyphs = {}
with open(DUMP_PATH, 'r', encoding='utf-8') as f:
    f.readline(); f.readline()
    for line in f:
        if line[0] != ' ': continue
        p = line.strip().split(' | ')
        if len(p) >= 3:
            d = p[2].strip()
            if d: glyphs[p[0].strip()] = d

with open(BUNDLE_PATH, 'r', encoding='utf-8') as f:
    bundle_js = f.read()

# ---- 定义对比组 ----
# (标签, IDS, 形状匹配选变体, slots, [ground_truth_name])
# 形状匹配结果来自 test_shape_render.py
comparisons = [
    {
        'label': '秦 (⿱𡗬禾)',
        'ids': '⿱𡗬禾',
        'shape': {
            'name': '_c_shape1',
            'data': '99:0:0:3:3:197:101:u215ec:0:0:0$99:0:0:3:101:197:197:u79be-04-var-001:0:0:0',
            'deps': ['u215ec', 'u79be-04-var-001'],
        },
        'truth': {'name': 'u79e6-g'},
    },
    {
        'label': '魔 (⿸麻鬼)',
        'ids': '⿸麻鬼',
        'shape': {
            'name': '_c_shape2',
            'data': '99:0:0:0:0:200:200:u9ebb-g:0:0:0$99:0:0:85:100:197:197:u9b3c-var-004:0:0:0',
            'deps': ['u9ebb-g', 'u9b3c-var-004'],
        },
        'truth': {'name': 'u9b54-g'},
    },
    {
        'label': '嵬 (⿱山鬼)',
        'ids': '⿱山鬼',
        'shape': {
            'name': '_c_shape3',
            'data': '99:0:0:3:3:197:92:u5c71-g03:0:0:0$99:0:0:3:92:197:197:u9b3c-var-004:0:0:0',
            'deps': ['u5c71-g03', 'u9b3c-var-004'],
        },
        'truth': {'name': 'u5d6c-02-var-002'},
    },
    {
        'label': '麿 (⿸麻木)',
        'ids': '⿸麻木',
        'shape': {
            'name': '_c_shape4',
            'data': '99:0:0:0:0:200:200:u9ebb-g:0:0:0$99:0:0:85:100:197:197:u6728:0:0:0',
            'deps': ['u9ebb-g', 'u6728'],
        },
        'truth': {'name': 'u9ebf-g'},
    },
    {
        'label': '麽 (⿸麻么)',
        'ids': '⿸麻么',
        'shape': {
            'name': '_c_shape5',
            'data': '99:0:0:0:0:200:200:u9ebb-g:0:0:0$99:0:0:85:100:197:197:u4e48:0:0:0',
            'deps': ['u9ebb-g', 'u4e48'],
        },
        'truth': {'name': 'u9ebd-g'},
    },
]

# ---- 收集所有需要的 glyph 数据 ----
def collect(name, collected, depth=0):
    if name in collected or depth > 10: return
    data = glyphs.get(name, '')
    if not data: return
    collected[name] = data
    for stroke in data.split('$'):
        if stroke.strip().startswith('99:'):
            parts = stroke.split(':')
            if len(parts) >= 8:
                ref = parts[7].split('@')[0]
                if ref in glyphs:
                    collect(ref, collected, depth + 1)

all_collected = {}
for comp in comparisons:
    # shape deps
    cn = comp['shape']['name']
    all_collected[cn] = comp['shape']['data']
    for dep in comp['shape']['deps']:
        collect(dep, all_collected)
    # truth deps
    tn = comp['truth']['name']
    collect(tn, all_collected)

print(f"Collected {len(all_collected)} glyphs total")

# ---- 生成 JS load ----
js_lines = []
for name, data in all_collected.items():
    esc = data.replace('\\', '\\\\').replace("'", "\\'")
    js_lines.append(f"loadGlyph('{name}', '{esc}');")
js_load_str = '\n    '.join(js_lines)

# ---- 生成 HTML cards ----
cards_html = ''
for comp in comparisons:
    sn = comp['shape']['name']
    tn = comp['truth']['name']
    cards_html += f'''
  <div class="pair">
    <h3>{comp['label']}</h3>
    <div class="side">
      <div class="card">
        <div id="shape_{sn}"></div>
        <div class="label">形状匹配 ({sn})</div>
      </div>
      <div class="card">
        <div id="truth_{tn}"></div>
        <div class="label">Ground Truth ({tn})</div>
      </div>
    </div>
    <div class="info">IDS: {comp['ids']} | shape data: {comp['shape']['data'][:80]}...</div>
  </div>'''

# ---- 生成渲染调用 ----
render_calls = ''
for comp in comparisons:
    sn = comp['shape']['name']
    tn = comp['truth']['name']
    render_calls += f'''
  document.getElementById('shape_{sn}').innerHTML = renderGlyph('{sn}', false);
  document.getElementById('truth_{tn}').innerHTML = renderGlyph('{tn}', false);'''

html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>形状匹配 vs Ground Truth 对比</title>
<style>
  body {{ font-family: sans-serif; padding: 24px; background: #1a1a2e; color: #eee; }}
  h2 {{ color: #e94560; margin-bottom: 8px; }}
  .pair {{ margin-bottom: 32px; border-bottom: 1px solid #333; padding-bottom: 20px; }}
  .side {{ display: flex; gap: 24px; }}
  .card {{ background: #f5f5f5; border-radius: 8px; padding: 16px; text-align: center; }}
  .card svg {{ background: white; border-radius: 4px; }}
  .label {{ font-size: 12px; color: #555; margin-top: 8px; font-weight: bold; }}
  .info {{ font-size: 11px; color: #888; margin-top: 8px; font-family: monospace; }}
</style></head><body>
<h2>形状匹配 vs Ground Truth 对比</h2>
<p style="color:#aaa;margin-bottom:24px">左=形状匹配算法 | 右=Dump实际 (Ch GT)</p>
{cards_html}
<script>
{bundle_js}
{js_load_str}
{render_calls}
</script>
</body></html>'''

out = r'D:\2026harucpp\scripts\render_compare.html'
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done: {out}")
