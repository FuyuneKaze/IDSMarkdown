# -*- coding: utf-8 -*-
"""
包围算符的空腔枚举与排序 —— 白式 IDS §6.6 的参考实现

【腔是什么】
  容器墨迹补集里的**面**。不是"最大内接矩形": 那个可能横跨两格, 也可能在同
  一个格子里偏心; 而文档说的"全封闭空间"是拓扑上的面。

【怎么做】
  ① 障碍 = 各笔画的墨迹盒 (shrink=False)
  ② 外框 F = 障碍的并集外接矩形  ← 必须用墨迹自己的框, 不能用 0-200
  ③ 竖条扫描, 精确覆盖补集 (无栅格、无子进程)
  ④ 并查集把"相邻条带共边且 y 重叠"的矩形并成面
  ⑤ 面的外接框贴到 F 的哪几条边 → 那几条边"开口"
  ⑥ 按算符要求封闭的边筛 (带放宽阶梯), 再按 §6.6 排序

  第 ⑤ 步是全部关键: F 是墨迹自己的框, 所以"面贴着 F 的某条边"等价于
  "那个方向没有墨迹封着"。9 个包围算符于是只剩 NEED 那张表。

【对外只有 4 个名字】
  ink_boxes(src)        串或笔画 list → 障碍盒
  faces(src)            串或笔画 list → (faces, outer)
  rank_faces(fs, op)    按算符筛 + 排序 → 候选
  cavity_of(src, op, i) [n] 入口: 第 i 个候选的矩形

  没有"分段"参数: 按最近骨架点给轮廓点归段会让弯折处漏空, 障碍盖不住笔画,
  腔就漏到外面 (实测 日 的两格会并成一个包住全字的大面)。要用分段, 先得证明
  "段盒的并集覆盖整笔"。
"""

import math

try:
    from stroke_outer import strokic_boundary, divide_boundary
except Exception:                                    # 允许单独 import 做测试
    strokic_boundary = divide_boundary = None

STROKE_KINDS = ("1", "2", "3", "4", "6", "7")

# 是否把弯曲笔画切开成多盒。**默认开**: type 3/4 必须切 (一笔一盒会把整条弯
# 占成一个矩形, 弯内侧的空白全被算成障碍, 腔被挤到角落); 其他类型走的是与
# 一笔一盒**数值等价**的路径 (divide_boundary 不切分时返回同一个盒)。
# 以后加纵撇等新切法都从 divide_boundary 的 cutof 进, 这里不用再动。
# 注意这只影响**腔和内部件盒**: ids_anal.bbox (⿰⿱ 布局) 仍然用一笔一盒。
SPLIT = True

# 每个包围算符要求"哪几条边必须被墨迹封住"; 补集的面贴着外框的边 = 那几条边开口。
# 文档 §2.1 的名字 + §6.6 的例子。
NEED = {
    "⿴": set("上下左右"),   # OC 全包围   囚=⿴囗人   → 封闭的面(洞), 无开口
    "⿵": set("上左右"),     # OD 上包围   冈=⿵冂乂   → 开口向下
    "⿶": set("下左右"),     # OU 下包围   凶=⿶凵乂   → 开口向上
    "⿷": set("上下左"),     # OR 左包围   区=⿷匚乂   → 开口向右
    "⿸": set("上左"),       # RD 左上包围 仄=⿸厂人   → 开口右下
    "⿹": set("上右"),       # LD 右上包围 寸=⿹𬺰丶   → 开口左下
    "⿺": set("下左"),       # RU 左下包围 亾=⿺𠃊人   → 开口右上
    "⿼": set("上下右"),     # OL 右包围   �=⿼叉丶    → 开口向左
    "⿽": set("下右"),       # LU 右下包围 斗=⿽十⺀   → 开口左上
}
ALL_EDGES = set("上下左右")


# ---------------------------------------------------------------- 障碍盒
def part_boxes(stro, shrink=False, split=None):
    """单笔画 → 盒列表

    split 时走 stroke_outer.divide_boundary (弯曲笔画切段, 每笔 N 个盒);
    不 split 时就是一笔一盒, 数值与 stroke_outer.strokic_boundary 相同。

    出错**不吞**: divide_boundary 的异常直接抛上来, traceback 会指向出问题的
    那支笔画 —— 比静默回退到一笔一盒好定位得多 (静默回退看起来一切正常, 结果
    却可能悄悄变了)。
    """
    if split is None:
        split = SPLIT
    if split:
        boxes = divide_boundary(stro, ifshrink=shrink)
    else:
        boxes = [strokic_boundary(stro, shrink)]
    # 退化盒 (宽或高为 0) 不算障碍 —— 这是"没面积的点/线不挡路"的语义,
    # 不是容错: 老路径 strokic_box 也是这么过滤的。
    return [(b.x1, b.y1, b.x2, b.y2) for b in boxes
            if b.x2 > b.x1 and b.y2 > b.y1]


