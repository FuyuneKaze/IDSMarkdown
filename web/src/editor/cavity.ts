/**
 * cavity.ts —— 容器墨迹的「空腔」枚举 (移植自 scripts/cavity.py)
 *
 * 空腔 = 墨迹**补集**的连通面, 不是"最大内接空矩形"。
 *   ① inkBoxes   每笔一个障碍盒 (弯曲笔画可切开成多盒, 见 divideBoundary)
 *   ② F = 并集外框
 *   ③ x 事件竖条扫描 → 补集被切成轴对齐矩形
 *   ④ 并查集: 相邻条带共边且 y 重叠 → 同一面
 *   ⑤ 面 = 外接框 + 真实矩形列表 + 面积 + 开口边 (外接框贴到 F 的哪几条边)
 *   ⑥ rankFaces 按算符 NEED **严格**筛边 + 内接矩形质量线
 *
 * 关键语义:
 *   · 开口边判定用**面的外接框**贴着 F 的哪条边 (bbox 级近似, 不是真拓扑)
 *   · 安放盒用**面内最大内接矩形** (inscribed), 不用外接框 —— 面常是 L/U/梳形,
 *     外接框会盖住容器墨迹, 视觉上就是"腔侵入字里"
 *   · eps=0.75 只在判连通时外扩障碍 (笔尖噪声会产生 0.1px 缝, 一漏就穿)
 */

import {
  type Box,
  boneShapeFunction,
  strokePoint,
  strokicBoundary,
  SHRINK_OFS,
} from "./strokeOutline";

export type Box4 = [number, number, number, number]; // x1,y1,x2,y2
/** 面的真实形状: 条带号 + 该条带里的一段矩形 (x1,y1,x2,y2) */
export type Rect5 = [number, number, number, number, number];
export type Edge = "左" | "上" | "右" | "下";

export const STROKE_KINDS = ["1", "2", "3", "4", "6", "7"];
export const ALL_EDGES: Edge[] = ["上", "下", "左", "右"];

/** 每个包围算符要求"哪几条边必须被墨迹封住" (白式 IDS §2.1 的方向) */
export const NEED: Record<string, Edge[]> = {
  "⿴": ["上", "下", "左", "右"], // OC 全包围   囚=⿴囗人
  "⿵": ["上", "左", "右"],       // OD 上包围   冈=⿵冂乂
  "⿶": ["下", "左", "右"],       // OU 下包围   凶=⿶凵乂
  "⿷": ["上", "下", "左"],       // OR 左包围   区=⿷匚乂
  "⿸": ["上", "左"],             // RD 左上包围 仄=⿸厂人
  "⿹": ["上", "右"],             // LD 右上包围 寸=⿹𬺰丶
  "⿺": ["下", "左"],             // RU 左下包围 亾=⿺𠃊人
  "⿼": ["上", "下", "右"],       // OL 右包围   =⿼叉丶
  "⿽": ["下", "右"],             // LU 右下包围 斗=⿽十⺀
};

export interface Face {
  box: Box4;
  rects: Rect5[];
  open: Set<Edge>;
  area: number;
  cx: number;
  cy: number;
  /** 面内最大内接矩形 (唯一可当安放盒的东西), rankFaces 挂上 */
  ins?: Box4;
}

interface Pt2 { x: number; y: number }

// ---------------------------------------------------------------- 障碍盒
/** 只留直绘笔画行 (排除 99 引用与命令行) */
export function strokesOf(glyph: string): string[] {
  const out: string[] = [];
  for (const s of glyph.split("$")) {
    const t = s.trim();
    if (t && STROKE_KINDS.includes(t.split(":")[0])) out.push(t);
  }
  return out;
}

export function unionBox(boxes: Box4[]): Box4 | null {
  if (boxes.length === 0) return null;
  let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
  for (const b of boxes) {
    if (b[0] < x1) x1 = b[0];
    if (b[1] < y1) y1 = b[1];
    if (b[2] > x2) x2 = b[2];
    if (b[3] > y2) y2 = b[3];
  }
  return [x1, y1, x2, y2];
}

/**
 * 一笔画 → 切点索引列表 (n = 采样点数)。加新切法 (纵撇等) 只改这里。
 * 切点 i 表示"第 i 个采样点之后断开"; 空数组 = 不切。
 *
 * 与 scripts/stroke_outer.py 的 cut_index 逐式对齐:
 *   3/4 撇捺弯 → 采样中点一刀
 *   2   二次贝塞尔 → 中点一刀
 *   7   纵撇     → 1 之后再来一刀 (直线段与曲线段分开)
 *   6   三次贝塞尔 → 三等分两刀
 */
