#!/usr/bin/env python3
"""盘点项目中 isIdsChar() 的码位覆盖范围"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 当前 isIdsCharCp() 覆盖的区间
COVERED = [
    (0x2E80, 0x2EF3),   # CJK Radicals
    (0x2F00, 0x2FD5),   # Kangxi Radicals
    (0x31C0, 0x31E3),   # CJK Strokes
    (0x2FF0, 0x2FFF),   # IDS Operators
    (0x4E00, 0x9FFF),   # CJK Unified
    (0x3400, 0x4DBF),   # CJK Ext A
    (0xF900, 0xFAFF),   # CJK Compat
    (0x20000, 0x3347F), # CJK Ext area (过宽)
]

def is_covered(lo, hi):
    for clo, chi in COVERED:
        if lo >= clo and hi <= chi:
            return True
    return False

# 关键 Unicode 区块
BLOCKS = [
    # 已覆盖
    ("CJK Radicals Supplement",         0x2E80, 0x2EFF),
    ("Kangxi Radicals",                 0x2F00, 0x2FD5),
    ("IDS Operators (17个+1个)",         0x2FF0, 0x2FFF),
    ("CJK Strokes",                     0x31C0, 0x31E3),
    ("CJK Extension A",                 0x3400, 0x4DBF),
    ("CJK Unified Ideographs",          0x4E00, 0x9FFF),
    ("CJK Compatibility Ideographs",    0xF900, 0xFAFF),
    ("CJK Ext B~H (范围过宽至0x3347F)",  0x20000, 0x3347F),
    # 未覆盖 - 日文
    ("Hiragana 平假名",                  0x3040, 0x309F),
    ("Katakana 片假名",                  0x30A0, 0x30FF),
    ("Katakana Phonetic Ext",           0x31F0, 0x31FF),
    # 未覆盖 - 韩文
    ("Hangul Jamo",                     0x1100, 0x11FF),
    ("Hangul Jamo Ext-A",               0xA960, 0xA97F),
    ("Hangul Jamo Ext-B",               0xD7B0, 0xD7FF),
    ("Hangul Syllables",                0xAC00, 0xD7AF),
    # 未覆盖 - 西夏文
    ("Tangut 西夏文",                     0x17000, 0x187F7),
    ("Tangut Components 西夏部件",        0x18800, 0x18AFF),
    ("Tangut Supplement",               0x18D00, 0x18D8F),
    # 未覆盖 - 其他重要区块
    ("Yi Syllables 彝文",                0xA000, 0xA48F),
    ("Yi Radicals",                     0xA490, 0xA4CF),
    ("Lisu",                            0xA4D0, 0xA4FF),
    ("Khitan Small Script 契丹小字",     0x18B00, 0x18CFF),
    ("Nushu 女书",                       0x1B170, 0x1B2FF),
    ("Kana Supplement",                 0x1B000, 0x1B0FF),
    ("Kana Extended-A",                 0x1B100, 0x1B12F),
    ("Small Kana Ext",                  0x1B130, 0x1B16F),
    # CJK 扩展区精确范围 (已在0x20000~0x3347F内)
    ("  Ext B",                         0x20000, 0x2A6DF),
    ("  Ext C",                         0x2A700, 0x2B739),
    ("  Ext D",                         0x2B740, 0x2B81F),
    ("  Ext E",                         0x2B820, 0x2CEA1),
    ("  Ext F",                         0x2CEB0, 0x2EBE0),
    ("  Ext G",                         0x30000, 0x3134F),
    ("  Ext H",                         0x31350, 0x323AF),
    ("  Compat Sup",                    0x2F800, 0x2FA1F),
    # 古文字
    ("Egyptian Hieroglyphs 圣书体",      0x13000, 0x1342F),
    ("Egyptian Hieroglyph Format Controls", 0x13430, 0x1345F),
    ("Anatolian Hieroglyphs",           0x14400, 0x1467F),
    ("Meroitic Cursive",                0x109A0, 0x109FF),
    ("Meroitic Hieroglyphs",            0x10980, 0x1099F),
    ("Cuneiform",                       0x12000, 0x123FF),
    ("Cuneiform Numbers",               0x12400, 0x1247F),
]

print("=" * 70)
print("isIdsChar() 码位覆盖盘点")
print("=" * 70)
print()

covered_blocks = [b for b in BLOCKS if is_covered(b[1], b[2])]
uncovered_blocks = [b for b in BLOCKS if not is_covered(b[1], b[2])]

print(f"已覆盖 {len(covered_blocks)} 个区块:")
for name, lo, hi in covered_blocks:
    print(f"  [Y] U+{lo:05X}~U+{hi:05X}  {name}")

print()
print(f"未覆盖 {len(uncovered_blocks)} 个区块:")
for name, lo, hi in uncovered_blocks:
    chars = hi - lo + 1
    print(f"  [N] U+{lo:05X}~U+{hi:05X}  {name}  ({chars} chars)")
