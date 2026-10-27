/**
 * 笔画轮廓 / 包围盒 —— stroke_outer.py 的 TypeScript 移植
 *
 * 用途: 组字时求"部件包围盒"。它必须与 Python 端逐字一致, 因为
 *       ids_anal 的左右/上下分配比例完全建立在这个盒上。
 *
 * 与 KAGE 引擎自带的笔宽 (kMinWidthT) 不同, 这里用的是 stroke_outer 的
 * 笔宽模型 bone_shape_function(起点 15 → 末端 3), 再加上 ifshrink 按
 * edgeofs × ofs 的收缩 —— 那是调出来的经验值, 照抄不要改。
 *
 * 移植注意:
 *   - Interp 在 Python 里先做 t=1-t 的补丁, 等价于标准 lerp
 *   - Bz2_tangent / Bz3_tangent 的系数与教科书式相反(P1/P3 互换),
 *     这是与 Bz2_normal 里 step=1-step 相互抵消的, 不要"修正"
 *   - Point.__mul__(Point) 在 Python 里是叉积, 但本文件所有调用只传标量,
 *     所以未移植叉积分支
 */

export interface Pt {
  x: number;
  y: number;
}

export interface Box {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

const P = (x: number, y: number): Pt => ({ x, y });
const padd = (a: Pt, b: Pt): Pt => P(a.x + b.x, a.y + b.y);
const psub = (a: Pt, b: Pt): Pt => P(a.x - b.x, a.y - b.y);
const pmul = (a: Pt, s: number): Pt => P(a.x * s, a.y * s);
const pdiv = (a: Pt, s: number): Pt => P(a.x / s, a.y / s);
const pdist = (a: Pt, b: Pt): number => Math.hypot(a.x - b.x, a.y - b.y);
const pnorm = (a: Pt): Pt => pdiv(a, Math.hypot(a.x, a.y));
const pswap = (a: Pt): Pt => P(a.y, a.x);

/** 原版 Interp: 先 t=1-t 再 E1*t+E2*(1-t), 等价于 lerp(E1,E2,t) */
const interp = (a: Pt, b: Pt, t: number): Pt =>
  P(a.x * (1 - t) + b.x * t, a.y * (1 - t) + b.y * t);

const bezier2 = (p1: Pt, p2: Pt, p3: Pt, t: number): Pt =>
  interp(interp(p1, p2, t), interp(p2, p3, t), t);

const bezier3 = (p1: Pt, p2: Pt, p3: Pt, p4: Pt, t: number): Pt =>
  interp(bezier2(p1, p2, p3, t), bezier2(p2, p3, p4, t), t);

/** 系数照抄原版 (P1 得 2t、P3 得 2t-2), 与 Bz2_normal 的 step 翻转抵消 */
const bz2Tangent = (p1: Pt, p2: Pt, p3: Pt, t: number): Pt =>
  padd(padd(pmul(p1, 2 * t), pmul(p2, 2 - 4 * t)), pmul(p3, -2 + 2 * t));

const bz3Tangent = (p1: Pt, p2: Pt, p3: Pt, p4: Pt, t: number): Pt =>
  padd(
    padd(pmul(p1, 3 * t), pmul(p2, 6 * t - 9 * t * t)),
    psub(pmul(p3, 3 - 12 * t + 9 * t * t), pmul(p4, 3 * (1 - t) * (1 - t))),
  );

/** 原版 normal(P1,P2,d): 垂直于 P1→P2、长度为 d 的向量 */
const normal = (p1: Pt, p2: Pt, d = 1): Pt => {
  const off = d / pdist(p1, p2);
  return P((p2.y - p1.y) * off, (p1.x - p2.x) * off);
};

/** 原版 Bz2_normal: 先 step=1-step 再取切线, 然后 (x,-y).swap() */
const bz2Normal = (p1: Pt, p2: Pt, p3: Pt, t: number): Pt => {
  const tg = bz2Tangent(p1, p2, p3, 1 - t);
  return pswap(P(tg.x, -1 * tg.y));
};

const bz3Normal = (p1: Pt, p2: Pt, p3: Pt, p4: Pt, t: number): Pt => {
  const tg = bz3Tangent(p1, p2, p3, p4, 1 - t);
  return pswap(P(tg.x, -1 * tg.y));
};

/** 累积弧长, 首项为 0 */
function lengthOfLine(points: Pt[]): number[] {
  const li: number[] = [0];
  let len = 0;
  for (let i = 0; i < points.length - 1; i++) {
    len += pdist(points[i], points[i + 1]);
    li.push(len);
  }
  return li;
}

function pointsToAng(p1: Pt, p2: Pt): number {
  if (p1.x === p2.x) return Math.PI / 2;
  if (p1.y === p2.y) return 0;
  return Math.atan(Math.abs(p2.y - p1.y) / Math.abs(p2.x - p1.x));
}

/** 该点处的走向角: 端点取相邻一段, 中间点取前后平均 */
function areaSlop(pl: Pt[], index: number): number {
  const l = pl.length;
  if (index === 0) return pointsToAng(pl[0], pl[1]);
  if (index === l - 1) return pointsToAng(pl[l - 1], pl[l - 2]);
  return (pointsToAng(pl[index], pl[index - 1]) + pointsToAng(pl[index], pl[index + 1])) / 2;
}

/**
 * 判定四条边"是否要按笔尖收缩"
 *   返回 (x1,y1,x2,y2) 四个 0/1 标志
 *   0 = 该边是笔画侧面(平行于边), 属于真正的"墙", 不收缩
 *   1 = 该边是笔尖/笔尾, 不是墙, 收缩掉
 * tips 非 null 时直接覆盖 (尾形 4=横钩 → y2, 5=竖钩 → y1)
 */
export function boxOffset(
  points: Pt[],
  tips: (number | null)[] = [null, null, null, null],
): number[] {
  let maxxi = 0;
  let minxi = 0;
  let maxyi = 0;
  let minyi = 0;
  let maxx = 0;
  let minx = 200;
  let maxy = 0;
  let miny = 200;

  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (p.x > maxx) {
      maxx = p.x;
      maxxi = i;
    } else if (p.x < minx) {
      minx = p.x;
      minxi = i;
    }
    if (p.y > maxy) {
      maxy = p.y;
      maxyi = i;
    } else if (p.y < miny) {
      miny = p.y;
      minyi = i;
    }
  }

