/**
 * GlyphFontManager — IDS 字形 ↔ Web 字体管理
 *
 * 职责:
 *   1. IDS 表达式 ↔ PUA 码点 (U+E000~U+E8FF) 双向映射
 *   2. KAGE SVG → opentype.js TrueType 轮廓 → FontFace 动态加载
 *   3. 字体序列化/反序列化 (文件保存/加载)
 *
 * PUA 范围: U+E000 ~ U+E8FF (2304 个位置, 文档内足够使用)
 */

import opentype from "opentype.js";

const PUA_START = 0xe000;
const PUA_END = 0xe8ff;
const FONT_UNITS = 1000;
const SVG_SIZE = 200;  // KAGE SVG viewBox 尺寸
const SCALE = FONT_UNITS / SVG_SIZE;  // 5.0
const FONT_FAMILY = "IDSGlyphFont";

// IDS 运算符 (U+2FF0-2FFF): 表达式的起始字符
const IDS_OPERATORS = "⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻⿾⿿㇯";

export interface GlyphMapping {
  idsToPua: [string, number][];
  nextPua: number;
}

export class GlyphFontManager {
  private idsToPua = new Map<string, number>();
  private puaToIds = new Map<number, string>();
  // ids → 显示字符 (真字符或 PUA), 由 idsCompose 合成时注册, 供块内渲染替换
  private idsToDisplay = new Map<string, string>();
  private svgCache = new Map<number, string>();  // pua → SVG 备用 (重建字体用)
  private kageCache = new Map<number, string>();  // pua → KAGE 原始数据 (重新编辑用)
  private nextPua = PUA_START;
  private fontBuffer: ArrayBuffer | null = null;
  private _ready = false;
  private _building = false;
  private _needsRebuild = false;

  get ready(): boolean {
    return this._ready;
  }

  /** 分配或获取已有 PUA 码点 (已存在时不覆盖, 避免即时合成冲掉编辑) */
  getOrCreatePua(idsSource: string, svgData: string): number {
    const existing = this.idsToPua.get(idsSource);
    if (existing !== undefined) return existing;

    if (this.nextPua > PUA_END) {
      console.warn("[GlyphFont] PUA range exhausted");
      return -1;
    }
    const pua = this.nextPua++;
    this.idsToPua.set(idsSource, pua);
    this.puaToIds.set(pua, idsSource);
    this.svgCache.set(pua, svgData);
    return pua;
  }

  /** 显式更新 PUA 的 SVG 和 KAGE 数据 (仅 KAGE 编辑提交时调用) */
  updatePuaSvg(idsSource: string, svgData: string, kageData: string): number {
    const existing = this.idsToPua.get(idsSource);
    const pua = existing ?? this.nextPua++;

    if (!existing) {
      if (pua > PUA_END) {
        console.warn("[GlyphFont] PUA range exhausted");
        return -1;
      }
      this.idsToPua.set(idsSource, pua);
      this.puaToIds.set(pua, idsSource);
    }

    this.svgCache.set(pua, svgData);
    if (kageData) this.kageCache.set(pua, kageData);
    return pua;
  }

  /** 根据已有 PUA 获取 IDS 源 (退格展开用) */
  getIdsSource(pua: number): string | null {
    return this.puaToIds.get(pua) || null;
  }

  /** 根据已有 PUA 获取 IDS 源, 兜底接受字符形式 */
  getIdsFromChar(ch: string): string | null {
    const cp = ch.codePointAt(0);
    if (cp === undefined) return null;
    return this.getIdsSource(cp);
  }

  // ============================================================
  // SVG → TrueType 轮廓
  // ============================================================

