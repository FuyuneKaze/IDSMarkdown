import { glyphBase } from "./assetUrl";
/**
 * KAGE 引擎 — 从 C++ KageJsRenderer.cpp 移植
 *
 * 职责:
 * 1. 管理字形数据 (从 core_glyphs.json 加载)
 * 2. IDS → type-99 KAGE 复合构建 (buildComposite)
 * 3. 变体选择 (selectLeafVariant)
 * 4. IDS → SVG 渲染 (renderSvg)
 *
 * 依赖: kage-bundle.js 全局函数 (loadGlyph, renderGlyph, clearGlyphs, getGlyphBox, getGlyphData)
 */

import { codePointAt, cpLen, isIdsOperator, isSurroundOp } from "./charUtils";
import { minmax, strokesBbox } from "./strokeOutline";
import { surroundPlan } from "./compose";
import type { SurroundPlan } from "./compose";
import { GlyphSource, guessGlyphNames } from "./glyphSource";
import type { GlyphSourceOptions } from "./glyphSource";

// ============================================================
// 类型定义
// ============================================================

interface BBox {
  x1: number; y1: number; x2: number; y2: number;
}

interface Rect {
  x1: number; y1: number; x2: number; y2: number;
}

interface ChildInfo {
  name: string;
  x1: number; y1: number;
  x2: number; y2: number;
  /** 旋转: a3 = 四分之一圈计数 (1=90°, 2=180°, 3=270°); 0 = 不转 */
  rot: number;
  /** 镜像: 1 = 发 0:98 命令 (左右镜像) */
  flip: number;
}

interface CompositeResult {
  rootName: string;
  data: string;
}

// ============================================================
// BBox 辅助函数 (从 C++ BBox 结构体移植)
// ============================================================

function makeBBox(): BBox {
  return { x1: 200, y1: 200, x2: 0, y2: 0 };
}

function bboxValid(bb: BBox): boolean {
  return bb.x1 <= bb.x2 && bb.y1 <= bb.y2;
}

function expandBBox(bb: BBox, x: number, y: number): void {
  if (x < bb.x1) bb.x1 = x;
  if (x > bb.x2) bb.x2 = x;
  if (y < bb.y1) bb.y1 = y;
  if (y > bb.y2) bb.y2 = y;
}

// ============================================================
// 变体选择 — positionChain + scoreVariantBbox (C++ 427-471)
// ============================================================

/**
 * 叶子变体后缀 —— 与 ids_anal.IDS 的取法一致
 *   ⿰ 左右: 左 -01, 右 -02      ⿱ 上下: 上 -03, 下 -04
 *   ⿲ 左中右: -01/-01/-02       ⿳ 上中下: -03/-03/-04
 */
function leafSuffix(opCp: number, position: number): string {
  switch (opCp) {
  case 0x2FF0: return position === 0 ? "-01" : "-02";
  case 0x2FF1: return position === 0 ? "-03" : "-04";
  case 0x2FF2: return position <= 1 ? "-01" : "-02";
  case 0x2FF3: return position <= 1 ? "-03" : "-04";
  // 包围算符: 容器取 -05 (外框变体), 内部件取 -06 (内容物变体)。
  // 与 ids_anal.surround 的 return_bone(args[0]+"-05") / (args[1]+"-06") 一致;
  // 库里没有该后缀时 selectLeafVariant 会退化到本体 (与 get_data 的子串回退等价)。
  case 0x2FF4: case 0x2FF5: case 0x2FF6: case 0x2FF7: case 0x2FF8:
  case 0x2FF9: case 0x2FFA: case 0x2FFC: case 0x2FFD:
    return position === 0 ? "-05" : "-06";
  default: return "";
  }
}

/**
 * 组件矩形分配 (⿰ ⿱ ⿲ ⿳) —— 与 ids_anal.IDS 的分配部分逐式一致
 *
 * 提成纯函数是为了可验证: 用 Python 端 spy 到的 trans 矩形直接对照。
 * 包围算符仍走 surroundRects (尚未移植)。
 */
export function layoutRects(opCp: number, boxes: BBox[]): Rect[] {
  const at = (i: number): BBox => boxes[i] ?? makeBBox();
  // 宽只由 x 决定, 高只由 y 决定 —— Python 端就是 b[2]-b[0] / b[3]-b[1],
  // 不做"整盒有效"判定: 空盒(200,200,0,0)差值为负, 经 minmax 自然落到 5。
  const wOf = (b: BBox) => minmax(5, b.x2 - b.x1, 195);
  const hOf = (b: BBox) => minmax(5, b.y2 - b.y1, 195);
  /**
   * 后件的那条边: 200 - 200*(200-split)/(200-max(1,前件外沿))
   *
   * 含义是「让后件的内容外沿正好落在 split 分界上」。分母为 0 只在
   * 前件外沿恰为 200 时出现 (空盒 (200,200,0,0) 就是), Python 到此直接
   * ZeroDivisionError 崩掉; 这里退化成 split 本身 —— 后件从分界处起排,
   * 与"前件占满整幅"的直觉一致, 也保证矩形有限。
   */
  const backEdge = (split: number, x: number): number => {
    const d = 200 - Math.max(1, x);
    return d !== 0 ? 200 - (200 * (200 - split)) / d : split;
  };

  switch (opCp) {
  case 0x2FF0: { // ⿰ 左右
    const b1 = at(0);
    const b2 = at(1);
    const w1 = wOf(b1);
    const w2 = wOf(b2);
    const split = minmax(5, 3 + (197 * w1) / (w1 + w2), 195);

    const leftbound = (split * 200) / Math.max(b1.x2, 1);
    const rightbound = backEdge(split, b2.x1);
    return [
      { x1: 0, y1: 0, x2: leftbound, y2: 200 },
      { x1: rightbound, y1: 0, x2: 200, y2: 200 },
    ];
  }
  case 0x2FF1: { // ⿱ 上下
    const b1 = at(0);
    const b2 = at(1);
    const h1 = hOf(b1);
    const h2 = hOf(b2);
    const split = minmax(5, 3 + (197 * h1) / (h1 + h2), 195);

    const bottombound = (split * 200) / Math.max(b1.y2, 1);
    const topbound = backEdge(split, b2.y1);
    return [
      { x1: 0, y1: 0, x2: 200, y2: bottombound },
      { x1: 0, y1: topbound, x2: 200, y2: 200 },
    ];
  }
  case 0x2FF2: { // ⿲ 左中右
    const b1 = at(0);
    const b2 = at(1);
    const b3 = at(2);
    const w1 = wOf(b1);
    const w2 = wOf(b2);
    const w3 = wOf(b3);
    const sum = w1 + w2 + w3;
    const s1 = minmax(2, 1 + (199 * w1) / sum, 90);
    const s2 = minmax(110, 199 - (199 * w3) / sum, 198);

    const leftbound = (s1 * 200) / Math.max(b1.x2, 1);
    const rightbound = backEdge(s2, b3.x1);
    // Python 端此处 ZeroDivisionError; 给 0 兜底 (中件不额外扩张)
    const span = b2.x2 - b2.x1;
    const kc = span > 1e-9 ? (s2 - s1) / span : 0;
    return [
      { x1: 0, y1: 0, x2: leftbound, y2: 200 },
      { x1: s1 - b2.x1 * kc, y1: 0, x2: s2 + (200 - b2.x2) * kc, y2: 200 },
      { x1: rightbound, y1: 0, x2: 200, y2: 200 },
    ];
  }
  case 0x2FF3: { // ⿳ 上中下
    const b1 = at(0);
    const b2 = at(1);
    const b3 = at(2);
    const h1 = hOf(b1);
    const h2 = hOf(b2);
    const h3 = hOf(b3);
    const sum = h1 + h2 + h3;
    const s1 = minmax(2, 1 + (199 * h1) / sum, 90);
    const s2 = minmax(110, 199 - (199 * h3) / sum, 198);

    const topbound = (s1 * 200) / Math.max(b1.y2, 1);
    const bottombound = backEdge(s2, b3.y1);
    const span = b2.y2 - b2.y1;
    const kc = span > 1e-9 ? (s2 - s1) / span : 0;
    return [
      { x1: 0, y1: 0, x2: 200, y2: topbound },
      { x1: 0, y1: s1 - b2.y1 * kc, x2: 200, y2: s2 + (200 - b2.y2) * kc },
      { x1: 0, y1: bottombound, x2: 200, y2: 200 },
    ];
  }
  default: // ⿻ 及其它: 全重叠
    return boxes.map(() => ({ x1: 0, y1: 0, x2: 200, y2: 200 }));
  }
}

