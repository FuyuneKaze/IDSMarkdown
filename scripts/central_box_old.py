# -*- coding: utf-8 -*-
"""
central_box —— 从骨架算"内容基准框" (替代 fit_into 里 [lo,hi] 的二选一启发式)

【思路】
  骨架是一条折线, 沿弧长给每个位置同样的权重。于是某个方向上的"内容密度"就是
  骨架在该方向的投影密度。基准框的四条边 = 中心某一侧那些点的**弧长加权均值**:
      上界 = E[y | y < cy],  下界 = E[y | y > cy],  左右同理
  框形部件 (口/日/田) 的笔画集中在边缘 → 基准接近墨迹盒 → 放进空腔只放大一点点;
  交叉形 (乂/木/人) 的笔画穿过中心 → 基准被拉向中心 → 放大得多。
  这正是"口 小一点才好看、乂 应该顶满"这条经验的可计算版本。

【为什么不用采样点、也不用真的把线段切开】
  设一段从 (x1,y1) 到 (x2,y2), 参数 t∈[0,1], 弧长 ds = L·dt, 坐标线性:
      ∫_{t0}^{t1} x(t)·L dt = L·[ x1·(t1-t0) + (x2-x1)·(t1²-t0²)/2 ]
  "x < cx 的那部分"在 t 轴上只是一个区间 [t0,t1], 端点由
      t* = (cx - x1)/(x2 - x1)  再 clamp 到 [0,1]
  决定, 递减段也不例外。所以只要**按 t 截区间再积分**就行 ——
  既不需要把 Segment 真的切成两半, 也不需要重采样, 更没有"哪个端点是 xmin"的陷阱。

  ⚠️ 这一段是本文件的关键: 旧写法 `divide()` 里用
      y = ymin + ratio*dy        (ratio 由 x 推出)
  只对"左下→右上"的正斜率段成立。撇/捺是负斜率段, ymin 在**右**端, 公式给出的
  交点 y 是镜像的, 于是切出来的两段长度全错 —— 而长度就是权重, 错的很隐蔽。

【约定】
  canvas 坐标 y 向下: "上" = y 较小。返回 (left, top, right, bottom)。
"""

from glyph_extend import return_bone
from stroke_outer import (Point, Bbox, prt_point_in_list, stroke_point,
                          strokic_boundary, bone_shape_function)
import numpy as np

STROKE_KINDS = ("1", "2", "3", "4", "6", "7")

# 加权口径 (只影响"骨架点的密度", 不影响退化判定):
#   "len" 按弧长 —— 细长笔画 (撇/捺/辶尾) 与粗笔画等权
#   "ink" 按 弧长×笔宽 ≈ 墨迹面积 —— 与视觉重量一致, 粗笔画说话更响
WEIGHT = "ink"

# "该侧边界"的取法: None = 加权**均值**; 给 0~0.5 的数 = 从外侧数第 q 分位。
# q 越小越靠墨迹边缘 → 基准框越大 → 部件被缩小得越多。
# 注意: 框形部件(口/日)那一侧的墨量集中在一条笔画上, 分布接近点质量, q 几乎不起
# 作用; 交叉形(乂/人)那一侧分布均匀, q 影响很大 —— 这就是"形状敏感"的旋钮。
# ⚠️ 实测 q>=0.3 时"两侧质量集中在笔尖"的部件(人)会让分位点跳空, 有效区 0~0.2。
QUANTILE = None

# alpha>0 时(内容框 = central_box)在基准上再乘的全局余量。
# 参考标定: QUANTILE=0.15 时 口 的放大率 ≈1.26, 乘 1.43 ≈ 0.88 (设计者中位)。
MARGIN = 1.0


