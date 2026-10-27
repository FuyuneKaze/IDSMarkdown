/**
 * compose.ts —— 包围结构 (⿴⿵⿶⿷⿸⿹⿺⿼⿽) 的合成流程
 *
 * 移植自 scripts/ids_anal.py 的 surround + fit_into，以及 glyph_extend.trans
 * 在 "dp=(0,0)" 情形下退化成的那一步**线性重映射**。
 *
 * 流程:
 *  ① 容器笔画 → cavity.pickCavity(op) 得到安放盒 (面内最大内接矩形)
 *  ② 内部件外框 ibb1 (收缩档) 与中宫盒 ibb2 (×2) 插值 → 基准盒 basis
 *  ③ fit_into: 基准盒 → 空腔, 得到 trans 的目标矩形
 *  ④ 把内部件每个控制点按目标矩形线性重映射, 与容器拼起来
 *
 * 为什么基准盒要两个算法插值: 中宫盒反映"墨量分布"(适合判断该占多大),
 * 而收缩外框反映"部件的真实边界"(不会把笔画撑出格子); 各取一半比任一单独用都稳。
 *
 * 注意 ①: 目标矩形在 Python 里是 `int(x)` **截断**后才用的, 这里保持同样语义,
 *        否则与 Python 版会有亚像素级的系统性偏移。
 * 注意 ②: 数据缺失时返回 null, 由调用方决定回退 (web 端不再有 max_empty_rect,
 *        这一步留给调用方或后续移植)。
 */

import type { Box } from "./strokeOutline";
import {
  type Box4,
  inkBoxes,
  pickCavity,
  strokesOf,
  unionBox,
} from "./cavity";
import { boxMap, centralBox, lerpBox } from "./centralBox";

/** ids_anal.fit_into 的默认阈值 (小部件保留设计留白) */
export const FIT_LO = 10;
export const FIT_HI = 190;

/**
 * 基准盒 → trans 的目标矩形 (ids_anal.fit_into)
 *
 * trans 的映射是  x' = R.x1 + (x/200)*(R.x2-R.x1)
 * 要的就是"把**基准盒**映射到空腔 rect 上", 于是
 *     W = 200*rect.w/basis.w,  A = rect.x1 - basis.x0/200*W
 *
 * useBbox=true: 无视 [lo,hi], 一律用基准盒 (中宫盒常常整块落在 [10,190] 内,
 *   走默认分支会被完全无视 —— 实测 (77.8,75.6)-(114.2,135.0) 和旧的
 *   (54.9,50.0)-(140.3,153.8) 会得到同一个结果, 缩放白算)。
 */
export function fitInto(basis: Box4, rect: Box4, useBbox = true): Box | null {
  let sx0: number, sx1: number, sy0: number, sy1: number;
  if (useBbox) {
    sx0 = basis[0]; sx1 = basis[2];
    sy0 = basis[1]; sy1 = basis[3];
  } else {
    sx0 = basis[0] < FIT_LO || basis[2] > FIT_HI ? basis[0] : FIT_LO;
    sx1 = basis[0] < FIT_LO || basis[2] > FIT_HI ? basis[2] : FIT_HI;
    sy0 = basis[1] < FIT_LO || basis[3] > FIT_HI ? basis[1] : FIT_LO;
    sy1 = basis[1] < FIT_LO || basis[3] > FIT_HI ? basis[3] : FIT_HI;
  }
  if (sx1 <= sx0 || sy1 <= sy0) return null;
  const W = (200 * (rect[2] - rect[0])) / (sx1 - sx0);
  const H = (200 * (rect[3] - rect[1])) / (sy1 - sy0);
  const A = rect[0] - (sx0 / 200) * W;
  const B = rect[1] - (sy0 / 200) * H;
  return { x1: A, y1: B, x2: A + W, y2: B + H };
}

/**
 * 目标矩形 → 把笔画控制点从 0-200 空间线性重映射 (glyph_extend.trans 的 dp=(0,0) 分支)
 * 非笔画行 (99 引用 / 0:9x 命令) 原样保留。
 */