// 预留: 变体后缀优先级链 + bbox 破平局评分。
// 现已改用 ids_anal 的固定后缀 (leafSuffix) 以与 Python 端产出一致,
// 这两个保留备用 (将来若要开启"更激进的变体搜索"可接回 selectLeafVariant)。
export function positionChain(position: number, opCp: number): string[] {
  if (isSurroundOp(opCp)) {
    if (position === 0)
      return ["05", "10", "15", ""];
    else
      return ["06", ""];
  }
  switch (opCp) {
  case 0x2FF0: // ⿰
    return (position === 0) ? ["01", "08", "07", ""]
                            : ["02", "08", "07", ""];
  case 0x2FF1: // ⿱
    return (position === 0) ? ["03", "09", "07", ""]
                            : ["04", "14", "24", "09", "07", ""];
  case 0x2FF2: // ⿲
    return (position <= 1) ? ["01", "08", "07", ""]
                           : ["02", "08", "07", ""];
  case 0x2FF3: // ⿳
    return (position <= 1) ? ["03", "09", "07", ""]
                           : ["04", "14", "24", "09", "07", ""];
  default:
    return [""];
  }
}

export function scoreVariantBbox(bb: BBox, position: number, opCp: number): number {
  if (!bboxValid(bb)) return 0;
  const w = Math.max(bb.x2 - bb.x1, 1);
  const h = Math.max(bb.y2 - bb.y1, 1);

  let dirFit = 0.5;
  if (opCp === 0x2FF0)
    dirFit = (position === 0) ? bb.x2 / 200.0 : (200.0 - bb.x1) / 200.0;
  else if (opCp === 0x2FF1)
    dirFit = (position === 0) ? bb.y2 / 200.0 : (200.0 - bb.y1) / 200.0;

  const area = w * h;
  const aspect = w / h;
  const aspectScore = (aspect > 1.0) ? (1.0 / aspect) : aspect;
  const areaScore = Math.min(area / 15000.0, 1.0);

  return dirFit * 0.3 + areaScore * 0.3 + aspectScore * 0.4;
}

// ============================================================
// KageEngine 类
// ============================================================

export class KageEngine {
  private glyphData = new Map<string, string>();    // name → KAGE 数据
  private charToName = new Map<string, string>();   // 字符 → uXXXX 字形名 (用于搜索)
  private bboxCache = new Map<string, BBox>();       // 边界框缓存
  // private cboxCache = new Map<string, BBox>();    // CBox 缓存 (与 getCbox/computeCbox 配套, 预留)
  private idsToSvg = new Map<string, string>();     // IDS → SVG 缓存
  private glyphCounter = 0;
  private _ready = false;
  /** 远程字形来源 (core_glyphs.json 缺失时按需走 GlyphWiki API) */
  private source: GlyphSource | null = null;
  /** 正在预取的 IDS 串 (去重, 避免渲染循环里反复排预取) */
  private prefetching = new Set<string>();

  get ready(): boolean { return this._ready; }

  /** 按名称查找部件的 KAGE 源数据 (kage-editor get-source 用) */
  getGlyphSource(name: string): string | null {
    // 先查内部缓存
    if (this.glyphData.has(name)) return this.glyphData.get(name)!;
    // 再尝试剥离 @N 后缀
    const atIdx = name.indexOf('@');
    if (atIdx > 0) {
      const base = name.substring(0, atIdx);
      return this.glyphData.get(base) || null;
    }
    return null;
  }

  /** 搜索部件名 (kage-editor search 用), 返回 tab 分隔的名字列表 */
  searchGlyphNames(query: string, maxResults: number = 200): string {
    const matches: string[] = [];
    const lower = query.toLowerCase();

    // 1. 汉字转 u+hex 前缀匹配 (向 C++ 看齐)
    for (const ch of query) {
      const cp = ch.codePointAt(0);
      if (cp && cp > 0x7F) {  // 非 ASCII 字符才做 hex 前缀匹配
        const prefix = "u" + cp.toString(16);
        for (const name of this.glyphData.keys()) {
          if (name.startsWith(prefix) && !matches.includes(name)) {
            matches.push(name);
            if (matches.length >= maxResults) break;
          }
        }
      }
    }

    // 2. 按字形名子串搜索
    for (const name of this.glyphData.keys()) {
      if (name.toLowerCase().includes(lower)) {
        if (!matches.includes(name)) {
          matches.push(name);
          if (matches.length >= maxResults) break;
        }
      }
    }
    return matches.join('\t');
  }

  /** 渲染原始 KAGE 笔画数据为 SVG */
  renderKageData(kageData: string): string | null {
    if (!this._ready || !kageData) return null;

    clearGlyphs();
    this.bboxCache.clear();
    const name = "_kage_direct";
    loadGlyph(name, kageData);
    // 解析 99: 引用依赖 (否则引用部件的 glyph 没有轮廓)
    const loaded = new Set<string>();
    loaded.add(name);
    this.resolveDeps(kageData, loaded);
    const svg = renderGlyph(name, false);
    if (!svg) return null;
    return svg.replace(/fill="black"/g, 'fill="#ffffff"');
  }

  // ============================================================
  // 数据加载
  // ============================================================