class Segment:
    def __init__(self, P1=Point(0, 0), P2=Point(0, 0)):
        self.P1 = P1
        self.P2 = P2
        self.x1 = P1.x
        self.y1 = P1.y
        self.x2 = P2.x
        self.y2 = P2.y
        self.dx = abs(self.x2 - self.x1)
        self.dy = abs(self.y2 - self.y1)
        self.length = np.sqrt(self.dx ** 2 + self.dy ** 2)
        self.angle = np.inf if self.dx == 0 else np.atan(self.dy / self.dx)
        self.central = (P1 + P2) / 2
        self.xmax = max(self.x1, self.x2)
        self.xmin = min(self.x1, self.x2)
        self.ymax = max(self.y1, self.y2)
        self.ymin = min(self.y1, self.y2)
        self.weight = self.length     # 统计权重; segments_of 按 WEIGHT 改写

    def __str__(self):
        return f"{self.P2}"#f"polygon({self.P1},{self.P2})"

    # ------------------------------------------------------------------
    # divide() 已废弃, 保留注释备查: 它的插值对负斜率段是错的 (见文件头),
    # 而且新做法根本不需要真的切段 —— 用 _integ() 的闭式积分即可。
    # def divide(self, div_axis="x", div_var=None):
    #     ...
    # ------------------------------------------------------------------


# ======================================================================
# 骨架 → 线段
# ======================================================================
def segments_of(bones: str, curve: str = "poly") -> list:
    """字形串 (return_bone 结果) → Segment 列表

    bones : 竖线/横线用控制点直接连线即可 (它们是直的);
    curve : 曲线笔画 (type 2/3/6/7) 的取法
        "poly"   用控制点连线 —— 少算点, 但曲率大的地方会把弧长估长
        "sample" 用 stroke_point 的采样点连线 —— 贴合曲线, 慢一点
    两种取法对**基准比例**的影响见 __main__ 里的对比。
    """
    segs = []
    for s in bones.split("$"):
        s = s.strip()
        if not s or s.split(":")[0] not in STROKE_KINDS:
            continue
        tp = s.split(":")[0]
        if curve == "sample" and tp in ("2", "3", "4", "6", "7"):
            pts, _n, _e = stroke_point(s)
            pts = [Point(float(p.x), float(p.y)) for p in pts]
        else:
            keys = s.split(":")
            pts = [Point(eval(keys[i]), eval(keys[i + 1]))
                   for i in range(3, len(keys) - 1, 2)]
        if len(pts) < 2:
            continue
        # 沿这条笔画累计弧长 → 归一化参数, 用来取 bone_shape_function 的笔宽
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + np.hypot(b.x - a.x, b.y - a.y))
        total = cum[-1] or 1.0
        for i in range(len(pts) - 1):
            seg = Segment(pts[i], pts[i + 1])
            if WEIGHT == "ink":
                # 权重 = 弧长 × 平均全宽 ≈ 该段的墨迹面积 (视觉重量)
                w = (bone_shape_function(cum[i] / total) +
                     bone_shape_function(cum[i + 1] / total))
                seg.weight = seg.length * w
            else:
                seg.weight = seg.length
            segs.append(seg)
    return segs


# ======================================================================
# 一维截断积分 (全部数学都在这里)
# ======================================================================
def _integ(a: float, b: float, t0: float, t1: float) -> float:
    """∫_{t0}^{t1} v(t) dt, v(t) = a + (b-a)t  (即"该区间的坐标和")"""
    if t1 <= t0:
        return 0.0
    return a * (t1 - t0) + (b - a) * (t1 * t1 - t0 * t0) / 2.0


def _clip_range(a: float, b: float, cut: float, side: int) -> tuple:
    """v(t) = a+(b-a)t 落在 cut 的 side 侧 (-1: v<cut, +1: v>cut) 的 t 区间"""
    if a == b:                                   # 与轴平行: 整段同侧或不同侧
        inside = (a < cut) if side < 0 else (a > cut)
        return (0.0, 1.0) if inside else (0.0, 0.0)
    t = (cut - a) / (b - a)                      # v(t) == cut 处
    if a < b:                                    # t 递增 → v 递增
        t = min(max(t, 0.0), 1.0)
        return (0.0, t) if side < 0 else (t, 1.0)
    t = min(max(t, 0.0), 1.0)                    # t 递增 → v 递减
    return (t, 1.0) if side < 0 else (0.0, t)


def side_mean(segs: list, axis: int, side: int, cut: float):
    """沿 axis 落在 cut 某一侧的部分, 按弧长加权的坐标均值

    side=-1 → 取 v<cut 的部分; side=+1 → 取 v>cut 的部分。
    **该侧一个骨架点都没有时返回 None** (退化), 由调用方决定怎么补 ——
    一根纯横线在 y 方向上就是两侧全空, 这时任何"均值"都没有定义。
    """
    num = den = 0.0
    for s in segs:
        a, b = (s.x1, s.x2) if axis == 0 else (s.y1, s.y2)
        t0, t1 = _clip_range(a, b, cut, side)
        if t1 <= t0:
            continue
        num += s.weight * _integ(a, b, t0, t1)
        den += s.weight * (t1 - t0)
    return num / den if den else None


