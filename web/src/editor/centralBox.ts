/**
 * centralBox.ts —— 内部件的「中宫盒」(移植自 scripts/central_box.py 的 return_segement)
 *
 * 语义: 中宫盒是"内部件应当被填满的那块区域"。
 *   上界 = 中心以上那些骨架点的**弧长加权**坐标均值 (perc 调每段取位)
 *   下界 = 中心以下同理; 左右同理
 * 于是框形部件 (口/日/田) 的中宫接近墨迹盒 → 放进空腔只放大一点点;
 * 交叉形 (乂/木/人) 的中宫被拉向中心 → 放大得多。
 *
 * 三个必须保留的细节 (都是 Python 版踩出来的):
 *   1. 某一侧**没有墨量**时 (纯横线的 y 两侧全空) 边界**落在中心**, 不是 0 ——
 *      0 会给出落在画布原点的假边界 (实测 一 给出 y1=0.0, 丨 给出 x1=0.0)
 *   2. 最后 min(x1, xm-15) / max(x2, xm+15): 中宫至少半幅 15 (这是"中宫"的定义,
 *      不是安全阀 —— 它同时挡住除零和"框塌成一条线")
 *   3. ifnormal: 把面积归一成正方形 (边长 = √面积), 保持中心到四边的比例
 */

import type { Box4 } from "./cavity";
import { strokePoint } from "./strokeOutline";

/** 中宫最小半幅 */
export const MIN_HALF = 15;

interface Seg { x1: number; y1: number; x2: number; y2: number; len: number }
interface Piece { v1: number; v2: number; w: number }

/** 沿轴的加权取位: I(min,max,p) —— p=0.5 即中点, p=1 取更外侧的端点 */
const iMin = (a: number, b: number, p: number): number => {
  const lo = Math.min(a, b), hi = Math.max(a, b);
  return lo * p + hi * (1 - p);
};
const iMax = (a: number, b: number, p: number): number => {
  const lo = Math.min(a, b), hi = Math.max(a, b);
  return hi * p + lo * (1 - p);
};

/** 笔画串 → 采样段 (相邻采样点连成一段, 权重 = 段长) */
function segmentsOf(strokes: string[]): Seg[] {
  const segs: Seg[] = [];
  for (const s of strokes) {
    const g = strokePoint(s);
    if (!g) continue;
    const v = g.verts;
    for (let i = 0; i + 1 < v.length; i++) {
      const len = Math.hypot(v[i + 1].x - v[i].x, v[i + 1].y - v[i].y);
      segs.push({ x1: v[i].x, y1: v[i].y, x2: v[i + 1].x, y2: v[i + 1].y, len });
    }
  }
  return segs;
}

/** 长度加权的段中点 = 骨架"重心" */
function central(segs: Seg[]): [number, number] {
  let sx = 0, sy = 0, tot = 0;
  for (const s of segs) {
    sx += ((s.x1 + s.x2) / 2) * s.len;
    sy += ((s.y1 + s.y2) / 2) * s.len;
    tot += s.len;
  }
  if (tot === 0) {
    if (segs.length === 0) return [100, 100];
    let ax = 0, ay = 0;
    for (const s of segs) { ax += (s.x1 + s.x2) / 2; ay += (s.y1 + s.y2) / 2; }
    return [ax / segs.length, ay / segs.length];
  }
  return [sx / tot, sy / tot];
}

/**
 * 把每个一维区间在 cut 处切成两段, 权重按分割比分摊。
 * 对应 Python 的 Section.divide + divide_part。
 */
function splitAt(segs: Seg[], axis: "x" | "y", cut: number): [Piece[], Piece[]] {
  const lo: Piece[] = [];
  const hi: Piece[] = [];
  for (const s of segs) {
    const a = axis === "x" ? s.x1 : s.y1;
    const b = axis === "x" ? s.x2 : s.y2;
    const v1 = Math.min(a, b), v2 = Math.max(a, b);
    const L = v2 - v1;
    if (cut <= v1) { lo.push({ v1, v2, w: 0 }); hi.push({ v1, v2, w: s.len }); continue; }
    if (cut >= v2) { lo.push({ v1, v2, w: s.len }); hi.push({ v1, v2, w: 0 }); continue; }
    const n = (cut - v1) / L;
    lo.push({ v1, v2: cut, w: s.len * n });
    hi.push({ v1: cut, v2, w: s.len * (1 - n) });
  }
  return [lo, hi];
}

const weighted = (
  pieces: Piece[],
  pick: (v1: number, v2: number, p: number) => number,
  p: number,
): { sum: number; w: number } => {
  let sum = 0, w = 0;
  for (const it of pieces) {
    sum += pick(it.v1, it.v2, p) * it.w;
    w += it.w;
  }
  return { sum, w };
};

export interface CentralBox {
  box: Box4;
  center: [number, number];
}

/**
 * 内部件 → 中宫盒 + 中心
 *   perc     : 每段内部的取位 (0.5=中点; 1 取更外侧的端点)
 *   ifnormal : 面积归一成正方形 (kage 的 99 矩形常是方的)
 */
export function centralBox(strokes: string[], perc = 0.5, ifnormal = false): CentralBox | null {
  const segs = segmentsOf(strokes);
  if (segs.length === 0) return null;
  const [xm, ym] = central(segs);

  const [lx, hx] = splitAt(segs, "x", xm);
  const [ly, hy] = splitAt(segs, "y", ym);
  const a = weighted(lx, iMin, perc);
  const b = weighted(hx, iMax, perc);
  const c = weighted(ly, iMin, perc);
  const d = weighted(hy, iMax, perc);

  // 该侧没有墨量 → 落在中心 (再用下面的 ±MIN_HALF 撑出最小半幅)
  let x1 = a.w > 0 ? a.sum / a.w : xm;
  let x2 = b.w > 0 ? b.sum / b.w : xm;
  let y1 = c.w > 0 ? c.sum / c.w : ym;
  let y2 = d.w > 0 ? d.sum / d.w : ym;

  x1 = Math.min(x1, xm - MIN_HALF);
  x2 = Math.max(x2, xm + MIN_HALF);
  y1 = Math.min(y1, ym - MIN_HALF);
  y2 = Math.max(y2, ym + MIN_HALF);

  if (ifnormal && x2 > x1 && y2 > y1) {
    const S = (x2 - x1) * (y2 - y1);
    const kx = (x2 - xm) / (x2 - x1);
    const ky = (y2 - ym) / (y2 - y1);
    const L = Math.sqrt(S);
    x1 = xm - L * (1 - kx);
    x2 = xm + L * kx;
    y1 = ym - L * (1 - ky);
    y2 = ym + L * ky;
  }
  return { box: [x1, y1, x2, y2], center: [xm, ym] };
}

/** 以 center 为心把盒放大/缩小 k 倍 (对应 ids_anal.box_map) */
export function boxMap(box: Box4, center: [number, number], k = 1): Box4 {
  const [xm, ym] = center;
  return [
    xm - k * (xm - box[0]),
    ym - k * (ym - box[1]),
    xm + k * (box[2] - xm),
    ym + k * (box[3] - ym),
  ];
}

/** 两条盒按 t 插值 (对应 ids_anal.list_Int) */
export function lerpBox(a: Box4, b: Box4, t = 0.5): Box4 {
  return [
    a[0] * t + b[0] * (1 - t),
    a[1] * t + b[1] * (1 - t),
    a[2] * t + b[2] * (1 - t),
    a[3] * t + b[3] * (1 - t),
  ];
}