  /** 加载 core_glyphs.json 到内存 */
  async loadCoreGlyphs(): Promise<void> {
    try {
      const json = await this.fetchBundle<{ glyphs?: Record<string, string> }>(
        glyphBase() + "core_glyphs.json",
        glyphBase() + "core_glyphs.json.gz",
      );
      const glyphs = json.glyphs as Record<string, string>;
      for (const [name, data] of Object.entries(glyphs)) {
        this.glyphData.set(name, data);
        this.source?.put(name, data);
        // 构建字符 → 字形名反向索引 (用于搜索)
        if (name.length >= 2 && (name[0] === 'u' || name[0] === 'U')) {
          const cp = parseInt(name.substring(1), 16);
          if (!isNaN(cp) && cp > 0 && cp <= 0x10FFFF) {
            const char = String.fromCodePoint(cp);
            if (!this.charToName.has(char)) {
              this.charToName.set(char, name);
            }
          }
        }
      }
      this._ready = true;
      console.log(`[KageEngine] loaded ${this.glyphData.size} core glyphs`);
    } catch (e) {
      // core_glyphs.json 不存在/太大没带上是**正常部署形态**: 只要开了远程兜底,
      // 引擎仍然可用 (按需从 GlyphWiki 取), 所以这里不再让 _ready 卡死。
      console.warn("[KageEngine] core glyphs unavailable:", e);
      if (this.source) this._ready = true;
    }
  }

  // ============================================================
  // 远程字形兜底 (bundled → 缓存 → GlyphWiki API)
  // ============================================================

  /**
   * 打开远程兜底。必须在渲染前调用一次。
   *
   * 渲染是同步的, 所以取数据发生在渲染**之前**: 调用方先 await `ensureGlyphs(...)`,
   * 再同步调用 renderIdsGlyph/renderKageData。
   */
  enableRemoteFallback(opts: GlyphSourceOptions = {}): GlyphSource {
    const src = new GlyphSource({ ...opts, onGlyph: (n, d) => this.addGlyph(n, d) });
    for (const [name, data] of this.glyphData) src.put(name, data);
    this.source = src;
    this._ready = true;
    return src;
  }

  /** 外部注入一个字形的 KAGE 数据 (远程取回 / 用户导入都走这里) */
  addGlyph(name: string, data: string): void {
    if (!name || !data) return;
    this.glyphData.set(name, data);
    this.bboxCache.delete("sk:" + name);   // 旧盒可能是在字形未加载时算的空盒
    this.source?.put(name, data);
    loadGlyph(name, data);
    if (name.length >= 2 && (name[0] === 'u' || name[0] === 'U')) {
      const cp = parseInt(name.substring(1), 16);
      if (!isNaN(cp) && cp > 0 && cp <= 0x10FFFF) {
        const char = String.fromCodePoint(cp);
        if (!this.charToName.has(char)) this.charToName.set(char, name);
      }
    }
  }

  /** 把 names 里还缺的字形从远程补齐; 返回失败名单 */
  async ensureGlyphs(names: string[]): Promise<string[]> {
    if (!this.source) return names;
    const r = await this.source.ensure(names);
    return r.failed;
  }

  // ============================================================
  // 边界框计算 (从 C++ computeBbox/computeCbox 移植)
  // ============================================================

  /** 从 KAGE 数据计算边界框 (递归展开 type-99) */
  private computeBbox(data: string, visited: Set<string> = new Set()): BBox {
    const bbox = makeBBox();
    if (!data) return bbox;

    const strokes = data.split("$");
    for (const s of strokes) {
      const stroke = s.trim();
      if (!stroke) continue;

      const parts = stroke.split(":");
      if (parts.length < 4) continue;

      const kind = parseInt(parts[0], 10);
      if (isNaN(kind)) continue;

      if (kind === 99 && parts.length >= 8) {
        let refName = parts[7];
        const atIdx = refName.indexOf("@");
        const base = atIdx > 0 ? refName.substring(0, atIdx) : refName;

        if (!visited.has(base) && this.glyphData.has(base)) {
          visited.add(base);
          const refBox = this.computeBbox(this.glyphData.get(base)!, visited);
          if (bboxValid(refBox)) {
            const rx1 = parseInt(parts[3], 10);
            const ry1 = parseInt(parts[4], 10);
            const rx2 = parseInt(parts[5], 10);
            const ry2 = parseInt(parts[6], 10);
            expandBBox(bbox,
              rx1 + (rx2 - rx1) * refBox.x1 / 200,
              ry1 + (ry2 - ry1) * refBox.y1 / 200);
            expandBBox(bbox,
              rx1 + (rx2 - rx1) * refBox.x2 / 200,
              ry1 + (ry2 - ry1) * refBox.y2 / 200);
          }
        }
      } else {
        for (let i = 3; i + 1 < parts.length; i += 2) {
          const x = parseInt(parts[i], 10);
          const y = parseInt(parts[i + 1], 10);
          if (!isNaN(x) && !isNaN(y))
            expandBBox(bbox, x, y);
        }
      }
    }
    return bbox;
  }

  // 预留: 计算内接盒 (CBox — 向中心收缩, 用于包围组件; 与 getCbox/cboxCache 配套, 恢复时取消注释)
  // private computeCbox(data: string, cx: number, cy: number, visited: Set<string> = new Set()): BBox {
  //   const cbox: BBox = { x1: 0, y1: 0, x2: 200, y2: 200 };
  //   if (!data) return cbox;

  //   const strokes = data.split("$");
  //   for (const s of strokes) {
  //     const stroke = s.trim();
  //     if (!stroke) continue;

  //     const parts = stroke.split(":");
  //     if (parts.length < 4) continue;

  //     const kind = parseInt(parts[0], 10);
  //     if (isNaN(kind)) continue;

  //     if (kind === 99 && parts.length >= 8) {
  //       let refName = parts[7];
  //       const atIdx = refName.indexOf("@");
  //       const base = atIdx > 0 ? refName.substring(0, atIdx) : refName;

  //       if (!visited.has(base) && this.glyphData.has(base)) {
  //         visited.add(base);
  //         const refData = this.glyphData.get(base)!;
  //         const refBox = this.computeBbox(refData, visited);
  //         if (bboxValid(refBox)) {
  //           const rx1 = parseInt(parts[3], 10);
  //           const ry1 = parseInt(parts[4], 10);
  //           const rx2 = parseInt(parts[5], 10);
  //           const ry2 = parseInt(parts[6], 10);
  //           // 映射 ref 坐标到目标矩形
  //           const mx1 = rx1 + (rx2 - rx1) * refBox.x1 / 200;
  //           const my1 = ry1 + (ry2 - ry1) * refBox.y1 / 200;
  //           const mx2 = rx1 + (rx2 - rx1) * refBox.x2 / 200;
  //           const my2 = ry1 + (ry2 - ry1) * refBox.y2 / 200;
  //           // CBox: 向中心收缩
  //           if (mx1 > cbox.x1 && mx1 <= cx) cbox.x1 = mx1;
  //           if (mx2 < cbox.x2 && mx2 >= cx) cbox.x2 = mx2;
  //           if (my1 > cbox.y1 && my1 <= cy) cbox.y1 = my1;
  //           if (my2 < cbox.y2 && my2 >= cy) cbox.y2 = my2;
  //         }
  //       }
  //     } else {
  //       for (let i = 3; i + 1 < parts.length; i += 2) {
  //         const x = parseInt(parts[i], 10);
  //         const y = parseInt(parts[i + 1], 10);
  //         if (isNaN(x) || isNaN(y)) continue;
  //         if (x > cbox.x1 && x <= cx) cbox.x1 = x;
  //         if (x < cbox.x2 && x >= cx) cbox.x2 = x;
  //         if (y > cbox.y1 && y <= cy) cbox.y1 = y;
  //         if (y < cbox.y2 && y >= cy) cbox.y2 = y;
  //       }
  //     }
  //   }
  //   return cbox;
  // }