  /** 解析 SVG → opentype.js Path (支持 <path d="..."> 和 <polygon points="...">) */
  private svgToGlyphPath(svgData: string): opentype.Path | null {
    const opPath = new opentype.Path();

    // 提取所有 <path d="..."> 的路径数据
    const pathRe = /<path[^>]*\sd="([^"]*)"[^>]*\/?>/gi;
    let match;
    let found = false;

    while ((match = pathRe.exec(svgData)) !== null) {
      const d = match[1];
      if (this.parseSvgD(d, opPath)) found = true;
    }

    // 兜底: 提取 <polygon points="..."> (KAGE 在 curve=false 时使用)
    const polyRe = /<polygon[^>]*\spoints="([^"]*)"[^>]*\/?>/gi;
    while ((match = polyRe.exec(svgData)) !== null) {
      const points = match[1].trim();
      if (this.parsePolygonPoints(points, opPath)) found = true;
    }

    return found ? opPath : null;
  }

  /** 解析 <polygon points="x,y x,y ..."> → 闭合多边形轮廓 */
  private parsePolygonPoints(points: string, opPath: opentype.Path): boolean {
    const coords = points.split(/[\s,]+/).map(Number);
    if (coords.length < 4) return false;  // 至少需要 2 个点

    // 第一个点 moveTo
    const sx = coords[0] * SCALE;
    const sy = FONT_UNITS - coords[1] * SCALE;
    opPath.moveTo(sx, sy);

    // 后续点 lineTo
    for (let i = 2; i + 1 < coords.length; i += 2) {
      const x = coords[i] * SCALE;
      const y = FONT_UNITS - coords[i + 1] * SCALE;
      opPath.lineTo(x, y);
    }

    opPath.closePath();
    return true;
  }

  /** 解析单个 SVG d 属性字符串, 追加到 opPath */
  private parseSvgD(d: string, opPath: opentype.Path): boolean {
    // 按命令字母分割
    const parts = d.match(/[MLHVQCSTAZmlhvqcsatz][^MLHVQCSTAZmlhvqcsatz]*/g);
    if (!parts) return false;

    let cx = 0, cy = 0;    // current point (font coords)
    let sx = 0, sy = 0;    // sub-path start
    // let lastCmd = "";   // 预留: 记录上一条命令 (暂未使用)

    for (const part of parts) {
      const cmd = part[0].toUpperCase();
      const raw = part.slice(1).trim();
      if (!raw && cmd !== "Z") continue;
      const nums = raw ? raw.split(/[\s,]+/).map(Number) : [];

      // 相对坐标转绝对 (预留工具, 暂未使用)
      // const toAbs = (i: number) => {
      //   const isRel = part[0] === part[0].toLowerCase();
      //   if (!isRel) return nums[i];

      //   // 奇数索引是 Y, 偶数索引是 X
      //   if (cmd === "V") return FONT_UNITS - nums[i] * SCALE + (FONT_UNITS - cy);
      //   if (cmd === "H") return nums[i] * SCALE + cx;
      //   return (i % 2 === 0 ? nums[i] * SCALE + cx : FONT_UNITS - nums[i] * SCALE + (FONT_UNITS - cy));
      // };

      // 绝对坐标 (SVG origin → font units, Y flip)
      const fx = (i: number) => nums[i] * SCALE;
      const fy = (i: number) => FONT_UNITS - nums[i] * SCALE;

      switch (cmd) {
        case "M": {
          if (part[0] === part[0].toLowerCase()) {
            // 相对坐标
            for (let i = 0; i + 1 < nums.length; i += 2) {
              cx += nums[i] * SCALE;
              cy -= nums[i + 1] * SCALE;
              opPath.moveTo(cx, cy);
              sx = cx; sy = cy;
            }
          } else {
            for (let i = 0; i + 1 < nums.length; i += 2) {
              cx = fx(i); cy = fy(i + 1);
              opPath.moveTo(cx, cy);
              sx = cx; sy = cy;
            }
          }
          break;
        }
        case "L": {
          if (part[0] === part[0].toLowerCase()) {
            for (let i = 0; i + 1 < nums.length; i += 2) {
              cx += nums[i] * SCALE;
              cy -= nums[i + 1] * SCALE;
              opPath.lineTo(cx, cy);
            }
          } else {
            for (let i = 0; i + 1 < nums.length; i += 2) {
              cx = fx(i); cy = fy(i + 1);
              opPath.lineTo(cx, cy);
            }
          }
          break;
        }
        case "H": {
          for (let i = 0; i < nums.length; i++) {
            cx = part[0] === part[0].toLowerCase() ? cx + nums[i] * SCALE : fx(i);
            opPath.lineTo(cx, cy);
          }
          break;
        }
        case "V": {
          for (let i = 0; i < nums.length; i++) {
            cy = part[0] === part[0].toLowerCase() ? cy - nums[i] * SCALE : fy(i);
            opPath.lineTo(cx, cy);
          }
          break;
        }
        case "Q": {
          if (part[0] === part[0].toLowerCase()) {
            for (let i = 0; i + 3 < nums.length; i += 4) {
              const cpx = cx + nums[i] * SCALE;
              const cpy = cy - nums[i + 1] * SCALE;
              cx += nums[i + 2] * SCALE;
              cy -= nums[i + 3] * SCALE;
              opPath.quadTo(cpx, cpy, cx, cy);
            }
          } else {
            for (let i = 0; i + 3 < nums.length; i += 4) {
              const cpx = fx(i); const cpy = fy(i + 1);
              cx = fx(i + 2); cy = fy(i + 3);
              opPath.quadTo(cpx, cpy, cx, cy);
            }
          }
          break;
        }
        case "C": {
          // TrueType 只支持二次贝塞尔, 用 de Casteljau 分割近似为多条二次曲线
          if (part[0] === part[0].toLowerCase()) {
            for (let i = 0; i + 5 < nums.length; i += 6) {
              const x0 = cx, y0 = cy;
              const x1 = x0 + nums[i] * SCALE, y1 = y0 - nums[i + 1] * SCALE;
              const x2 = x0 + nums[i + 2] * SCALE, y2 = y0 - nums[i + 3] * SCALE;
              const x3 = x0 + nums[i + 4] * SCALE, y3 = y0 - nums[i + 5] * SCALE;
              this.cubicToQuads(opPath, x0, y0, x1, y1, x2, y2, x3, y3);
              cx = x3; cy = y3;
            }
          } else {
            for (let i = 0; i + 5 < nums.length; i += 6) {
              const x0 = cx, y0 = cy;
              const x1 = fx(i), y1 = fy(i + 1);
              const x2 = fx(i + 2), y2 = fy(i + 3);
              const x3 = fx(i + 4), y3 = fy(i + 5);
              this.cubicToQuads(opPath, x0, y0, x1, y1, x2, y2, x3, y3);
              cx = x3; cy = y3;
            }
          }
          break;
        }
        case "Z": {
          opPath.closePath();
          cx = sx; cy = sy;
          break;
        }
        // T (shorthand quadratic), S (shorthand cubic) 暂不处理
        case "A":
          // Arc: 转换为折线近似
          break;
      }

      // lastCmd = cmd;  // 预留 (声明已注释)
    }

    return opPath.commands.length > 0;
  }

  /** 三次贝塞尔近似为两段二次贝塞尔 (保持端点切线) */
  private cubicToQuads(
    opPath: opentype.Path,
    x0: number, y0: number,
    x1: number, y1: number,
    x2: number, y2: number,
    x3: number, y3: number,
  ): void {
    // 中点分割 + 端点切线近似
    const mx = (x0 + 3 * x1 + 3 * x2 + x3) / 8;
    const my = (y0 + 3 * y1 + 3 * y2 + y3) / 8;

    // 第一段二次: P0 → P0.5, 控制点 = (3*P1 - P0) / 2
    const q1x = (3 * x1 - x0) / 2;
    const q1y = (3 * y1 - y0) / 2;
    opPath.quadTo(q1x, q1y, mx, my);

    // 第二段二次: P0.5 → P3, 控制点 = (3*P2 - P3) / 2
    const q2x = (3 * x2 - x3) / 2;
    const q2y = (3 * y2 - y3) / 2;
    opPath.quadTo(q2x, q2y, x3, y3);
  }

  // ============================================================
  // 字体构建
  // ============================================================

  /** 重建 TrueType 字体并通过 FontFace 加载 (防并发: 同时只有一个构建在进行) */
  async buildFont(): Promise<void> {
    if (this._building) {
      this._needsRebuild = true;  // 标记需要重建, 当前构建完成后自动触发
      return;
    }

    if (this.svgCache.size === 0) {
      this._ready = true;
      return;
    }

    this._building = true;
    this._needsRebuild = false;

    try {
      const glyphs: opentype.Glyph[] = [];

      // .notdef (glyph 0)
      glyphs.push(new opentype.Glyph({
        name: ".notdef",
        unicode: 0,
        advanceWidth: FONT_UNITS,
      }));

      for (const [pua, svgData] of this.svgCache) {
        const path = this.svgToGlyphPath(svgData);
        glyphs.push(new opentype.Glyph({
          name: `g${pua.toString(16)}`,
          unicode: pua,
          advanceWidth: FONT_UNITS,
          path: path || undefined,
        }));
      }

      const font = new opentype.Font({
        familyName: FONT_FAMILY,
        styleName: "Regular",
        unitsPerEm: FONT_UNITS,
        ascender: 880,
        descender: -120,
        glyphs,
      });

      this.fontBuffer = font.toArrayBuffer();

      // 卸载旧字体
      try {
        const old = [...(document.fonts as any).values()].find(
          (f: any) => f.family === FONT_FAMILY,
        );
        if (old) (document.fonts as any).delete(old);
      } catch { /* ignore */ }

      // 加载新字体
      const face = new FontFace(FONT_FAMILY, this.fontBuffer!, {
        style: "normal",
        weight: "400",
        unicodeRange: "U+E000-E8FF",
      });
      await face.load();
      (document.fonts as any).add(face);

      this._ready = true;
      console.log(`[GlyphFont] font built: ${this.svgCache.size} glyphs`);
    } finally {
      this._building = false;
      // 如果在构建期间有新的重建请求, 立即执行 (使用最新的 svgCache)
      if (this._needsRebuild) {
        this._needsRebuild = false;
        await this.buildFont();
      }
    }
  }

  // ============================================================
  // 序列化 (文件保存/加载)
  // ============================================================

  /** 导出 IDS↔PUA 映射 (保存到 .idsmd 文件头) */
  exportMapping(): GlyphMapping {
    return {
      idsToPua: [...this.idsToPua.entries()],
      nextPua: this.nextPua,
    };
  }

  /** 从文件头恢复映射 */
  importMapping(data: GlyphMapping): void {
    this.idsToPua.clear();
    this.puaToIds.clear();
    this.nextPua = data.nextPua || PUA_START;
    for (const [ids, pua] of data.idsToPua) {
      this.idsToPua.set(ids, pua);
      this.puaToIds.set(pua, ids);
    }
  }

  /** 获取字体二进制 (保存到文件) */
  getFontBuffer(): ArrayBuffer | null {
    return this.fontBuffer;
  }

  /** 设置字形 SVG 缓存 (从文件加载后, 需要重新渲染时填充) */
  setSvgForPua(pua: number, svgData: string): void {
    this.svgCache.set(pua, svgData);
  }

  // ============================================================
  // KAGE 原始数据存储 (重新编辑时使用, 避免从 IDS 重新生成丢失编辑)
  // ============================================================

  /** 存储 PUA 对应的 KAGE 原始数据 */
  setKageData(pua: number, kageData: string): void {
    if (kageData) this.kageCache.set(pua, kageData);
  }

  /** 根据 PUA 获取 KAGE 原始数据 */
  getKageData(pua: number): string | null {
    return this.kageCache.get(pua) || null;
  }

  /** 根据 IDS 源获取 KAGE 原始数据 (右键重新编辑时使用) */
  getKageByIdsSource(idsSource: string): string | null {
    const pua = this.idsToPua.get(idsSource);
    if (pua === undefined) return null;
    return this.kageCache.get(pua) || null;
  }

  /** 获取已有映射用于 kageGlyph 节点 */
  hasMapping(idsSource: string): boolean {
    return this.idsToPua.has(idsSource);
  }

  /** 已映射 IDS 表达式 → PUA 码点; 未映射返回 -1 (ruby/双行块内渲染合成用) */
  getPua(idsSource: string): number {
    return this.idsToPua.get(idsSource) ?? -1;
  }

  /** 注册 ids → 显示字符 (合成时调用; 真字符与 PUA 路径都注册, 供块内渲染替换) */
  registerIdsDisplay(idsSource: string, displayChar: string): void {
    this.idsToDisplay.set(idsSource, displayChar);
  }

  /** 字符串中已映射的 IDS 表达式替换为显示字符 (真字符或 PUA, 块内渲染); 未映射保持原样 */
  renderIdsToPua(text: string): string {
    const IDS_OP = new Set([...IDS_OPERATORS]);
    const MAX_LEN = 32;
    let out = "";
    let i = 0;
    while (i < text.length) {
      if (IDS_OP.has(text[i])) {
        let matchedLen = 0;
        let replaced: string | null = null;
        for (let len = Math.min(MAX_LEN, text.length - i); len >= 1; len--) {
          const sub = text.slice(i, i + len);
          const display = this.idsToDisplay.get(sub);
          if (display !== undefined) { replaced = display; matchedLen = len; break; }
          const pua = this.idsToPua.get(sub);
          if (pua !== undefined) { replaced = String.fromCodePoint(pua); matchedLen = len; break; }
        }
        if (replaced !== null) {
          out += replaced;
          i += matchedLen;
          continue;
        }
      }
      out += text[i];
      i++;
    }
    return out;
  }

  /** 获取所有映射条目, 用于 .idsmd 序列化. 返回 [idsSource, pua, kageData | null][] */
  getAllKageEntries(): [string, number, string | null][] {
    const result: [string, number, string | null][] = [];
    for (const [ids, pua] of this.idsToPua) {
      result.push([ids, pua, this.kageCache.get(pua) || null]);
    }
    return result;
  }

  /** 清除所有字形映射和缓存 (用于"新建"操作) */
  clearAll(): void {
    this.idsToPua.clear();
    this.puaToIds.clear();
    this.svgCache.clear();
    this.kageCache.clear();
    this.nextPua = PUA_START;
    this.fontBuffer = null;
    this._ready = false;
    this._building = false;
    this._needsRebuild = false;
  }
}

/** 全局单例 */
export const glyphFontManager = new GlyphFontManager();