def side_pieces(segs: list, axis: int, side: int, cut: float) -> list:
    """该侧每一段对坐标分布的贡献: (v_lo, v_hi, 权重)

    每段在 t 上均匀 → 它的坐标值在 [v_lo,v_hi] 上均匀, 权重就是该段的统计权重。
    分位点就是这个"分段均匀密度"的分位数, 用二分求 (CDF 单调且分段线性)。
    """
    out = []
    for s in segs:
        a, b = (s.x1, s.x2) if axis == 0 else (s.y1, s.y2)
        t0, t1 = _clip_range(a, b, cut, side)
        if t1 <= t0:
            continue
        v0 = a + (b - a) * t0
        v1 = a + (b - a) * t1
        out.append((min(v0, v1), max(v0, v1), s.weight * (t1 - t0)))
    return out


def side_quantile(segs: list, axis: int, side: int, cut: float, q: float,
                  iters: int = 40):
    """该侧坐标分布的 q 分位点 (q=0 取最外侧, q=0.5 是中位数)"""
    pieces = side_pieces(segs, axis, side, cut)
    total = sum(p[2] for p in pieces)
    if total <= 0:
        return None
    target = q * total

    def cdf(v):
        acc = 0.0
        for lo, hi, m in pieces:
            if v <= lo:
                continue
            if v >= hi:
                acc += m
            else:
                acc += m * (v - lo) / (hi - lo)
        return acc

    a = min(p[0] for p in pieces)
    b = max(p[1] for p in pieces)
    for _ in range(iters):
        m = (a + b) / 2.0
        if cdf(m) < target:
            a = m
        else:
            b = m
    return (a + b) / 2.0


def axis_mean(segs: list, axis: int) -> float:
    """沿 axis 的全量加权均值 (= 重心); 不会为空"""
    num = den = 0.0
    for s in segs:
        a, b = (s.x1, s.x2) if axis == 0 else (s.y1, s.y2)
        num += s.weight * _integ(a, b, 0.0, 1.0)
        den += s.weight
    return num / den


# ======================================================================
# 基准框
# ======================================================================
def central_box(bones: str, ink_box: tuple = None, curve: str = "poly"):
    """→ (left, top, right, bottom): 骨架的方向加权"内容框"

    top < bottom (canvas y 向下), left < right。
    上界 = E[y | y<cy], 下界 = E[y | y>cy], 左右同理。

    ink_box : 退化侧 (某侧没有骨架点) 用它的对应边来补。两种典型退化:
              纯横线 (一) → y 两侧全空, 只能靠笔宽撑出高度;
              纯竖线 (丨) → x 两侧全空。
              没传 ink_box 又遇到退化 → 直接 raise (宁可报错, 不要悄悄给出
              零高度框让后面的除法炸掉)。
    """
    segs = segments_of(bones, curve=curve)
    if not segs:
        return None
    cx = axis_mean(segs, 0)
    cy = axis_mean(segs, 1)
    out = []
    for axis, cut, side, idx in ((0, cx, -1, 0), (1, cy, -1, 1),
                                 (0, cx, +1, 2), (1, cy, +1, 3)):
        if QUANTILE is None:
            v = side_mean(segs, axis, side, cut)
        else:
            # 分位数从**外侧**数: 左/上那侧取 q, 右/下那侧要反过来取 1-q,
            # 否则 q=0 会把右边界拉到中心 (左边界在最小值、右边界在最大值,
            # 同一套 CDF 方向相反)。
            q_eff = QUANTILE if side < 0 else 1.0 - QUANTILE
            v = side_quantile(segs, axis, side, cut, q_eff)
        if v is None:
            if ink_box is None:
                raise ValueError(
                    f"central_box: 该部件在 {'x' if axis == 0 else 'y'} 方向"
                    f"{'上' if side < 0 else '下'}侧没有骨架点(退化输入), 请传入 ink_box")
            v = float(ink_box[idx])
        out.append(v)
    return tuple(out)