  private getComponentBbox(name: string): BBox {
    if (this.bboxCache.has(name))
      return this.bboxCache.get(name)!;

    const data = this.glyphData.get(name);
    if (!data) return makeBBox();

    const bbox = this.computeBbox(data);
    this.bboxCache.set(name, bbox);
    return bbox;
  }

  // 预留: 获取组件 CBox (暂未被调用, 保留供后续使用)
  // private getCbox(name: string, cx = 100, cy = 100): BBox {
  //   const cacheKey = `${name}:${cx}:${cy}`;
  //   if (this.cboxCache.has(cacheKey))
  //     return this.cboxCache.get(cacheKey)!;

  //   const data = this.glyphData.get(name);
  //   if (!data) return { x1: 0, y1: 0, x2: 200, y2: 200 };

  //   const cbox = this.computeCbox(data, cx, cy);
  //   this.cboxCache.set(cacheKey, cbox);
  //   return cbox;
  // }

  // ============================================================
  // 变体选择 (从 C++ 473-541 移植)
  // ============================================================

  private kageNameForChar(cp: number): string {
    const hex = cp.toString(16);
    const candidate = "u" + hex;
    if (this.glyphData.has(candidate))
      return candidate;
    return "";
  }

  // ============================================================
  // 笔画展开 + 部件包围盒 (对应 glyph_extend.return_bone / ids_anal.bbox)
  // ============================================================

  /**
   * 递归展开 type-99, 返回直绘笔画串; 坐标落在调用者的 0-200 空间。
   * 对应 glyph_extend.unfold —— 每层: 收子级 → 接缝拉伸 → 映射进引用矩形。
   *
   * visited 是「路径集」而非全局集: 只用来断环, 同一字形被引用两次照样展开
   * (Python 无此判重, 兄弟级重复引用必须都算进去)。
   */
  private collectStrokes(data: string, visited: Set<string>, depth = 0): string[] {
    return this.unfoldTo(
      data,
      { rect: { x1: 0, y1: 0, x2: 200, y2: 200 }, sx: 0, sy: 0, sx2: 0, sy2: 0 },
      visited,
      depth,
    );
  }

  /**
   * 解析字形内部的 99 引用名 —— 与 glyph_extend.get_data(exact=True) 同一规则
   *
   * ① 精确名优先;
   * ② 没有精确名时, 取**名字最长**的可用子串 (不是"退到本体"那一级)。
   * 为什么: 库里大量互为子串的拼接名 (u2ff1-cdp-88b4-u6bd4 与 u6bd4-j / u2ff1),
   * "精确 → 本体" 会跳到 u6bd4-j, 丢掉复合体自己的笔画 (实测 鹿-05 少 5 笔)。
   * 注意这条只用于**内部引用**; 叶子查找(加后缀)仍走 selectLeafVariant 的
   * "后缀 → 本体"退化, 两回事。
   */
  private resolveRef(refName: string): string | undefined {
    const key = refName.split("@")[0];
    // ① 精确名
    if (this.glyphData.has(key)) return key;
    // ② **剥后缀阶梯**: 逐段去掉末尾的 "-xxx", 找到存在的就停
    //    (X-j → X, X-01 → X, X-var-001 → X-var → X)
    //
    // 为什么不用"最长子串": 那套假设库是全的 (Python 侧 248 万条)。web bundle 只有
    // 139 万条, 99 引用的目标缺失率约一半 (652,985/1,332,102, 多是 ac1-*/第三方名),
    // 最长子串会兜到**别的字形**上 —— 展开出的笔画是错的, 甚至兜回自己导致整层被
    // 环检测跳过、返回空 → strokicBboxOf 拿到空盒 → ⿰/⿱⿲⿳ 的分配塌成一条线
    // (实测 u9ea6 / u5c06 都是空盒)。剥后缀只往"本体"方向走, 不跨名字;
    // 目标真的缺数据时老实返回 undefined, 让调用方按"缺字形"处理。
    let name = key;
    for (let i = 0; i < 4; i++) {
      const cut = name.lastIndexOf("-");
      if (cut <= 0) break;
      name = name.slice(0, cut);
      if (this.glyphData.has(name)) return name;
    }
    return undefined;
  }

  /** 一层的展开: geom 来自父级 99 行 (矩形 + 拉伸源点 ps / 目标点 pd) */
  private unfoldTo(
    data: string,
    geom: { rect: Rect; sx: number; sy: number; sx2: number; sy2: number },
    path: Set<string>,
    depth = 0,
  ): string[] {
    const A: string[] = [];
    if (!data || depth > 12) return A;

    for (const segRaw of data.split("$")) {
      const seg = segRaw.trim();
      if (!seg) continue;
      const p = seg.split(":");
      const kind = parseInt(p[0], 10);
      if (Number.isNaN(kind)) continue;
      if (kind === 99 && p.length >= 8) {
        const refName = p[7];
        const base = refName.split("@")[0];
        // resolveRef 返回的是**名字**, 这里必须再取一次数据 ——
        // 早期把名字当数据传给 unfoldTo, 结果 parseInt("u9ea6-j")=NaN,
        // 任何"数据是 99 引用"的字形都展开成 0 笔 (布局塌 / 包围退 legacy 的根因)。
        const refKey = this.resolveRef(refName);
        if (!refKey) continue;
        const refData = this.glyphData.get(refKey);
        if (!refData || path.has(base)) continue;
        // 99:sx:sy:x1:y1:x2:y2:name:sx2:sy2  (字段含义见 stretchSeam)
        const rect: Rect = {
          x1: Math.trunc(parseFloat(p[3])), y1: Math.trunc(parseFloat(p[4])),
          x2: Math.trunc(parseFloat(p[5])), y2: Math.trunc(parseFloat(p[6])),
        };
        const nx = (v: string | undefined) => {
          const n = v === undefined ? 0 : parseFloat(v);
          return Number.isFinite(n) ? n : 0;
        };
        // 缺栏/空栏一律当 0 (与 Python 端补齐到 11 栏一致): 库里有 21 行
        // 9/10 栏的第三方数据, 老代码取 Lp[9]/Lp[10] 会 IndexError/SyntaxError。
        const geom2 = {
          rect,
          sx: nx(p[1]), sy: nx(p[2]),
          sx2: nx(p[9]), sy2: nx(p[10]),
        };
        path.add(base);
        A.push(...this.unfoldTo(refData, geom2, path, depth + 1));
        path.delete(base);
      } else if (kind >= 1 && kind <= 7) {
        A.push(seg);
      }
    }

    this.stretchSeam(A, geom.sx, geom.sy, geom.sx2, geom.sy2);
    const x1 = Math.trunc(geom.rect.x1);
    const y1 = Math.trunc(geom.rect.y1);
    const w = Math.trunc(geom.rect.x2) - x1;
    const h = Math.trunc(geom.rect.y2) - y1;
    return A.map((s) => this.remapStroke(s, { x1, y1, x2: x1 + w, y2: y1 + h }));
  }