  let x1 = areaSlop(points, minxi) > 1.4 ? 0 : 1;
  let x2 = areaSlop(points, maxxi) > 1.4 ? 0 : 1;
  let y1 = areaSlop(points, minyi) < 0.1 ? 0 : 1;
  let y2 = areaSlop(points, maxyi) < 0.1 ? 0 : 1;

  if (tips[0] !== null && tips[0] !== undefined) x1 = tips[0];
  if (tips[1] !== null && tips[1] !== undefined) x2 = tips[1];
  if (tips[2] !== null && tips[2] !== undefined) y1 = tips[2];
  if (tips[3] !== null && tips[3] !== undefined) y2 = tips[3];
  return [x1, y1, x2, y2];
}

/** 采样密度: 0/15 … 15/15 共 16 个采样点 */
const SAMP = 15;
const SAMPP: number[] = Array.from({ length: SAMP + 1 }, (_, i) => i / SAMP);
/** 圆角基础长度 (与 kage-bundle 的 kMage 同值) */
const KMAGE = 10;

export interface StrokeGeom {
  verts: Pt[];
  normals: Pt[];
  edgeofs: number[];
}

/**
 * 笔画 → 中心线采样点 + 单位法线 + 四边收缩标志
 * 类型: 1 直线 / 2 二次贝塞尔 / 3 折れ / 4 乙線 / 6 三次贝塞尔 / 7 縦払い
 */
export function strokePoint(stro: string): StrokeGeom | null {
  const keys = stro.split("$")[0].split(":").map((s) => parseFloat(s));
  const type = keys[0];
  const tailType = keys[2];
  const tips: (number | null)[] = [null, null, null, null];
  if (tailType === 4) tips[3] = 0; // 横钩
  if (tailType === 5) tips[2] = 0; // 竖钩

  const verts: Pt[] = [];
  const normals: Pt[] = [];

  switch (type) {
    case 1: {
      const v0 = P(keys[3], keys[4]);
      const v1 = P(keys[5], keys[6]);
      verts.push(v0, v1);
      const n = normal(v0, v1, 1);
      normals.push(n, n);
      break;
    }
    case 2: {
      const c = [P(keys[3], keys[4]), P(keys[5], keys[6]), P(keys[7], keys[8])];
      for (const t of SAMPP) {
        verts.push(bezier2(c[0], c[1], c[2], t));
        normals.push(pnorm(bz2Normal(c[0], c[1], c[2], t)));
      }
      break;
    }
    case 3: {
      const c = [P(keys[3], keys[4]), P(keys[5], keys[6]), P(keys[7], keys[8])];
      const t1 = interp(c[1], c[0], KMAGE / pdist(c[1], c[0]));
      const t2 = interp(c[1], c[2], KMAGE / pdist(c[1], c[2]));
      verts.push(c[0]);
      normals.push(normal(t1, c[0], 1));
      for (const t of SAMPP) {
        verts.push(bezier2(t1, c[1], t2, t));
        normals.push(pnorm(bz2Normal(t1, c[1], t2, t)));
      }
      verts.push(c[2]);
      normals.push(normal(c[2], t2, 1));
      break;
    }
    case 4: {
      let rate = 6;
      const c = [P(keys[3], keys[4]), P(keys[5], keys[6]), P(keys[7], keys[8])];
      if (pdist(c[1], c[2]) < 120) rate = pdist(c[1], c[2]) / 20;
      const t1 = interp(c[1], c[0], (KMAGE * rate) / pdist(c[1], c[0]));
      const t2 = interp(c[1], c[2], (KMAGE * rate) / pdist(c[1], c[2]));
      verts.push(c[0]);
      normals.push(normal(t1, c[0], 1));
      for (const t of SAMPP) {
        verts.push(bezier2(t1, c[1], t2, t));
        normals.push(pnorm(bz2Normal(t1, c[1], t2, t)));
      }
      verts.push(c[2]);
      normals.push(normal(c[2], t2, 1));
      break;
    }
    case 6: {
      const c = [
        P(keys[3], keys[4]),
        P(keys[5], keys[6]),
        P(keys[7], keys[8]),
        P(keys[9], keys[10]),
      ];
      for (const t of SAMPP) {
        verts.push(bezier3(c[0], c[1], c[2], c[3], t));
        normals.push(pnorm(bz3Normal(c[0], c[1], c[2], c[3], t)));
      }
      break;
    }
    case 7: {
      const c = [
        P(keys[3], keys[4]),
        P(keys[5], keys[6]),
        P(keys[7], keys[8]),
        P(keys[9], keys[10]),
      ];
      verts.push(c[0]);
      normals.push(normal(c[0], c[1], 1));
      for (const t of SAMPP) {
        verts.push(bezier2(c[1], c[2], c[3], t));
        normals.push(pnorm(bz2Normal(c[1], c[2], c[3], t)));
      }
      break;
    }
    default:
      return null;
  }

  return { verts, normals, edgeofs: boxOffset(verts, tips) };
}