def basis_box(bones: str, ink_box: tuple, alpha: float = 0.0,
              expand: float = None, curve: str = "sample"):
    """fit_into 该用的**基准框**

       先算"内容框"  c = (1-alpha)*墨迹盒 + alpha*central_box
       再按放大率映射 outward:  basis = c 以自身中心撑大到  c宽/mag

    alpha  : 0 = 内容框就是墨迹盒; 1 = 纯 central_box (方向加权)
    expand : 固定外扩比例, 默认 0.068 → 放大率 0.88x

    为什么默认是这个: web/analysis/calib_basis.py 量了 150 个真包围字,
      设计者放大率中位 **0.88x**, 且"贴边框形"与"穿心交叉"两组都是 0.88x ——
      设计者不因为部件穿心就放大它。纯 central_box 会给 2.0~2.5x, 明显过大。
    """
    cb = central_box(bones, ink_box=ink_box, curve=curve)
    if cb is None:
        return None
    c = [(1 - alpha) * float(ink_box[i]) + alpha * cb[i] for i in range(4)]
    w, hh = c[2] - c[0], c[3] - c[1]
    if w <= 0 or hh <= 0:
        return None
    if alpha > 0 and MARGIN:
        w, hh = w * MARGIN, hh * MARGIN    # 全局余量: 把 q 框放大到"格子"尺度
    mag = 1.0 / (1.0 + 2.0 * expand) if expand is not None else 1.0
    if mag <= 0:
        return None
    cw, chh = w / mag, hh / mag                    # 基准比内容框大 → 部件被缩小
    mx, my = (c[0] + c[2]) / 2.0, (c[1] + c[3]) / 2.0
    return (mx - cw / 2.0, my - chh / 2.0, mx + cw / 2.0, my + chh / 2.0)


def basis_ratio(bones: str, curve: str = "sample") -> float:
    """基准框 / 墨迹盒 的比例 —— 越接近 1 说明"笔画贴边"(框形), 越小越"穿心"

    只用骨架自身的极值当 ink_box, 所以对退化的单笔画也安全 (不会 raise)。
    """
    segs = segments_of(bones, curve=curve)
    if not segs:
        return 0.0
    xs = [v for s in segs for v in (s.x1, s.x2)]
    ys = [v for s in segs for v in (s.y1, s.y2)]
    ink = (min(xs), min(ys), max(xs), max(ys))
    cb = central_box(bones, ink_box=ink, curve=curve)
    w = ink[2] - ink[0]
    return (cb[2] - cb[0]) / w if w else 0.0


# ======================================================================
if __name__ == "__main__":
    '''CASES = [("口", "u53e3"), ("乂", "u4e42"), ("国", "u56fd"), ("日", "u65e5"),
             ("田", "u7530"), ("人", "u4eba"), ("乃", "u4e43"), ("木", "u6728"),
             ("丶", "u4e36"), ("心", "u5fc3"), ("一", "u4e00"), ("我", "u6211")]
    print(f"{'部件':5s} " + " ".join(f"{lbl:>10s}" for lbl in
          ("均值(None)", "q=0.5", "q=0.4", "q=0.3", "q=0.2", "q=0.1", "q=0.0")))
    old_q = QUANTILE
    for ch, nm in CASES:
        bones = return_bone(nm)
        boxes = []
        for s in bones.split("$"):
            s = s.strip()
            if not s or s.split(":")[0] not in STROKE_KINDS:
                continue
            b = strokic_boundary(s, False)
            boxes.append((b.x1, b.y1, b.x2, b.y2))
        if not boxes:
            print(f"{ch:5s}   (没有直绘笔画)")
            continue
        ink = (min(b[0] for b in boxes), min(b[1] for b in boxes),
               max(b[2] for b in boxes), max(b[3] for b in boxes))
        iw = ink[2] - ink[0]
        cells = []
        for q in (None, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0):
            QUANTILE = q
            f = central_box(bones, ink_box=ink)
            cells.append(f"{iw/(f[2]-f[0]):9.2f}x" if f and f[2] > f[0] else "     --  ")
        print(f"{ch:5s} " + " ".join(cells))
    QUANTILE = old_q
    print("\n(数字 = 放大率 = 墨迹宽/基准宽; 1.0x 表示部件刚好填满空腔)")'''
    prt_point_in_list(segments_of( return_bone("u53e3")))