export function cutIndex(type: string, n: number): number[] {
  switch (type) {
    case "3":
    case "4":
    case "2":
      return [Math.floor(n / 2)];
    case "7":
      return [1, 1 + Math.floor((n - 1) / 2)];
    case "6":
      return [Math.floor(n / 3), Math.floor((2 * n) / 3)];
    default:
      return [];
  }
}

/**
 * 一笔画 → 若干盒 (按 cutIndex 切开)。对应 Python 的 divide_boundary。
 *
 * pad 必须 > 0: 两段盒只"相切"时补集会沿对角缝连通, 两个面被并成一个
 * (实测 日 的两格并成整字一个大面)。外扩方向安全 —— 盒偏大只会让腔变小/分裂。
 * 切段时不做 ifshrink (edgeofs 描述的是整笔, 套到半段没意义)。
 */
export function divideBoundary(
  stro: string,
  ifshrink = false,
  ofs: number[] = SHRINK_OFS,
  pad = 1.0,
): Box4[] {
  const g = strokePoint(stro);
  if (!g || g.verts.length === 0) return [];
  const type = stro.split(":")[0].trim();
  const cuts = cutIndex(type, g.verts.length);

  // 采样点间的累计长度 → 归一化参数, 用来取笔宽
  const cum = [0];
  for (let i = 1; i < g.verts.length; i++) {
    cum.push(cum[i - 1] + Math.hypot(g.verts[i].x - g.verts[i - 1].x, g.verts[i].y - g.verts[i - 1].y));
  }
  const total = cum[cum.length - 1] || 1;

  const b1: Pt2[][] = [];
  const b2: Pt2[][] = [];
  let seg = 0;
  for (let i = 0; i < g.verts.length; i++) {
    while (seg < cuts.length && i >= cuts[seg]) seg++;
    const w = boneShapeFunction(cum[i] / total);
    const p = g.verts[i], n = g.normals[i];
    (b1[seg] ||= []).push({ x: p.x + n.x * w, y: p.y + n.y * w });
    (b2[seg] ||= []).push({ x: p.x - n.x * w, y: p.y - n.y * w });
  }

  const nSeg = b1.length;
  const boxes: Box4[] = [];
  for (let k = 0; k < nSeg; k++) {
    if (!b1[k]) continue;
    const pts = (b2[k] || []).slice().reverse().concat(b1[k]);
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const p of pts) {
      if (p.x < x1) x1 = p.x;
      if (p.y < y1) y1 = p.y;
      if (p.x > x2) x2 = p.x;
      if (p.y > y2) y2 = p.y;
    }
    if (nSeg > 1 && pad) {
      x1 -= pad; y1 -= pad; x2 += pad; y2 += pad;
    } else if (ifshrink) {
      x1 += g.edgeofs[0] * ofs[0];
      y1 += g.edgeofs[1] * ofs[1];
      x2 -= g.edgeofs[2] * ofs[2];
      y2 -= g.edgeofs[3] * ofs[3];
    }
    boxes.push([x1, y1, x2, y2]);
  }
  return boxes;
}

/** 单笔画的盒列表 (split=true 走切段, 否则一笔一盒) */
export function strokeBoxes(stro: string, shrink = false, split = true): Box4[] {
  if (split) return divideBoundary(stro, shrink);
  const b: Box | null = strokicBoundary(stro, shrink);
  return b ? [[b.x1, b.y1, b.x2, b.y2]] : [];
}

/**
 * 字形/笔画表 → 障碍盒表。
 * 退化盒 (宽或高为 0) 不算障碍 —— "没面积就不挡路", 与旧路径同一规则。
 */
export function inkBoxes(src: string | string[], shrink = false, split = true): Box4[] {
  const strokes = typeof src === "string" ? strokesOf(src) : src;
  const out: Box4[] = [];
  for (const s of strokes) {
    for (const b of strokeBoxes(s, shrink, split)) {
      if (b[2] > b[0] && b[3] > b[1]) out.push(b);
    }
  }
  return out;
}

