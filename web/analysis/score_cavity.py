# -*- coding: utf-8 -*-
"""
空腔选择的客观评分器

【为什么能客观】
  真字形库里每个字都有设计者画好的 KAGE 数据。字 C 的 IDS 是 `⿴AB` 时,
  C 的字形里就有一条指向 B 变体的 99 引用, **那条 99 的矩形就是设计者选的腔**。
  于是不需要猜"哪个腔是对的" —— 拿设计者的矩形去对候选列表即可。

【输出什么】
  ① 三种"默认该选哪个"的命中率: 文档语义 #0 / 现在语义 最大面积 / 最靠近中心
  ② 只看"真有得选"的字 (候选 >1 个) 的命中率 —— 这才是真正的判据
  ③ 显式写了 [n] 的字: 命中序号是否正好等于 n  ← 这一条能钉死排序规则

用法:
    python -u web/analysis/score_cavity.py [样本上限]
    python -u web/analysis/score_cavity.py --explicit 100    # 只看带 [n] 的字
"""

import sys, io, os, re, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")

import preview                                   # 建索引接管 get_data (半小时→秒级)
import glyph_extend                              # noqa: E402
import cavity                                    # noqa: E402

PUB = r"D:\2026harucpp\web\public"
LV = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"]
SURROUND = set("⿴⿵⿶⿷⿸⿹⿺⿼⿽")
OPCH = "".join(SURROUND)

_buf = io.StringIO()


def quiet(fn, *a, **kw):
    import contextlib
    with contextlib.redirect_stdout(_buf):
        return fn(*a, **kw)


# ---------------------------------------------------------------- 解析
def strip_notation(body):
    """去掉 . 、#(...)、{...}、(...), 只留纯 IDS (与 web 的 normalize 同义)"""
    body = body.split("\t")[0]
    body = re.sub(r"#\([^)]*\)|\{[^}]*\}|\([^)]*\)", "", body)
    return body.replace(".", "").strip()


def subtree_end(s, i):
    """一个子树(含算符与可选 [修饰符]) 的结束位置"""
    if i >= len(s):
        return i
    cp = ord(s[i])
    if 0x2FF0 <= cp <= 0x2FFF or cp == 0x31EF:
        i += 1
        if i < len(s) and s[i] == "[":            # 跳过 [] 修饰符
            k = s.find("]", i)
            i = (k + 1) if k >= 0 else len(s)
        arity = 3 if cp in (0x2FF2, 0x2FF3) else (1 if cp in (0x2FFE, 0x2FFF) else 2)
        for _ in range(arity):
            i = subtree_end(s, i)
        return i
    return i + 1


def split_children(s, i, n):
    """从 s[i] 起取 n 个子节点"""
    out = []
    for _ in range(n):
        if i >= len(s):
            return out, i
        j = subtree_end(s, i)
        out.append(s[i:j])
        i = j
    return out, i


def first_char(node):
    """子节点里的第一个汉字 (跳过算符、修饰符、位置标记)"""
    for ch in node:
        cp = ord(ch)
        if 0x2FF0 <= cp <= 0x2FFF or cp == 0x31EF:
            continue
        if ch in ".[]0123456789:-,":
            continue
        return ch
    return ""


# ---------------------------------------------------------------- 字形侧
def refs_of(char):
    """字 C 的字形里指向别处的 99 引用 [(名字, 矩形)] —— 需要时下钻 -j 外壳"""
    name = "u%x" % ord(char)
    for _ in range(3):
        data = quiet(glyph_extend.get_data, name)
        if not data:
            return []
        inner = []
        for seg in data.split("$"):
            p = seg.strip().split(":")
            if p[0] == "99" and len(p) >= 8:
                inner.append((p[7].split("@")[0], tuple(float(v) for v in p[3:7])))
        if not inner:
            return []
        if len(inner) == 1 and inner[0][0] == name + "-j":
            name = inner[0][0]                    # 外壳, 继续往下钻
            continue
        return inner
    return []


def order_of(op, container_name, inner_rect):
    """设计者的内部件矩形落在候选列表的第几个

    返回 (序号, 候选数, (最大面积是第几个, 最靠中心是第几个))
    """
    strokes = quiet(glyph_extend.return_bone, container_name)
    strokes = [s for s in strokes.split("$") if s]
    cands = quiet(cavity.cavity_list, strokes, op)
    if not cands:
        return None, 0, (0, 0)

    ix = (inner_rect[0] + inner_rect[2]) / 2.0
    iy = (inner_rect[1] + inner_rect[3]) / 2.0
    best, best_ov, inside_idx = None, -1.0, None
    for k, f in enumerate(cands):
        b = f["box"]
        if b[0] <= ix <= b[2] and b[1] <= iy <= b[3] and inside_idx is None:
            inside_idx = k
        ov = (max(0.0, min(b[2], inner_rect[2]) - max(b[0], inner_rect[0])) *
              max(0.0, min(b[3], inner_rect[3]) - max(b[1], inner_rect[1])))
        if ov > best_ov:
            best, best_ov = k, ov
    if inside_idx is not None:
        best = inside_idx

    big = max(range(len(cands)), key=lambda k: cands[k]["area"])
    cen = min(range(len(cands)),
              key=lambda k: (cands[k]["cx"] - 100) ** 2 + (cands[k]["cy"] - 100) ** 2)
    return best, len(cands), (big, cen)