def ink_boxes(src, shrink=False, split=None):
    """串(dump 后的字形或 return_bone 结果) 或 笔画 list → 障碍盒 list

    shrink=False 才是墨迹范围 (腔/外框都要这一档; shrink=True 会按 ofs 收掉
    笔尖边, 那是给"分配比例"用的另一档, 别混)。
    """
    strokes = src.split("$") if isinstance(src, str) else src
    out = []
    for s in strokes:
        s = s.strip()
        if not s or s.split(":")[0] not in STROKE_KINDS:
            continue
        out.extend(part_boxes(s, shrink=shrink, split=split))
    return out


def union_box(boxes):
    """矩形并集外接框; 空 → None"""
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


# ---------------------------------------------------------------- 补集的面
def faces(src, eps=0.75, min_side=5.0, split=None):
    """→ (faces, outer)

    face = {"box","open","area","cx","cy"}
      open: 这个面贴着外框的边 (即没有墨迹封着的方向)
      area: 面的真实面积 (多个矩形之和, 不是外接框面积)

    eps      : 判定"连通/封边"时把障碍外扩的量。笔尖的数值噪声会产生 0.1px 的
               缝, 缝一出现就被当成连通, 腔就漏了。面积与位置仍用原始盒算。
    min_side : 扔掉细缝。角的圆角处在盒近似下会留下几像素宽的面 (实测 日 的四角
               各有 5x2 的碎片), 它们会挤进候选把序号搅乱; 真腔不会窄于 5。
    """
    boxes = ink_boxes(src, split=split)
    outer = union_box(boxes)
    if not outer or outer[2] - outer[0] <= 0 or outer[3] - outer[1] <= 0:
        return [], outer

    F = outer
    sealed = [(b[0] - eps, b[1] - eps, b[2] + eps, b[3] + eps) for b in boxes]

    # ③ 竖条扫描: x 事件点 = 外框两边 + 每个障碍的两条竖边 (去掉贴外框的)
    xs = {F[0], F[2]}
    for b in sealed:
        for v in (b[0], b[2]):
            if F[0] + 1e-9 < v < F[2] - 1e-9:
                xs.add(v)
    xs = sorted(xs)

    rects = []                                       # (条带号, x1, y1, x2, y2)
    for strip, (xa, xb) in enumerate(zip(xs, xs[1:])):
        if xb - xa <= 1e-9:
            continue
        spans = sorted((b[1], b[3]) for b in sealed
                       if b[0] < xb - 1e-9 and b[2] > xa + 1e-9)
        cur = F[1]
        for y1, y2 in spans:
            if y1 > cur + 1e-9:
                rects.append((strip, xa, cur, xb, min(y1, F[3])))
            cur = max(cur, y2)
            if cur >= F[3] - 1e-9:
                break
        if cur < F[3] - 1e-9:
            rects.append((strip, xa, cur, xb, F[3]))

    # ④ 并查集: 只有相邻条带 (条带号差 1) 之间共边且 y 重叠的才算连通
    parent = list(range(len(rects)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_strip = {}
    for i, r in enumerate(rects):
        by_strip.setdefault(r[0], []).append(i)
    for i, r in enumerate(rects):
        for j in by_strip.get(r[0] + 1, []):
            g = rects[j]
            if abs(g[1] - r[3]) < 1e-6 and min(r[4], g[4]) - max(r[2], g[2]) > 1e-6:
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    groups = {}
    for i in range(len(rects)):
        groups.setdefault(find(i), []).append(rects[i])

    # ⑤ 每个连通块 → 一个面
    out = []
    for group in groups.values():
        x1 = min(r[1] for r in group)
        y1 = min(r[2] for r in group)
        x2 = max(r[3] for r in group)
        y2 = max(r[4] for r in group)
        if x2 - x1 < min_side or y2 - y1 < min_side:
            continue
        t = 1e-6
        open_edges = set()
        if x1 <= F[0] + t:
            open_edges.add("左")
        if y1 <= F[1] + t:
            open_edges.add("上")
        if x2 >= F[2] - t:
            open_edges.add("右")
        if y2 >= F[3] - t:
            open_edges.add("下")
        out.append({
            "box": (x1, y1, x2, y2),
            "rects": group,          # 面的真实形状 (轴对齐矩形列表); 可能远小于 box
            "open": open_edges,
            "area": sum((r[3] - r[1]) * (r[4] - r[2]) for r in group),
            "cx": (x1 + x2) / 2.0,
            "cy": (y1 + y2) / 2.0,
        })
    return out, outer


# ---------------------------------------------------------------- 筛选与排序
def rank_faces(fs, op, min_w=20.0, min_h=20.0):
    """按算符要求**严格**筛边 → 挂上安放盒(内接矩形) → 按 §6.6 排序

    严格 = 要求封闭的边必须**全封住**, 不搞"允许差一条"的放宽。
    为什么取消放宽: 对本来就没有口袋的容器 (辶 是开口钩子、行 是左右分立、
    衣 是上下分立), 放宽会硬凑出一个候选 ——
      · 辶: 把**外部面**(开口=上/右/左)拉进来, 又因面积最大被选中,
        于是"上边 3/4 全成 cavity、忽略横折左边";
      · 行/衣: 把中间的细缝或某个碎面拉进来, 反而比原来的 max_empty_rect 差。
    严格筛时这些容器给空 → 调用方退回 max_empty_rect (老做法), 那里表现更好。

    再挂一道质量线: 面的**内接矩形**太小就没有安放价值 (鬼 的那个面是 10 块拼成
    的梳形, 内接矩形只有 9x102), 直接不算候选, 也退回老做法。
    """
    need = NEED.get(op)
    if not need:
        return []
    out = []
    for f in fs:
        if not need <= (ALL_EDGES - f["open"]):
            continue
        ins = inscribed(f["rects"])
        if not ins or (ins[2] - ins[0]) < min_w or (ins[3] - ins[1]) < min_h:
            continue
        f = dict(f, ins=ins)             # 安放盒跟着面一起走, 免得调用方重算
        out.append(f)
    return _order(out)


def _order(fs, row_overlap=0.5):
    """§6.6: 从上到下分行, 行内从左到右"""
    rows = []
    for f in sorted(fs, key=lambda f: (f["cy"], f["cx"])):
        for row in rows:
            if any(_v_overlap(f, g) > row_overlap for g in row):
                row.append(f)
                break
        else:
            rows.append([f])
    return [f for row in rows for f in sorted(row, key=lambda f: f["cx"])]


def _v_overlap(a, b):
    """两个面在 y 方向的重叠 / 较矮者的高度"""
    lo = max(a["box"][1], b["box"][1])
    hi = min(a["box"][3], b["box"][3])
    shorter = min(a["box"][3] - a["box"][1], b["box"][3] - b["box"][1])
    return (hi - lo) / shorter if shorter > 0 else 0.0


def cavity_list(src, op, split=None):
    """排序好的全部候选 (预览编号 / 评分器用)"""
    return rank_faces(faces(src, split=split)[0], op)


def inscribed(rects):
    """面(轴对齐矩形列表)里**最大的内接矩形**

    为什么不能用面的外接框当安放盒: 面常常是 L 形/U 形/梳形, 外接框会盖住容器的
    墨迹 —— 视觉上就是"腔侵入字里"。

    算法: 面从竖条扫描出来, 是一堆矩形 (每条带若干互不重叠的 y 段)。
      ① 取所有矩形的竖边做切片 [x_k, x_{k+1}]
      ② 每个切片内被面覆盖的 y 段 = 该切片内矩形 y 段的并集
      ③ 一个 x 区间 [x_k, x_{m+1}] 可用的 y 段 = 各切片 y 段的**交集**
         (每层都得被覆盖, 否则矩形就跨出面边界了)
      ④ 取面积最大的那个

    ⚠️ 老写法要求"某个矩形**单独**覆盖整个 [xa,xb]", 那是错的: 一个 100% 填充的
    矩形面会被切成 2 条带, 没有单条能覆盖全宽, 于是只拿到半条竖带 —— 实测
    ⿸疒粤 的面 (63.8,54.8)-(186,189.4) 填充 100%, ins 却只有右半
    (125.8,54.8)-(186,189.4), 于是内部件被塞进右半、左边那条大空间被无视。
    现在按交集算, 100% 填充的面会原样返回。
    """
    if not rects:
        return None

    def union_runs(pairs):
        out = []
        for y1, y2 in sorted(pairs):
            if out and y1 <= out[-1][1] + 1e-9:
                out[-1] = (out[-1][0], max(out[-1][1], y2))
            else:
                out.append((y1, y2))
        return out

    def isect_runs(A, B):
        out = []
        for a1, a2 in A:
            for b1, b2 in B:
                lo, hi = max(a1, b1), min(a2, b2)
                if hi > lo + 1e-9:
                    out.append((lo, hi))
        return union_runs(out)

    xs = sorted({v for r in rects for v in (r[1], r[3])})
    if len(xs) < 2:
        return None
    # ② 每个切片的 y 覆盖
    cov = [union_runs([(r[2], r[4]) for r in rects
                       if r[1] <= xa + 1e-9 and r[3] >= xb - 1e-9])
           for xa, xb in zip(xs, xs[1:])]

    # ③ 区间 [x_k, x_{m+1}] 的 y 覆盖 = 逐切片求交
    best, best_area = None, -1.0
    for k in range(len(cov)):
        if not cov[k]:
            continue
        acc = cov[k]
        for m in range(k, len(cov)):
            if m > k:
                acc = isect_runs(acc, cov[m])
                if not acc:
                    break
            y1, y2 = max(acc, key=lambda t: t[1] - t[0])
            a = (xs[m + 1] - xs[k]) * (y2 - y1)
            if a > best_area:
                best_area, best = a, (xs[k], y1, xs[m + 1], y2)
    return best


def cavity_of(src, op, index=0, split=None):
    """§6.6 的 [n] 入口: 第 index 个候选的**安放盒** (= 面内最大内接矩形)

    没候选 → None (调用方退回老算法, 别让字消失);
    越界 → 夹紧到最后一个。
    """
    cands = cavity_list(src, op, split=split)
    if not cands:
        return None
    index = min(max(index, 0), len(cands) - 1)
    return inscribed(cands[index]["rects"]) or cands[index]["box"]