/** 笔宽模型: 起点 d → 末端 d*k (d=15, k=0.2 → 15 → 3) */
export function boneShapeFunction(t: number, d = 15, k = 0.2): number {
  if (t > 1 || t < 0) return 0;
  return d * (1 - t) + d * k * t;
}

/** 轮廓点列 + 四边收缩标志 */
export function generateBorder(
  stro: string,
  shape: (t: number) => number = boneShapeFunction,
): { border: Pt[]; edgeofs: number[] } | null {
  const sp = strokePoint(stro);
  if (!sp || sp.verts.length === 0) return null;
  const { verts, normals, edgeofs } = sp;
  const ratio = lengthOfLine(verts);
  const total = ratio[ratio.length - 1];

  const b1: Pt[] = [];
  const b2: Pt[] = [];
  for (let i = 0; i < verts.length; i++) {
    const w = total > 0 ? shape(ratio[i] / total) : shape(0);
    b1.push(padd(verts[i], pmul(normals[i], w)));
    b2.push(psub(verts[i], pmul(normals[i], w)));
  }
  b2.reverse();
  return { border: b2.concat(b1), edgeofs };
}

/**
 * 四边收缩量: x1,y1,x2,y2 (与 edgeofs 相乘)
 *   SHRINK_OFS        —— strokic_boundary 的缺省档, 笔尖边收得多
 *   BBOX_OFS          —— ids_anal.bbox() 实际用的档 (逐笔 [10,5,10,5])
 * 两档不能混: 分配比例必须走 BBOX_OFS, 才与 Python 完全一致。
 */
export const SHRINK_OFS = [15, 10, 15, 10];
export const BBOX_OFS = [10, 5, 10, 5];

/**
 * 单笔画的包围盒
 *   ifshrink=false → 纯轮廓外接矩形 (包围容器空腔用这个)
 *   ifshrink=true  → 再把"笔尖边"乘 ofs 收掉 (左右/上下分配比例用这个)
 */
export function strokicBoundary(
  stro: string,
  ifshrink = false,
  ofs: number[] = SHRINK_OFS,
  shape: (t: number) => number = boneShapeFunction,
): Box | null {
  const g = generateBorder(stro, shape);
  if (!g || g.border.length === 0) return null;
  let x1 = 200;
  let y1 = 200;
  let x2 = 0;
  let y2 = 0;
  for (const p of g.border) {
    if (p.x < x1) x1 = p.x;
    if (p.x > x2) x2 = p.x;
    if (p.y < y1) y1 = p.y;
    if (p.y > y2) y2 = p.y;
  }
  if (x1 > x2 || y1 > y2) return null;
  if (ifshrink) {
    x1 += g.edgeofs[0] * ofs[0];
    y1 += g.edgeofs[1] * ofs[1];
    x2 -= g.edgeofs[2] * ofs[2];
    y2 -= g.edgeofs[3] * ofs[3];
  }
  return { x1, y1, x2, y2 };
}

/** 多笔画的包围盒并集 (对应 ids_anal.bbox, 逐笔 ofs=[10,5,10,5]) */
export function strokesBbox(
  strokes: string[],
  ifshrink = true,
  ofs: number[] = BBOX_OFS,
): Box | null {
  let acc: Box | null = null;
  for (const s of strokes) {
    const b = strokicBoundary(s, ifshrink, ofs);
    if (!b) continue;
    acc = acc
      ? {
          x1: Math.min(acc.x1, b.x1),
          y1: Math.min(acc.y1, b.y1),
          x2: Math.max(acc.x2, b.x2),
          y2: Math.max(acc.y2, b.y2),
        }
      : b;
  }
  return acc;
}

/** 与 ids_anal.minmax 一致 (容忍 minv/maxv 颠倒) */
export function minmax(minv: number, val: number, maxv: number): number {
  const lo = Math.min(minv, maxv);
  const hi = Math.max(minv, maxv);
  return Math.min(hi, Math.max(lo, val));
}