export function transformStrokes(strokes: string[], target: Box): string[] {
  // Python: x1,y1,x2,y2 = [int(x) for x in glyph[0]]  → 截断
  const x1 = Math.trunc(target.x1);
  const y1 = Math.trunc(target.y1);
  const x2 = Math.trunc(target.x2);
  const y2 = Math.trunc(target.y2);
  const w = x2 - x1;
  const h = y2 - y1;

  return strokes.map((stro) => {
    const p = stro.split(":");
    const t = p[0];
    if (!["1", "2", "3", "4", "6", "7"].includes(t)) return stro;
    for (let i = 3; i + 1 < p.length; i += 2) {
      const x = parseFloat(p[i]);
      const y = parseFloat(p[i + 1]);
      p[i] = String((x / 200) * w + x1);
      p[i + 1] = String((y / 200) * h + y1);
    }
    return p.join(":");
  });
}

export interface SurroundPlan {
  op: string;
  /** 容器墨迹外框 */
  outer: Box4 | null;
  /** 通过 NEED 的候选面 (逐个用外接框表示, 给预览用) */
  candidates: Box4[];
  /** 选中的安放盒 (面内最大内接矩形) */
  cavity: Box4 | null;
  /** 内部件收缩外框 */
  ibb1: Box4 | null;
  /** 内部件中宫盒 ×2 */
  ibb2: Box4 | null;
  /** 实际当基准用的盒 (ibb1 / ibb2 插值) */
  basis: Box4 | null;
  /** trans 用的目标矩形 */
  target: Box | null;
}

/**
 * 笔画数 → 两套盒的混合比例 (对应 ids_anal.stronummap)
 *
 * 注意 `^` 在 Python 里是**按位异或**不是乘方, 原实现就是 `x^2`;
 * 这里保持一致 (否则 alpha 与 Python 不同, basis 会对不上)。
 */
export function stronummap(x: number): number {
  const v = Math.max(0, x);
  const q = v ^ 2;
  return q / (q + 16);
}

/**
 * 算出包围合成的全部中间结果 (不拼接, 便于预览画框 / 调试)
 *
 * 与 Python 侧 surround 逐式对齐的三处细节 (都是对拍时抓出来的):
 *   ① ibb1 走**一笔一盒** (strokic_box + shrink), 不是切分后的多盒
 *   ② boxMap 的中心用**盒自身的中心**, 不是骨架重心
 *      —— 用重心会把不对称部件甩出画布 / 压成一条线
 *   ③ 插值比例 alpha 由内部件笔画数决定 (stronummap), 不是固定 0.5
 *
 * @param containerStrokes 容器笔画 (已 unfold 成直绘笔画)
 * @param innerStrokes     内部件笔画 (同上, 应在 0-200 空间)
 */
export function surroundPlan(
  op: string,
  containerStrokes: string[],
  innerStrokes: string[],
): SurroundPlan {
  const { cavity, candidates, outer } = pickCavity(containerStrokes, op);

  const ibb1 = unionBox(inkBoxes(innerStrokes, true, false));
  const cb = centralBox(innerStrokes, 1, true);
  const ibb2 = cb
    ? boxMap(cb.box, [(cb.box[0] + cb.box[2]) / 2, (cb.box[1] + cb.box[3]) / 2], 2)
    : null;
  const alpha = stronummap(2 * innerStrokes.length - 2);
  const basis = ibb1 && ibb2 ? lerpBox(ibb1, ibb2, alpha) : ibb1 ?? ibb2;
  const target = basis && cavity ? fitInto(basis, cavity, true) : null;

  return { op, outer, candidates, cavity, ibb1, ibb2, basis, target };
}

/**
 * 包围合成: 容器笔画 + 已重映射的内部件笔画 → 合成后的 KAGE 笔画串
 * 内部件没腔 / 没基准盒 / 目标矩形非法时返回 null (调用方自己决定怎么退)
 */
export function composeSurround(
  op: string,
  containerStrokes: string[],
  innerStrokes: string[],
): { data: string; plan: SurroundPlan } | null {
  const plan = surroundPlan(op, containerStrokes, innerStrokes);
  if (!plan.target) return null;
  const moved = transformStrokes(innerStrokes, plan.target);
  return { data: containerStrokes.concat(moved).join("$"), plan };
}

/** 便利: 从整段 KAGE 数据串直接合成 (先取出直绘笔画) */
export function composeSurroundData(
  op: string,
  containerData: string,
  innerData: string,
): { data: string; plan: SurroundPlan } | null {
  return composeSurround(op, strokesOf(containerData), strokesOf(innerData));
}
