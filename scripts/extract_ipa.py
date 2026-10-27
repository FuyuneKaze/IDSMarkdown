#!/usr/bin/env python3
"""
从 ipa_typeit/ipa.typeit.orgfull.txt 提取 IPA 键位映射，
生成干净的 JSON 文件放到 data/ 目录。

支持两种 lower 格式:
  1. 纯 Unicode 转义: 'æ' 或 'ɑ̃'
  2. 混合字面字符+转义: 't͡ʃ' (字面 t + 转义序列)
"""
import re
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(PROJECT, 'ipa_typeit', 'ipa.typeit.orgfull.txt')
DST = os.path.join(PROJECT, 'data', 'ipa_keymap.json')

with open(SRC, 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 1. 提取 chars
# ============================================================

def parse_lower_string(raw):
    """
    解析 lower 字符串值, 返回码点列表.
    raw 示例: 't͡ʃ' 或 'ɑ̃' 或 'æ'
    """
    cps = []
    i = 0
    while i < len(raw):
        if raw[i] == '\\' and i + 1 < len(raw) and raw[i+1] == 'u':
            # Unicode 转义: \uXXXX
            hex_part = raw[i+2:i+6]
            cps.append(int(hex_part, 16))
            i += 6
        elif raw[i] == '\\' and i + 1 < len(raw):
            # 其他转义 (如 \' \\)
            cps.append(ord(raw[i+1]))
            i += 2
        else:
            cps.append(ord(raw[i]))
            i += 1
    return cps


# 匹配 chars['name'] = { lower: 'VALUE'  ... }
# VALUE 可包含: 字面字符、\uXXXX unicode转义、\' \\ 等JS转义
char_re = re.compile(
    r"""chars\['(.+?)'\]\s*=\s*\{\s*lower:\s*'((?:[^'\\]|\\(?:u[0-9A-Fa-f]{4}|.))*)'""")
chars = {}
for m in char_re.finditer(content):
    name = m.group(1)
    raw_lower = m.group(2)
    cps = parse_lower_string(raw_lower)
    chars[name] = cps

print(f'chars: {len(chars)}')

# ============================================================
# 2. 提取 keys
# ============================================================

key_re = re.compile(
    r"""keys\['(.+?)'\]\s*=\s*\[(.+)\]\s*;""")
keys = {}
for m in key_re.finditer(content):
    key_spec_raw = m.group(1)
    array_body = m.group(2)

    # 处理链式赋值: keys['A'] = keys['B'] = [...]
    if "'] = keys['" in key_spec_raw:
        all_key_specs = key_spec_raw.split("'] = keys['")
    else:
        all_key_specs = [key_spec_raw]

    # 从 array_body 提取 chars['name'] 引用
    char_names = []
    for nm in re.findall(r"chars\['(.+?)'\]", array_body):
        if nm in chars:
            char_names.append(nm)

    if not char_names:
        continue

    for ks in all_key_specs:
        shift = False
        base_key = ks
        if ks.startswith('Mod+Shift+'):
            shift = True
            base_key = ks[10:]
        elif ks.startswith('Mod+'):
            base_key = ks[4:]
        else:
            continue

        key_entry = {'base': base_key, 'shift': shift, 'chars': char_names}
        if ks not in keys:
            keys[ks] = key_entry

print(f'keys: {len(keys)}')

# ============================================================
# 3. 输出 JSON
# ============================================================

# 将码点列表转为十六进制字符串以便 JSON 可读 (兼容 Qt 的 QChar(uint) 构造)
output = {
    'chars': chars,
    'keys': list(keys.values())
}

with open(DST, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'-> {DST}')

# 检查多码点字符
multi = [(n, cps) for n, cps in chars.items() if len(cps) > 1]
print(f'  multi-codepoint chars: {len(multi)}')
for name, cps in multi:
    chars_str = ''.join(chr(cp) for cp in cps if cp < 0x110000)
    # 避免控制台编码错误, 用 repr
    pass  # 跳过打印, 避免 GBK 问题

# 验证 T 键候选
for entry in output['keys']:
    if entry['base'] == 'T':
        print(f'  Alt+T candidates: {len(entry["chars"])}')
        for cn in entry['chars']:
            cps = chars.get(cn, [])
            print(f'    {cn}: {cps}')
        break
