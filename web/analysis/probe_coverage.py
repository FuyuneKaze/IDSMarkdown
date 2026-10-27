# -*- coding: utf-8 -*-
"""按「不同的字」统计各扩展语法的覆盖面 (不是行数), 并列出 ⿱[..] 那个异类"""
import io, os, re, sys, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PUB = r"D:\2026harucpp\web\public"
files = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]

FEATS = [
    ("§6.2 ⿻[a:b] 跨越速成", re.compile(r"⿻\[-?\d*:-?\d*\]")),
    ("§6.3/6.4 ⿻[矩阵]", re.compile(r"⿻\[[^\]]*[A-Za-z_,|][^\]]*\]")),
    ("§6.6 ⿴/⿵/⿶/⿷/⿼[n] 包围索引", re.compile(r"[⿴⿵⿶⿷⿼]\[\d+\]")),
    ("§6.6 ⿱[n] 异类", re.compile(r"⿱\[\d+\]")),
    ("§5 #(...) 笔画链", re.compile(r"#\(")),
    ("§7 {...} 唯一化", re.compile(r"\{")),
    (". 部件分隔", re.compile(r"\.")),
    ("⿼ 右包围", re.compile("⿼")),
    ("⿾ 镜像", re.compile("⿾")),
    ("⿿ 旋转", re.compile("⿿")),
    ("㇯ 减法", re.compile("㇯")),
    ("(tag) 变体标识", re.compile(r"\([^)]*\)")),
]

chars = {k: set() for k, _ in FEATS}
rows = collections.Counter()
weird = []

for f in files:
    p = os.path.join(PUB, f)
    if not os.path.exists(p):
        continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        head, _, body = line.partition("\t")
        head = head.strip()
        rows[f] += 1
        for k, pat in FEATS:
            if pat.search(body):
                chars[k].add(head)
        if re.search(r"⿱\[\d+\]", body) and len(weird) < 6:
            weird.append(line[:110])

print(f"行数合计 {sum(rows.values()):,}  (各 lv 文件可能重复同一字)")
print()
print(f"{'扩展语法':34s} {'不同字数':>8s}")
for k, _ in FEATS:
    print(f"{k:34s} {len(chars[k]):8d}")
print()
print("⿱[n] 的原始行:")
for w in weird:
    print("   ", w)
print()
ex = sorted(chars["§6.6 ⿴/⿵/⿶/⿷/⿼[n] 包围索引"])
print("用到包围索引的全部字:", "".join(ex), f"({len(ex)} 个)")
