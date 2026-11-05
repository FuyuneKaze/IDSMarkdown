# -*- coding: utf-8 -*-
r"""把两份手工表合成 symbols.json（重写版）

用法: python scripts/build_symbols.py
源:
  web/public/data/component_table.txt   生僻部件: col1 字形 / col2 码位(作名称)
  web/public/data/ipa_table.txt         IPA: col1 符号 / col2 中文名(辅音/塞擦音多为空)
  cpp-desktop/ipa_typeit/ipa.typeit.orgfull.txt  英文表述 chars['name'] = { lower: '\uXXXX' }
输出: web/public/data/symbols.json
规则:
  · 名称: 表格第二列 > AFF_NAME(塞擦音等内置名) > typeit 英文名 > 用符号本身
  · insert: 含 ◌ 时去掉 ◌（显示保留），否则与 slogan 相同
"""
import io, json, re, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = r"D:\2026harucpp"
IPA = ROOT + r"\web\public\data\ipa_table.txt"
COMP = ROOT + r"\web\public\data\component_table.txt"
TYPEIT = ROOT + r"\cpp-desktop\ipa_typeit\ipa.typeit.orgfull.txt"
OUT = ROOT + r"\web\public\data\symbols.json"
DOT = chr(0x25CC)
TIE = chr(0x361)
RING = chr(0x325)


def aff(*parts):
    return TIE.join(parts)


# 表格里这些组合的第二列为空，这里给名字（改名字直接改这张表）
AFF_NAME = {
    aff("p", "f"): "清唇齿塞擦音",
    aff("b", "v"): "浊唇齿塞擦音",
    aff("t", "s"): "清齿龈塞擦音",
    aff("d", "z"): "浊齿龈塞擦音",
    aff("\u0288", "\u0282"): "清卷舌塞擦音",
    aff("\u0256", "\u0290"): "浊卷舌塞擦音",
    aff("t", "\u0255"): "清龈腭塞擦音",
    aff("d", "\u0291"): "浊龈腭塞擦音",
    aff("c", "\u00e7"): "清硬腭塞擦音",
    aff("\u025f", "\u029d"): "浊硬腭塞擦音",
    aff("k", "x"): "清软腭塞擦音",
    aff("g", "\u0263"): "浊软腭塞擦音",
    aff("q", "\u03c7"): "清小舌塞擦音",
    aff("\u0262", "\u0281"): "浊小舌塞擦音",
    aff("t", "\u0299" + RING): "清齿龈塞颤音",
    aff("d", "\u0299"): "浊齿龈塞颤音",
    aff("p", "s"): "清唇-齿龈塞擦音",
    aff("b", "z"): "浊唇-齿龈塞擦音",
    aff("k", "s"): "清软腭-齿龈塞擦音",
    aff("g", "z"): "浊软腭-齿龈塞擦音",
    aff("k", "p"): "清软腭-唇双塞音",
    aff("g", "b"): "浊软腭-唇双塞音",
    aff("t", "\u0283"): "清龈后塞擦音",
    aff("d", "\u0292"): "浊龈后塞擦音",
    aff("t", "\u026c"): "清齿龈边塞擦音",
    aff("d", "\u026e"): "浊齿龈边塞擦音",
}


def unesc(s):
    return re.sub(r"\\u([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)


# ---------- typeit 英文名 ----------
eng = {}
for m in re.finditer(r"chars\['([^']+)'\]\s*=\s*\{\s*lower:\s*'([^']*)'",
                     io.open(TYPEIT, encoding="utf-8", errors="replace").read()):
    eng.setdefault(unesc(m.group(2)), m.group(1))
print(f"typeit 英文名: {len(eng)} 条")

# ---------- 生僻部件 ----------
comp_items, seen = [], set()
for line in io.open(COMP, encoding="utf-8"):
    cols = line.rstrip("\n").split("\t")
    if len(cols) < 2:
        continue
    ch, cp = cols[0].strip(), cols[1].strip()
    if not ch or ch in seen:
        continue
    seen.add(ch)
    comp_items.append({"slogan": ch, "name": cp, "insert": ch})
print(f"生僻部件: {len(comp_items)} 条")

# ---------- IPA ----------
ipa_items, n_aff = [], 0
for line in io.open(IPA, encoding="utf-8"):
    cols = [c.strip() for c in line.rstrip("\n").split("\t")]
    if not cols or not cols[0]:
        continue
    sym = cols[0]
    if sym in seen:
        continue
    seen.add(sym)
    cn = cols[1] if len(cols) > 1 else ""
    name = cn or AFF_NAME.get(sym) or eng.get(sym) or sym
    if sym in AFF_NAME:
        n_aff += 1
    insert = sym.replace(DOT, "") if DOT in sym else sym
    ipa_items.append({"slogan": sym, "name": name, "insert": insert})
print(f"IPA: {len(ipa_items)} 条 (其中塞擦音/双塞音 {n_aff} 条, 含 {DOT} 的 "
      f"{sum(1 for i in ipa_items if DOT in i['slogan'])} 条)")

data = {"groups": [
    {"id": "ipa", "title": "IPA", "items": ipa_items},
    {"id": "component", "title": "难输入部件", "items": comp_items},
]}
io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
print(f"写出 {OUT} (共 {len(ipa_items) + len(comp_items)} 条)")

# 抽查
print("\n塞擦音名称:")
for it in ipa_items:
    if it["slogan"] in AFF_NAME:
        print(f"  {it['slogan']!r:14} {it['name']}")