  /**
   * 接缝拉伸 —— 逐字对齐 kage-bundle.js 的 getEachStrokesOfBuhin + stretch
   *
   * 99 行的两个点 (相对中心的偏移):
   *   缝   sp = (sx2,sy2) + 100        列9,10
   *   目标 dp = (sx,sy)  + 100         列1,2, 但 sx>100 时先 sx-=200
   * 且 sx>100 走"折成负偏移"这条, 否则把缝归到中心 (sx2=sy2=0)。
   * 然后按 p<sp+100 / p≥sp+100 把 [min,max] 两段分别线性映到 [min,dp+100] /
   * [dp+100,max]: 缝从 sp 挪到 dp, 元素被拉开或压扁。
   *
   * 关键在第 2 步的合法性: 只要 dp+100 仍落在 [min,max] 内, 两段就都是增函数,
   * 内容不会跑出自己的盒子。早先照 Python 早期版本把列1,2 当缝、列9,10 当目标
   * 再加 100, 130/200 这类"右半区位置"会变成 230/300 —— 冲过子件盒右沿后右半段
   * 退化成减函数, 于是 忽 的心 / 鼻 的自 出现反向拉伸和飞出框外的点。
   */
  private stretchSeam(
    A: string[],
    sx: number, sy: number, sx2: number, sy2: number,
  ): void {
    if (sx !== 0 || sy !== 0) {
      if (sx > 100) {
        sx -= 200;
      } else {
        sx2 = 0;
        sy2 = 0;
      }
    }
    if (sx === 0 && sy === 0) return;

    let bx1 = Infinity, by1 = Infinity, bx2 = -Infinity, by2 = -Infinity;
    for (const s of A) {
      const p = s.split(":");
      const k = parseInt(p[0], 10);
      if (!(k >= 1 && k <= 7)) continue;
      for (let i = 3; i + 1 < p.length; i += 2) {
        const x = parseFloat(p[i]);
        const y = parseFloat(p[i + 1]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        if (x < bx1) bx1 = x;
        if (x > bx2) bx2 = x;
        if (y < by1) by1 = y;
        if (y > by2) by2 = y;
      }
    }
    if (!Number.isFinite(bx1)) return;

    // 缝 = (sx2,sy2)+100, 目标 = (sx,sy)+100 (kage-bundle.js: stretch(dp=sx, sp=sx2))
    const spx = sx2 + 100;
    const spy = sy2 + 100;
    const dpx = sx + 100;
    const dpy = sy + 100;

    // p < 缝 → [lo, 缝] 映到 [lo, 目标]; p ≥ 缝 → [缝, hi] 映到 [目标, hi]
    const warp = (v: number, lo: number, hi: number, sp: number, dp: number): number => {
      if (v < sp) return sp !== lo ? lo + ((v - lo) * (dp - lo)) / (sp - lo) : dp;
      if (v > sp) return hi !== sp ? dp + ((v - sp) * (hi - dp)) / (hi - sp) : dp;
      return dp;
    };

    for (let n = 0; n < A.length; n++) {
      const p = A[n].split(":");
      const k = parseInt(p[0], 10);
      if (!(k >= 1 && k <= 7)) continue;
      for (let i = 3; i + 1 < p.length; i += 2) {
        const x = parseFloat(p[i]);
        const y = parseFloat(p[i + 1]);
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        p[i] = String(warp(x, bx1, bx2, spx, dpx));
        p[i + 1] = String(warp(y, by1, by2, spy, dpy));
      }
      A[n] = p.join(":");
    }
  }

  /** 把笔画控制点从 0-200 线性映射到 rect (保留类型与头形/尾形两栏) */
  private remapStroke(seg: string, rect: Rect): string {
    const p = seg.split(":");
    const rw = rect.x2 - rect.x1;
    const rh = rect.y2 - rect.y1;
    const out = [p[0], p[1], p[2]];
    for (let i = 3; i + 1 < p.length; i += 2) {
      const x = parseFloat(p[i]);
      const y = parseFloat(p[i + 1]);
      out.push(String(rect.x1 + (x / 200) * rw));
      out.push(String(rect.y1 + (y / 200) * rh));
    }
    return out.join(":");
  }

  /**
   * 部件包围盒 = 各笔画 strokic 轮廓盒的并集
   * 对应 ids_anal.bbox() —— 用 ifshrink=True 那一档 (笔尖边按 ofs 收掉)。
   * 注意与 getComponentBbox (纯控制点 bbox) 是两套, 不要混用。
   */
  private strokicBboxOf(name: string): BBox {
    const key = "sk:" + name;
    const hit = this.bboxCache.get(key);
    if (hit) return hit;

    const bb = makeBBox();
    let ok = false;
    const baseName = name.split("@")[0];
    const data = this.glyphData.get(name) ?? this.glyphData.get(baseName);
    if (data) {
      const strokes = this.collectStrokes(data, new Set([baseName]));
      const u = strokes.length ? strokesBbox(strokes, true) : null;
      if (u && u.x2 > u.x1 && u.y2 > u.y1) {
        bb.x1 = u.x1; bb.y1 = u.y1; bb.x2 = u.x2; bb.y2 = u.y2;
        ok = true;
      }
    }
    if (!ok) {
      // 展开失败 / 盒退化时**绝不能**把空盒 (200,200,0,0) 交给 layoutRects ——
      // 那会让 ⿰/⿱⿲⿳ 的分配塌成一条线或飞出去。
      // 退回控制点 bbox (getComponentBbox) 至少是个有效尺寸。
      const fb = this.getComponentBbox(name);
      if (bboxValid(fb)) {
        bb.x1 = fb.x1; bb.y1 = fb.y1; bb.x2 = fb.x2; bb.y2 = fb.y2;
        console.warn(`[KageEngine] strokicBboxOf(${name}) 回退到控制点 bbox`, fb);
      } else {
        // 连控制点都没有: 用画布整幅, 别返回空盒
        bb.x1 = 0; bb.y1 = 0; bb.x2 = 200; bb.y2 = 200;
        console.warn(`[KageEngine] strokicBboxOf(${name}) 完全取不到, 用 0-200`);
      }
    }
    this.bboxCache.set(key, bb);
    return bb;
  }

  /**
   * 叶子变体选择 —— 与 ids_anal.IDS 一致: 固定后缀, 缺失时退化到本体
   *
   * Python 端靠 glyph_extend.get_data 的子串匹配: 查 "u7592-01" 若不存在,
   * 会命中它的子串 "u7592"(本体)。但它够不到 -08/-07/-var-* 这类,
   * 所以这里也只试「后缀名 → 本体」两级, 保证 web 与 Python 产出一致。
   */
  private selectLeafVariant(cp: number, position: number, opCp: number): string {
    const base = "u" + cp.toString(16);
    const named = base + leafSuffix(opCp, position);
    if (this.glyphData.has(named)) return named;
    if (this.glyphData.has(base)) return base;
    return "";
  }

  // ============================================================
  // 包围矩形分配 (从 C++ 546-638 移植)
  // ============================================================

  /**
   * 包围结构的分配矩形 (空腔算法)。
   *
   * 返回 [容器矩形(不变), 内部件映射矩形]:
   *   · 容器矩形固定 0-200 (容器笔画原样画)
   *   · 内部件矩形 = fitInto(basis, cavity): 把**基准盒**映射到空腔上,
   *     于是内部件的缩放比 = 空腔/基准盒 (中宫盒小 → 放得大)
   *
   * 空腔求不出来时退回旧算法 (C++ 移植的固定矩形), 保证字不消失。
   */
  private surroundRects(opCp: number, outerName: string, innerName: string): Rect[] {
    const op = String.fromCodePoint(opCp);
    const container = this.composeStrokes(outerName);
    const inner = this.composeStrokes(innerName);
    const plan = container.length && inner.length
      ? surroundPlan(op, container, inner)
      : null;
    if (plan?.target) {
      const t = plan.target;
      return [
        { x1: 0, y1: 0, x2: 200, y2: 200 },
        { x1: t.x1, y1: t.y1, x2: t.x2, y2: t.y2 },
      ];
    }
    // 没走成新算法: 打出**原因**, 否则会静默退到旧固定矩形 (视觉上就是"下面空一段")
    const why = !container.length ? "容器笔画为空"
      : !inner.length ? "内部件笔画为空"
      : !plan ? "planSurround 返回 null"
      : !plan.cavity ? `没求出空腔 (候选 ${plan.candidates.length}, 面数见 cavity)`
      : !plan.basis ? "没求出基准盒"
      : "目标矩形非法";
    console.warn(`[KageEngine] ${op}${outerName}+${innerName} 退回旧固定矩形: ${why}`,
      plan ? { cavity: plan.cavity, basis: plan.basis, candidates: plan.candidates } : null);
    return this.surroundRectsLegacy(opCp, outerName);
  }

  /** 一个字形名 → 展开后的直绘笔画 (合成算法只需要直绘笔画) */
  private composeStrokes(name: string): string[] {
    const base = name.split("@")[0];
    const data = this.glyphData.get(name) ?? this.glyphData.get(base);
    if (!data) return [];
    return this.collectStrokes(data, new Set([base]));
  }

  /**
   * 包围合成的全部中间结果 (给预览画框 / 调试用):
   * 空腔、候选面、内部件外框、中宫盒、基准盒、目标矩形。
   */
  planSurround(op: string, outerName: string, innerName: string): SurroundPlan | null {
    const container = this.composeStrokes(outerName);
    const inner = this.composeStrokes(innerName);
    if (container.length === 0 || inner.length === 0) return null;
    return surroundPlan(op, container, inner);
  }

  /** 旧的固定矩形分配 (C++ 移植), 只在空腔路径失败时兜底 */
  private surroundRectsLegacy(opCp: number, outerName: string): Rect[] {
    const clamp = (ix1: number, iy1: number, ix2: number, iy2: number): Rect => {
      ix1 = Math.max(3, Math.min(ix1, 197));
      iy1 = Math.max(3, Math.min(iy1, 197));
      ix2 = Math.max(ix1 + 10, Math.min(ix2, 197));
      iy2 = Math.max(iy1 + 10, Math.min(iy2, 197));
      return { x1: ix1, y1: iy1, x2: ix2, y2: iy2 };
    };

    const outer: Rect = { x1: 0, y1: 0, x2: 200, y2: 200 };
    const bb = outerName ? this.getComponentBbox(outerName) : makeBBox();

    if (!bboxValid(bb)) {
      let ix1: number, iy1: number, ix2: number, iy2: number;
      switch (opCp) {
      case 0x2FF4: ix1 = 38; iy1 = 38; ix2 = 162; iy2 = 162; break;
      case 0x2FF5: ix1 = 18; iy1 = 38; ix2 = 182; iy2 = 197; break;
      case 0x2FF6: ix1 = 18; iy1 = 3;  ix2 = 182; iy2 = 108; break;
      case 0x2FF7: ix1 = 52; iy1 = 18; ix2 = 197; iy2 = 182; break;
      case 0x2FF8: ix1 = 58; iy1 = 52; ix2 = 197; iy2 = 197; break;
      case 0x2FF9: ix1 = 3;  iy1 = 42; ix2 = 148; iy2 = 197; break;
      case 0x2FFA: ix1 = 45; iy1 = 3;  ix2 = 197; iy2 = 158; break;
      case 0x2FFC: ix1 = 3;  iy1 = 18; ix2 = 148; iy2 = 182; break;
      default:     ix1 = 8;  iy1 = 8;  ix2 = 192; iy2 = 192; break;
      }
      return [outer, clamp(ix1, iy1, ix2, iy2)];
    }

    const ox1 = bb.x1, oy1 = bb.y1, ox2 = bb.x2, oy2 = bb.y2;
    const ow = ox2 - ox1, oh = oy2 - oy1;

    let ix1: number, iy1: number, ix2: number, iy2: number;
    switch (opCp) {
    case 0x2FF4: { // ⿴ 全包围
      const cx = Math.floor((ox1 + ox2) / 2);
      const cy = Math.floor((oy1 + oy2) / 2);
      const iw = ow * 0.90, ih = oh * 0.95;
      ix1 = cx - iw / 2; iy1 = cy - ih / 2;
      ix2 = cx + iw / 2; iy2 = cy + ih / 2;
      break;
    }
    case 0x2FF5: // ⿵ 从上包围
      ix1 = ox1 + 10; iy1 = oy1 + oh * 0.12;
      ix2 = ox2 - 10; iy2 = 197;
      break;
    case 0x2FF6: // ⿶ 从下包围
      ix1 = ox1 + 2; iy1 = 0;
      ix2 = ox2 - 2; iy2 = oy2 - 3;
      break;
    case 0x2FF7: // ⿷ 从左包围
      ix1 = ox1 + ow * 0.22; iy1 = oy1 + 8;
      ix2 = 197; iy2 = oy2 - 8;
      break;
    case 0x2FFC: // ⿼ 从右包围(?)
      ix1 = 3; iy1 = oy1 + 8;
      ix2 = ox2 - ow * 0.22; iy2 = oy2 - 8;
      break;
    case 0x2FF8: // ⿸ 从左上包围
      ix1 = Math.min(Math.floor(ox1 + ow * 0.32), 90);
      iy1 = Math.min(Math.floor(oy1 + oh * 0.32), 85);
      ix2 = 197; iy2 = 197;
      break;
    case 0x2FF9: // ⿹ 从右上包围
      ix2 = Math.max(Math.floor(ox2 - ow * 0.30), 110);
      iy1 = Math.floor(oy1 + oh * 0.25);
      ix1 = 3; iy2 = 197;
      break;
    case 0x2FFA: // ⿺ 从左下包围
      ix1 = Math.floor(ox1 + ow * 0.30);
      iy2 = Math.max(Math.floor(oy2 - oh * 0.30), 110);
      ix2 = 197; iy1 = 3;
      break;
    default:
      ix1 = 8; iy1 = 8; ix2 = 192; iy2 = 192;
      break;
    }

    return [outer, clamp(ix1, iy1, ix2, iy2)];
  }

  // ============================================================
  // 动态重叠计算 (从 C++ 644-668 移植; 预留, 暂未参与矩形分配)
  // ============================================================

  // private computeDynamicOverlap(opCp: number, childNames: string[]): number {
  //   if (childNames.length < 2) return 6;

  //   const b1 = this.getComponentBbox(childNames[0]);
  //   const b2 = this.getComponentBbox(childNames[1]);

  //   if (!bboxValid(b1) || !bboxValid(b2)) return 6;
  //   if ((b1.x2 - b1.x1) >= 180 || (b1.y2 - b1.y1) >= 180 ||
  //       (b2.x2 - b2.x1) >= 180 || (b2.y2 - b2.y1) >= 180) return 12;

  //   if (opCp === 0x2FF0) {
  //     const gap1 = 200 - b1.x2;
  //     const gap2 = b2.x1;
  //     const extra = (gap1 + gap2) * 0.90;
  //     return Math.max(10, Math.min(6 + extra, 100));
  //   } else {
  //     const gap1 = 200 - b1.y2;
  //     const gap2 = b2.y1;
  //     const extra = (gap1 + gap2) * 0.80;
  //     return Math.max(6, Math.min(6 + extra, 90));
  //   }
  // }

  // ============================================================
  // 工具函数
  // ============================================================

  private nextGlyphName(): string {
    return "_c" + (this.glyphCounter++).toString().padStart(3, "0");
  }

  /** 递归加载 type-99 依赖到 kage-bundle.js */
  private resolveDeps(data: string, loaded: Set<string>): void {
    if (!data) return;
    const strokes = data.split("$");
    for (const stroke of strokes) {
      if (!stroke.startsWith("99:")) continue;
      const parts = stroke.split(":");
      if (parts.length < 8) continue;

      const refName = parts[7];
      if (!refName || loaded.has(refName)) continue;

      // 查找字形数据: 先精确匹配, 再尝试剥离 @N 后缀
      let refData = this.glyphData.get(refName);
      let lookupName = refName;
      if (!refData) {
        const atIdx = refName.indexOf("@");
        if (atIdx > 0) {
          lookupName = refName.substring(0, atIdx);
          refData = this.glyphData.get(lookupName);
        }
      }
      if (!refData) {
        console.warn("[KageEngine] dep not found:", lookupName);
        continue;
      }

      // 用原始名称 (含 @N) 加载到 KAGE 引擎
      loadGlyph(refName, refData);
      loaded.add(refName);

      // 递归
      this.resolveDeps(refData, loaded);
    }
  }

  // ============================================================
  // buildComposite — 核心: 递归 IDS → type-99 KAGE 数据 (从 C++ 674-864 移植)
  // ============================================================

  private buildComposite(
    ids: string,
    posRef: { pos: number },
    parentOpCp: number = 0,
    position: number = 0,
  ): CompositeResult {
    const result: CompositeResult = { rootName: "", data: "" };
    if (posRef.pos >= ids.length) return result;

    const opCp = codePointAt(ids, posRef.pos);

    // 叶子节点 — 选择最佳变体
    if (!isIdsOperator(opCp)) {
      if (parentOpCp !== 0)
        result.rootName = this.selectLeafVariant(opCp, position, parentOpCp);
      else
        result.rootName = this.kageNameForChar(opCp);
      if (!result.rootName) {
        console.warn(`[KageEngine] no variant for U+${opCp.toString(16)}`);
        return result;
      }
      posRef.pos += cpLen(opCp);

      // 将叶子数据加载到 kage-bundle.js (以便后续 getGlyphBox 使用)
      const leafData = this.glyphData.get(result.rootName);
      if (leafData) {
        loadGlyph(result.rootName, leafData);
      }

      return result;
    }

    posRef.pos++; // 跳过操作符 (IDS 操作符全在 BMP, 单 JS char)

    let arity = 2;
    const surround = isSurroundOp(opCp);
    switch (opCp) {
    case 0x2FF2: case 0x2FF3: arity = 3; break;
    case 0x2FFE: case 0x2FFF: arity = 1; break;
    }

    // 第一遍: 递归处理子节点
    const childNames: string[] = [];
    for (let k = 0; k < arity; k++) {
      const child = this.buildComposite(ids, posRef, opCp, k);
      if (!child.rootName) return result;
      childNames.push(child.rootName);
    }

    // 第二遍: 分配矩形
    // 预留: 动态重叠计算 (C++ 移植残留, 暂未参与分配)
    // let dynOverlap = 0;
    // if (opCp === 0x2FF0 || opCp === 0x2FF1)
    //   dynOverlap = this.computeDynamicOverlap(opCp, childNames);

    const children: ChildInfo[] = [];

    for (let k = 0; k < arity; k++) {
      const ci: ChildInfo = {
        name: childNames[k],
        x1: 0, y1: 0, x2: 200, y2: 200, rot: 0, flip: 0,
      };

      if (surround) {
        // 包围算符: 仍用旧算法 (尚未移植, 待你研究的空腔方案接入)
        const rects = this.surroundRects(opCp, childNames[0], childNames[1]);
        const r = k < rects.length ? rects[k] : { x1: 0, y1: 0, x2: 200, y2: 200 };
        ci.x1 = r.x1; ci.y1 = r.y1; ci.x2 = r.x2; ci.y2 = r.y2;
      } else if (arity === 1) {
        if (opCp === 0x2FFE) { // 镜像 (⿾)
          // 不再用「反向矩形」手工镜像: 那是对骨架镜像, 之后明朝体的起收笔
          // 调整 (adjustStrokes) 是方向敏感的, 会只镜像一半 (实测 日 的墨迹
          // 从 [40,165] 变成 [40,160], 左边那半没动)。改成和旋转同一条通路:
          // 发 0:98 命令, 由渲染器 dfTransform 对**成品轮廓**做镜像。
          ci.x1 = 0; ci.x2 = 200; ci.y1 = 0; ci.y2 = 200;
          ci.flip = 1;
        } else if (opCp === 0x2FFF) { // 旋转 (⿿)
          ci.x1 = 0; ci.x2 = 200; ci.y1 = 0; ci.y2 = 200;
          // a3 = 四分之一圈计数; 库里 0:99:2 出现 79 次 (0:99:1 只有 1 次),
          // 即 ⿿ 默认是 180°。⿿[n] 直接映射 a3。
          ci.rot = 2;
        } else {
          ci.x1 = 0; ci.y1 = 0; ci.x2 = 200; ci.y2 = 200;
        }
      } else {
        // ⿰ ⿱ ⿲ ⿳ ⿻ —— 统一走 layoutRects (与 ids_anal.IDS 逐式一致)
        const boxes = childNames.map((n) => this.strokicBboxOf(n));
        const rects = layoutRects(opCp, boxes);
        const r = rects[k] ?? { x1: 0, y1: 0, x2: 200, y2: 200 };
        ci.x1 = r.x1; ci.y1 = r.y1; ci.x2 = r.x2; ci.y2 = r.y2;
      }

      children.push(ci);
    }

    // 第三遍: 生成 type-99 数据
    //
    // 变换命令 (0:9x) 的两个约定, 都从 kage-bundle.js 的 dfTransform 反推:
    //   ① a3 是"四分之一圈"计数 (97/98 忽略它, 99 用它: 1=90°, 2=180°, 3=270°)
    //   ② 命令框必须**比画布宽**: dfTransform 要求一条多边形的所有点都在框内
    //      才变换, 否则整条跳过; 而墨迹经常超出 0-200 几个像素 (笔端),
    //      用紧框就会"只转了一半" —— 这就是镜像/旋转偶发消失的原因。
    //      库里作者自己也绕这个门 (有一条 0:98:0:-10:-10:210:210)。
    const XFORM_BOX = "-20:-20:220:220";
    const strokeList: string[] = [];
    for (const c of children) {
      strokeList.push(
        `99:0:0:${c.x1}:${c.y1}:${c.x2}:${c.y2}:${c.name}:0:0:0`,
      );
      if (c.flip)
        strokeList.push(`0:98:0:${XFORM_BOX}`);
      if (c.rot)
        strokeList.push(`0:99:${c.rot}:${XFORM_BOX}`);
    }
    result.data = strokeList.join("$");
    result.rootName = this.nextGlyphName();

    // 缓存该复合的 bbox (子矩形并集)
    {
      const cb = makeBBox();
      for (const c of children) {
        expandBBox(cb, c.x1, c.y1);
        expandBBox(cb, c.x2, c.y2);
      }
      this.bboxCache.set(result.rootName, cb);
    }

    // 加载到 kage-bundle.js
    loadGlyph(result.rootName, result.data);
    this.glyphData.set(result.rootName, result.data);

    return result;
  }

  // ============================================================
  // 公开 API: IDS → SVG (从 C++ 870-930 移植)
  // ============================================================

  /** 预取本串需要、但本地还没有的字形 (远程兜底); 返回取不到的名字 */
  async prefetchFor(ids: string): Promise<string[]> {
    if (!this.source) return [];
    const SUFFIXES = ["", "-01", "-02", "-03", "-04", "-05", "-06", "-07", "-08", "-09",
      "-10", "-11", "-14", "-15", "-24", "-j"];
    const names = guessGlyphNames(ids, SUFFIXES).filter((n) => !this.glyphData.has(n));
    if (names.length === 0) return [];
    const r = await this.source.ensure(names);
    return r.failed;
  }

  /** 渲染失败时按串去重地排一次预取, 取到后触发一次重排 */
  private schedulePrefetch(ids: string): void {
    if (!this.source || !ids || this.prefetching.has(ids)) return;
    this.prefetching.add(ids);
    void this.prefetchFor(ids)
      .then((failed) => {
        const total = failed.length;
        if (total > 0) {
          console.warn(`[KageEngine] ${total} 个字形取不到 (远端子集): ${failed.slice(0, 6).join(", ")}…`);
        }
        this.afterPrefetch();
      })
      .catch(() => { /* 网络问题不阻塞渲染 */ })
      .finally(() => { this.prefetching.delete(ids); });
  }

  /**
   * 远程取到字形之后的重排触发
   *
   * 为什么不是直接 `__recomposeIds?.()`: 线上(无 bundle)首次渲染发生得很早,
   * 那一刻 idsCompose 的插件可能**还没注册** __recomposeIds, 或者它的 IDS 数据库
   * 还没 loaded —— 直接调用会被静默吞掉, 于是字一直停在"等待数据"的黄色状态。
   * 这里改成轮询等待函数出现, 再交给它自己的重试预算去等数据库。
   */
  private afterPrefetch(attempt = 0): void {
    const fn = (window as any).__recomposeIds;
    if (typeof fn === "function") {
      fn();
      return;
    }
    if (attempt >= 20) {
      console.warn("[KageEngine] __recomposeIds 一直未注册, 放弃自动重排");
      return;
    }
    setTimeout(() => this.afterPrefetch(attempt + 1), 250);
  }

  /** 将 IDS 字符串渲染为 SVG，未就绪或失败返回 null */
  renderSvg(ids: string): string | null {
    const out = this.renderSvgInner(ids);
    // 缺字形 → 排一次远程预取, 取到后由 __recomposeIds 触发重排 (同步 API 保持不变)
    if (!out) this.schedulePrefetch(ids);
    return out;
  }

  private renderSvgInner(ids: string): string | null {
    if (!this._ready || !ids) return null;

    const cached = this.idsToSvg.get(ids);
    if (cached) return cached;

    // 1. 清空 kage-bundle.js 和 bbox 缓存
    clearGlyphs();
    this.bboxCache.clear();

    // 2. 构建复合字形树
    const posRef = { pos: 0 };
    const composite = this.buildComposite(ids, posRef);
    if (!composite.rootName) return null;

    if (posRef.pos !== ids.length) {
      console.warn(`[KageEngine] incomplete parse at ${posRef.pos}/${ids.length}`);
      return null;
    }

    const loaded = new Set<string>();
    loaded.add(composite.rootName);

    // 3. 如果是叶子节点 (非复合), 加载原始数据
    if (!composite.data) {
      const leafData = this.glyphData.get(composite.rootName);
      if (leafData) {
        loadGlyph(composite.rootName, leafData);
        this.resolveDeps(leafData, loaded);
      }
    }

    // 4. 解析复合数据中的 type-99 依赖
    this.resolveDeps(composite.data, loaded);

    // 5. 调用 kage-bundle.js 渲染
    const svg = renderGlyph(composite.rootName, true);
    if (!svg) return null;

    // 适配深色主题: 替换黑色填充
    const themed = svg.replace(/fill="black"/g, 'fill="#ffffff"');

    this.idsToSvg.set(ids, themed);
    return themed;
  }

  /** 将 IDS 解析为完全展开的 KAGE 笔画数据 (用于 kage-editor) */
  kageDataFromIds(ids: string): string | null {
    if (!this._ready || !ids) return null;

    // const cached = this.idsToSvg.get(ids);  // 复用同一缓存键 (实际存的是不同数据, 但 C++ 分别缓存)
    // 注: C++ 用 m_idsToKageData 单独缓存, 这里暂不缓存简化实现

    clearGlyphs();
    this.bboxCache.clear();

    const posRef = { pos: 0 };
    const composite = this.buildComposite(ids, posRef);
    if (!composite.rootName) return null;

    if (posRef.pos !== ids.length) return null;

    const loaded = new Set<string>();
    loaded.add(composite.rootName);

    if (!composite.data) {
      const leafData = this.glyphData.get(composite.rootName);
      if (leafData) {
        loadGlyph(composite.rootName, leafData);
        this.resolveDeps(leafData, loaded);
      }
    }

    this.resolveDeps(composite.data, loaded);

    // getGlyphData 返回完全展开的 KAGE 数据
    return getGlyphData(composite.rootName) || null;
  }
}