// ---------------------------------------------------------------- 补集的面
export function faces(
  src: string | string[],
  eps = 0.75,
  minSide = 5.0,
  split = true,
): { faces: Face[]; outer: Box4 | null } {
  const boxes = inkBoxes(src, false, split);
  const outer = unionBox(boxes);
  if (!outer || outer[2] - outer[0] <= 0 || outer[3] - outer[1] <= 0) {
    return { faces: [], outer };
  }
  const F = outer;
  // eps 只在判连通/封边时外扩障碍; 面积与位置仍用原始盒
  const sealed = boxes.map((b) => [b[0] - eps, b[1] - eps, b[2] + eps, b[3] + eps]);

  // x 事件点: 外框两边 + 每个障碍的两条竖边 (贴外框的去掉)
  const xset = new Set<number>([F[0], F[2]]);
  for (const b of sealed) {
    for (const v of [b[0], b[2]]) {
      if (F[0] + 1e-9 < v && v < F[2] - 1e-9) xset.add(v);
    }
  }
  const xs = [...xset].sort((a, b) => a - b);

  const rects: Rect5[] = [];
  for (let strip = 0; strip < xs.length - 1; strip++) {
    const xa = xs[strip], xb = xs[strip + 1];
    if (xb - xa <= 1e-9) continue;
    const spans: [number, number][] = [];
    for (const b of sealed) {
      if (b[0] < xb - 1e-9 && b[2] > xa + 1e-9) spans.push([b[1], b[3]]);
    }
    spans.sort((p, q) => p[0] - q[0]);
    let cur = F[1];
    for (const [y1, y2] of spans) {
      if (y1 > cur + 1e-9) rects.push([strip, xa, cur, xb, Math.min(y1, F[3])]);
      cur = Math.max(cur, y2);
      if (cur >= F[3] - 1e-9) break;
    }
    if (cur < F[3] - 1e-9) rects.push([strip, xa, cur, xb, F[3]]);
  }

  // 并查集: 只有相邻条带 (号差 1) 共边且 y 重叠才算连通
  const parent = rects.map((_, i) => i);
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]];
      i = parent[i];
    }
    return i;
  };
  const byStrip = new Map<number, number[]>();
  rects.forEach((r, i) => {
    const a = byStrip.get(r[0]);
    if (a) a.push(i);
    else byStrip.set(r[0], [i]);
  });
  rects.forEach((r, i) => {
    for (const j of byStrip.get(r[0] + 1) || []) {
      const g = rects[j];
      if (Math.abs(g[1] - r[3]) < 1e-6 && Math.min(r[4], g[4]) - Math.max(r[2], g[2]) > 1e-6) {
        const ri = find(i), rj = find(j);
        if (ri !== rj) parent[rj] = ri;
      }
    }
  });

  const groups = new Map<number, Rect5[]>();
  rects.forEach((r, i) => {
    const root = find(i);
    const a = groups.get(root);
    if (a) a.push(r);
    else groups.set(root, [r]);
  });

  const out: Face[] = [];
  for (const group of groups.values()) {
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const r of group) {
      if (r[1] < x1) x1 = r[1];
      if (r[2] < y1) y1 = r[2];
      if (r[3] > x2) x2 = r[3];
      if (r[4] > y2) y2 = r[4];
    }
    if (x2 - x1 < minSide || y2 - y1 < minSide) continue;
    const t = 1e-6;
    const open = new Set<Edge>();
    if (x1 <= F[0] + t) open.add("左");
    if (y1 <= F[1] + t) open.add("上");
    if (x2 >= F[2] - t) open.add("右");
    if (y2 >= F[3] - t) open.add("下");
    let area = 0;
    for (const r of group) area += (r[3] - r[1]) * (r[4] - r[2]);
    out.push({ box: [x1, y1, x2, y2], rects: group, open, area, cx: (x1 + x2) / 2, cy: (y1 + y2) / 2 });
  }
  return { faces: out, outer };
}

// ---------------------------------------------------------------- 内接矩形
/**
 * 面 (轴对齐矩形列表) 里**最大的内接矩形**。
 *
 * 面由竖条扫描得到, 一个 100% 填充的矩形面天然被切成几条竖带 —— 所以不能要求
 * "某个矩形单独覆盖整个 x 区间" (老写法, 会只拿到半条竖带)。正确做法是按 x 切片,
 * 一个跨多切片的 x 区间可用的 y 段 = 各切片 y 段的**交集**。
 */