# ---------------------------------------------------------------- 主流程
def collect(limit, only_explicit):
    rows, seen, explicit = [], set(), []
    for f in LV:
        p = os.path.join(PUB, f)
        if not os.path.exists(p):
            continue
        for line in io.open(p, encoding="utf-8", errors="replace"):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            char, _, body = line.partition("\t")
            char = char.strip()
            if not char or char in seen:
                continue

            # 一个字的多个 IDS 定义组用 ; 分隔; 而 [n] 常常出现在**嵌套**位置
            # (比如 龜 是 ⿱⺈⿹⿴[3]...), 所以要在整个串里找每一个算符位置,
            # 不能只看最外层、也不能只看第一组。
            hits = []
            for raw in body.split(";"):
                clean = strip_notation(raw)
                if not clean:
                    continue
                for m in re.finditer(r"([%s])(\[(\d+)\])?" % OPCH, clean):
                    if only_explicit and not m.group(2):
                        continue
                    kids, _ = split_children(clean, m.end(), 2)
                    if len(kids) < 2:
                        continue
                    a, b = first_char(kids[0]), first_char(kids[1])
                    if not a or not b:
                        continue
                    hits.append((m.group(1), int(m.group(3)) if m.group(3) else 0,
                                 bool(m.group(2)), a, b))
                    if m.group(2):                # 显式 [n] 优先
                        break
                if hits and hits[-1][2]:
                    break
            if not hits:
                continue

            for op, explicit_n, has_n, a, b in hits:
                refs = refs_of(char)
                if len(refs) < 2:
                    continue
                cont = [r for r in refs if r[0].startswith("u%x" % ord(a))]
                inn = [r for r in refs if r[0].startswith("u%x" % ord(b))]
                if not cont or not inn:
                    continue
                seen.add(char)

                cname, crect = cont[0]
                iname, irect = inn[0]
                cw, ch = crect[2] - crect[0], crect[3] - crect[1]
                if cw <= 0 or ch <= 0:
                    continue
                # 设计者矩形 → 容器自己的 0-200 空间
                norm = ((irect[0] - crect[0]) / cw * 200.0,
                        (irect[1] - crect[1]) / ch * 200.0,
                        (irect[2] - crect[0]) / cw * 200.0,
                        (irect[3] - crect[1]) / ch * 200.0)

                k, n, (big, cen) = order_of(op, cname, norm)
                if k is None:
                    continue
                rows.append((char, op, k, n, explicit_n, big, cen))
                if has_n:
                    explicit.append((char, op, k, n, explicit_n, cname, iname))
                if not only_explicit:
                    break                          # 一个字只记一行
            if not only_explicit and len(rows) >= limit:
                return rows, explicit
    return rows, explicit


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only_explicit = "--explicit" in sys.argv
    limit = int(args[0]) if args else 400

    rows, explicit = collect(limit, only_explicit)
    print(f"评分 {len(rows)} 个包围字 (容器与内部件都能在字形里对上)\n")
    if not rows:
        print("  (没扫到样本: 该字在 KAGE 库里可能没有字形, 或 --explicit 过滤太严)")
        return

    c0 = sum(1 for r in rows if r[2] == 0)
    cbig = sum(1 for r in rows if r[2] == r[5])
    ccen = sum(1 for r in rows if r[2] == r[6])
    print(f"  三种「默认该选哪个」的命中率 (全部 {len(rows)} 字):")
    print(f"    文档语义 #0 第一个   {c0:4d}/{len(rows)} = {c0/len(rows)*100:5.1f}%   ← §6.6 的默认")
    print(f"    现在语义 最大面积     {cbig:4d}/{len(rows)} = {cbig/len(rows)*100:5.1f}%   ← max_empty_rect")
    print(f"    最靠近画布中心        {ccen:4d}/{len(rows)} = {ccen/len(rows)*100:5.1f}%")

    multi = [r for r in rows if r[3] > 1]
    if multi:
        m0 = sum(1 for r in multi if r[2] == 0)
        mb = sum(1 for r in multi if r[2] == r[5])
        print(f"\n  只看「真有得选」的字 (候选 >1 个, 共 {len(multi)} 个):")
        print(f"    文档语义 #0 第一个   {m0}/{len(multi)} = {m0/len(multi)*100:.1f}%")
        print(f"    现在语义 最大面积     {mb}/{len(multi)} = {mb/len(multi)*100:.1f}%")

    print("\n  序号分布:", dict(sorted(collections.Counter(r[2] for r in rows).items())))
    print("  每字候选数分布:", dict(sorted(collections.Counter(r[3] for r in rows).items())))

    byop = collections.defaultdict(lambda: [0, 0])
    for ch, op, k, n, _e, _b, _c in rows:
        byop[op][1] += 1
        if k == 0:
            byop[op][0] += 1
    print("\n  按算符:")
    for op in sorted(byop, key=lambda o: -byop[o][1]):
        hit, tot = byop[op]
        print(f"    {op}  命中 #0 {hit:4d}/{tot:4d} = {hit/tot*100:5.1f}%")

    if explicit:
        print(f"\n  显式写了 [n] 的字 —— 排序规则能否复现作者的 n:")
        for ch, op, k, n, e, cname, iname in explicit:
            print(f"    {'✓' if k == e else '×'} {ch}  {op}[{e}]  候选 {n} 个, "
                  f"设计者落在 #{k}   ({cname} ← {iname})")


if __name__ == "__main__":
    main()