export function inscribed(rects: Rect5[]): Box4 | null {
  if (rects.length === 0) return null;

  const unionRuns = (pairs: [number, number][]): [number, number][] => {
    const out: [number, number][] = [];
    for (const [y1, y2] of pairs.slice().sort((p, q) => p[0] - q[0])) {
      const last = out[out.length - 1];
      if (last && y1 <= last[1] + 1e-9) last[1] = Math.max(last[1], y2);
      else out.push([y1, y2]);
    }
    return out;
  };
  const isectRuns = (A: [number, number][], B: [number, number][]): [number, number][] => {
    const out: [number, number][] = [];
    for (const [a1, a2] of A) {
      for (const [b1, b2] of B) {
        const lo = Math.max(a1, b1), hi = Math.min(a2, b2);
        if (hi > lo + 1e-9) out.push([lo, hi]);
      }
    }
    return unionRuns(out);
  };

  const xset = new Set<number>();
  for (const r of rects) { xset.add(r[1]); xset.add(r[3]); }
  const xs = [...xset].sort((a, b) => a - b);
  if (xs.length < 2) return null;

  const cov: [number, number][][] = [];
  for (let k = 0; k < xs.length - 1; k++) {
    const xa = xs[k], xb = xs[k + 1];
    const pairs: [number, number][] = [];
    for (const r of rects) {
      if (r[1] <= xa + 1e-9 && r[3] >= xb - 1e-9) pairs.push([r[2], r[4]]);
    }
    cov.push(unionRuns(pairs));
  }

  let best: Box4 | null = null;
  let bestArea = -1;
  for (let k = 0; k < cov.length; k++) {
    if (cov[k].length === 0) continue;
    let acc = cov[k];
    for (let m = k; m < cov.length; m++) {
      if (m > k) {
        acc = isectRuns(acc, cov[m]);
        if (acc.length === 0) break;
      }
      let y1 = acc[0][0], y2 = acc[0][1];
      for (const [a, b] of acc) if (b - a > y2 - y1) { y1 = a; y2 = b; }
      const area = (xs[m + 1] - xs[k]) * (y2 - y1);
      if (area > bestArea) {
        bestArea = area;
        best = [xs[k], y1, xs[m + 1], y2];
      }
    }
  }
  return best;
}

// ---------------------------------------------------------------- 筛选与排序
const vOverlap = (a: Face, b: Face): number => {
  const lo = Math.max(a.box[1], b.box[1]);
  const hi = Math.min(a.box[3], b.box[3]);
  const shorter = Math.min(a.box[3] - a.box[1], b.box[3] - b.box[1]);
  return shorter > 0 ? (hi - lo) / shorter : 0;
};

/** 白式 IDS §6.6 的序号: 从上到下分行, 行内从左到右 */
function orderFaces(fs: Face[], rowOverlap = 0.5): Face[] {
  const rows: Face[][] = [];
  for (const f of fs.slice().sort((a, b) => a.cy - b.cy || a.cx - b.cx)) {
    let placed = false;
    for (const row of rows) {
      if (row.some((g) => vOverlap(f, g) > rowOverlap)) {
        row.push(f);
        placed = true;
        break;
      }
    }
    if (!placed) rows.push([f]);
  }
  const out: Face[] = [];
  for (const row of rows) {
    row.sort((a, b) => a.cx - b.cx);
    out.push(...row);
  }
  return out;
}

/**
 * 按算符要求**严格**筛边 → 挂上安放盒 → 按 §6.6 排序
 *
 * 严格 = 要求封闭的边必须全封住, 不搞"允许差一条"的放宽。放宽会把外部面
 * (辶: 开口=上/右/左) 拉进来又因面积最大被选中, 反而更差。给空时调用方退回老做法。
 */
export function rankFaces(fs: Face[], op: string, minW = 20.0, minH = 20.0): Face[] {
  const need = NEED[op];
  if (!need) return [];
  const out: Face[] = [];
  for (const f of fs) {
    if (!need.every((e) => !f.open.has(e))) continue;
    const ins = inscribed(f.rects);
    if (!ins || ins[2] - ins[0] < minW || ins[3] - ins[1] < minH) continue;
    out.push({ ...f, ins });
  }
  return orderFaces(out);
}

export function cavityList(strokes: string | string[], op: string): Face[] {
  return rankFaces(faces(strokes).faces, op);
}

/**
 * 安放盒的选择链 (与 ids_anal.surround 一致):
 *   ① 通过 NEED 的候选里, 内接矩形面积最大者
 *   ② 没有候选 → 最大的面 (不管开口) 的内接矩形
 *   ③ 连面都没有 → null (调用方保留老做法)
 * ② 之所以存在: 面按构造不含墨迹, 而"最大内接空矩形"会真的压到笔画上。
 */
export function pickCavity(
  strokeSrc: string | string[],
  op: string,
): { cavity: Box4 | null; candidates: Box4[]; outer: Box4 | null } {
  const { faces: fs, outer } = faces(strokeSrc);
  const cands = rankFaces(fs, op);
  const candidates = cands.map((f) => f.box);
  if (cands.length > 0) {
    let best = cands[0];
    let bestArea = -1;
    for (const f of cands) {
      const ins = f.ins!;
      const a = (ins[2] - ins[0]) * (ins[3] - ins[1]);
      if (a > bestArea) { bestArea = a; best = f; }
    }
    return { cavity: best.ins!, candidates, outer };
  }
  if (fs.length > 0) {
    let big = fs[0];
    for (const f of fs) if (f.area > big.area) big = f;
    return { cavity: inscribed(big.rects) ?? big.box, candidates, outer };
  }
  return { cavity: null, candidates, outer };
}
