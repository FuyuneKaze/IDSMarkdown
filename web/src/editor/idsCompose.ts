import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { IdsDatabase } from "./idsDatabase";
import { isIdeographic, isIdsOperator, idsOperatorArity, codePointAt, cpLen } from "./charUtils";
import { glyphFontManager } from "./glyphFontManager";

/**
 * IDS 自动合成插件 (C++ scanForCompose 移植)
 *
 * 扫描策略 (对齐 C++ Document::scanForCompose):
 *   1. 展平文档: glyph 节点 → '\0' 占位符, 记录 idsSource/kageData
 *   2. 从左到右扫描, 遇到 IDS 操作符即用 idsComponentLen 计算完整树长
 *   3. 验证每个部件 (表意文字 / glyph 占位符)
 *   4. 返回第一个合法表达式, 或全部表达式列表
 *
 * 触发: 键入文字后 appendTransaction, 或 compositionend
 */
export const IdsComposeExtension = Extension.create({
  name: "idsCompose",

  addProseMirrorPlugins() {
    const db = new IdsDatabase();
    let loaded = false;

    // ============================================================
    // 辅助函数
    // ============================================================

    /** 获取 IDS 子树长度 (字符串中占用的 code unit 数).
     *  遇到 BLOCK_SEP (block 边界) 返回 0, 阻止跨段落匹配. */
    const idsComponentLen = (text: string, pos: number): number => {
      if (pos >= text.length) return 0;
      if (text[pos] === BLOCK_SEP) return 0;
      const cp = codePointAt(text, pos);
      if (isIdsOperator(cp)) {
        const arity = idsOperatorArity(cp);
        let p = pos + 1;
        for (let k = 0; k < arity; k++) {
          const clen = idsComponentLen(text, p);
          if (clen === 0) return 0;
          p += clen;
        }
        return p - pos;
      }
      return cpLen(cp);
    };

    /** 验证完整的 IDS 表达式 */
    const validateIds = (text: string): boolean => {
      if (!text) return false;
      const firstCp = codePointAt(text, 0);
      if (!isIdsOperator(firstCp)) return false;
      try {
        const consumed = idsComponentLen(text, 0);
        return consumed > 0 && consumed === text.length;
      } catch {
        return false;
      }
    };

    // ============================================================
    // scanForward — C++ scanForCompose 的 JS 移植
    // ============================================================

    interface FlatEntry {
      docPos: number;       // 文档位置
      size: number;         // 占位大小 (1=普通字符, 2=代理对, nodeSize=glyph)
      text: string;         // 字符或 "\0"
      glyphSource: string;  // glyph 的 idsSource/kageData
    }

    interface ScanResult {
      from: number;
      to: number;
      idsSource: string;
    }

    // 哨兵字符: block 边界标记, idsComponentLen 遇到即终止
    const PUA_START = 0xE000;
    const PUA_END = 0xE8FF;
    const BLOCK_SEP = "\x01";

    /** 展平文档为 token 序列, 从左到右扫描 IDS 表达式 */
    const scanForward = (doc: any, startPos: number): ScanResult[] => {
      // 1. 展平文档
      const entries: FlatEntry[] = [];

      doc.nodesBetween(startPos, doc.content.size, (node: any, pos: number) => {
        if (pos + node.nodeSize <= startPos) return true;

        if (node.isText) {
          const text: string = node.text || "";
          const idsMark = node.marks?.find((m: any) => m.type.name === "idsMark");
          let i = 0;
          let dp = pos;
          while (i < text.length) {
            const cp = codePointAt(text, i);
            const len = cpLen(cp);
            if (idsMark && cp >= PUA_START && cp <= PUA_END) {
              // PUA 字符带 idsMark: 视为 glyph 占位符, 用 idsSource 参与外层 IDS 合成
              entries.push({
                docPos: dp,
                size: len,
                text: "\0",
                glyphSource: idsMark.attrs.idsSource || glyphFontManager.getIdsSource(cp) || "",
              });
            } else {
              entries.push({
                docPos: dp,
                size: len,
                text: text.slice(i, i + len),
                glyphSource: "",
              });
            }
            dp += len;
            i += len;
          }
        } else if (node.type.name === "idsGlyph") {
          entries.push({
            docPos: pos,
            size: node.nodeSize,
            text: "\0",
            glyphSource: (node.attrs as any).idsSource || "",
          });
        } else if (node.type.name === "kageGlyph") {
          entries.push({
            docPos: pos,
            size: node.nodeSize,
            text: "\0",
            glyphSource: (node.attrs as any).kageData || "",
          });
        } else if (node.type.name === "rubyBlock" || node.type.name === "doubleLine") {
          // 哨兵: 阻止 IDS 表达式跨注音/双行块合成 (否则 ⿰木+注音块+石 会吞掉块)
          entries.push({
            docPos: pos,
            size: 0,
            text: BLOCK_SEP,
            glyphSource: "",
          });
        } else if (node.isBlock) {
          // 插入 block 边界哨兵, 阻止 IDS 表达式跨段落/标题等
          entries.push({
            docPos: pos,
            size: 0,
            text: BLOCK_SEP,
            glyphSource: "",
          });
        }
        // 其他节点跳过

        return true;
      });

      if (entries.length < 3) return [];  // 至少需要 op + 2 component

      // flatStr 用于 idsComponentLen 扫描
      const flatStr = entries.map((e) => e.text).join("");
      // charToEntry: flatStr 字符索引 → entries 索引
      const charToEntry: number[] = [];
      for (let ei = 0; ei < entries.length; ei++) {
        for (let ci = 0; ci < entries[ei].text.length; ci++) {
          charToEntry.push(ei);
        }
      }

      const results: ScanResult[] = [];

      // 2. 从左到右扫描 IDS 操作符
      for (let i = 0; i < flatStr.length; ) {
        const cp = codePointAt(flatStr, i);
        const cpL = cpLen(cp);

        if (!isIdsOperator(cp)) {
          i += cpL;
          continue;
        }

        // 检查转义
        if (i > 0 && flatStr[i - 1] === "\\") {
          i += cpL;
          continue;
        }

        const arity = idsOperatorArity(cp);
        let compEnd = i + 1;
        let valid = true;

        for (let k = 0; k < arity; k++) {
          const compLen = idsComponentLen(flatStr, compEnd);
          if (compLen === 0 || compEnd + compLen > flatStr.length) {
            valid = false;
            break;
          }
          compEnd += compLen;
        }

        if (!valid) {
          i += cpL;
          continue;
        }

        // 3. 验证每个部件并构建 rawIds
        let rawIds = "";
        for (let j = i; j < compEnd; j++) {
          const ch = flatStr[j];
          const entry = entries[charToEntry[j]];

          if (ch === "\0") {
            // glyph 占位符
            if (!entry.glyphSource) {
              valid = false;
              break;
            }
            rawIds += entry.glyphSource;
          } else if (ch >= "\uD800" && ch <= "\uDBFF") {
            // 高位代理对
            if (
              j + 1 >= compEnd ||
              !(flatStr[j + 1] >= "\uDC00" && flatStr[j + 1] <= "\uDFFF")
            ) {
              valid = false;
              break;
            }
            const fullCp = codePointAt(flatStr, j);
            if (!isIdeographic(fullCp)) {
              valid = false;
              break;
            }
            rawIds += ch + flatStr[j + 1];
            j++; // 跳过低位代理
          } else if (!isIdeographic(ch.codePointAt(0) || 0)) {
            valid = false;
            break;
          } else {
            rawIds += ch;
          }
        }

        if (!valid || !validateIds(rawIds)) {
          i += cpL;
          continue;
        }

        // 4. 计算文档位置
        const firstEntry = entries[charToEntry[i]];
        const lastEntry = entries[charToEntry[compEnd - 1]];
        const from = firstEntry.docPos;
        const to = lastEntry.docPos + lastEntry.size;

        results.push({ from, to, idsSource: rawIds });
        i = compEnd; // 跳过已扫描的整个表达式
      }

      return results;
    };

    // ============================================================
    // composeSingle — 合成单个表达式, 返回替换节点或 null
    // ============================================================

    const composeSingle = (
      state: any,
      idsText: string,
    ): { node: any; unicode: string } | null => {
      const normalized = db.normalize(idsText);
      if (!normalized) return null;

      const unicode = db.lookup(normalized);
      if (unicode && unicode !== normalized) {
        // 已入 U: 返回 Unicode 字符; 注册显示映射 (供 ruby/双行块内渲染替换)
        glyphFontManager.registerIdsDisplay(normalized, unicode);
        if (normalized !== idsText) glyphFontManager.registerIdsDisplay(idsText, unicode);
        return { node: state.schema.text(unicode), unicode };
      }

      // 未入 U: 分配 PUA, 用 idsMark 包裹普通文本 (享受原生选中高亮)
      let svgData = "";
      const engine = (window as any).__kageEngine;
      if (engine?.ready) {
        try {
          svgData = engine.renderSvg(idsText) || "";
        } catch (e) {
          console.warn("[idsCompose] KAGE render failed:", e);
        }
      }

      let pua = -1;
      if (svgData) {
        pua = glyphFontManager.getOrCreatePua(idsText, svgData);
      }

      // KAGE 就绪且有 SVG → 使用 idsMark 包裹的普通文本
      if (pua > 0 && state.schema.marks.idsMark) {
        glyphFontManager.registerIdsDisplay(idsText, String.fromCodePoint(pua));
        const mark = state.schema.marks.idsMark.create({ idsSource: idsText, pua });
        const textNode = state.schema.text(String.fromCodePoint(pua), [mark]);
        return { node: textNode, unicode: "" };
      }

      // 兜底: idsGlyph 节点 (KAGE 未就绪 / 无 SVG / PUA 耗尽)
      if (pua > 0) glyphFontManager.registerIdsDisplay(idsText, String.fromCodePoint(pua));
      const glyphNode = state.schema.nodes.idsGlyph?.create({
        idsSource: idsText,
        svgData,
        unicode: "",
        pua,
      });
      if (!glyphNode) return null;
      return { node: glyphNode, unicode: "" };
    };

    // ============================================================
    // 字体重建调度 — 首次合成时分配 PUA 并重建字体, 后续直接复用
    // ============================================================

    let _fontRebuildTimer: any = null;

    const scheduleFontRebuild = () => {
      if (_fontRebuildTimer) return; // 已排期
      _fontRebuildTimer = setTimeout(async () => {
        _fontRebuildTimer = null;
        await glyphFontManager.buildFont();
        // 浏览器通过 FontFace.unicodeRange 自动为 PUA 码点匹配 IDSGlyphFont
      }, 100); // 延迟 100ms, 合并同一批次的多次合成
    };

    // ============================================================
    // 块内 IDS 扫描 — ruby/双行块内的表达式自动注册 (重新打开文件后
    // 块内合成字无需先在正文合成一遍)
    // ============================================================

    /** 扫描纯文本中的 IDS 表达式 (块内文本用; 无 glyph 占位符与 block 边界, 逻辑对齐 scanForward) */
    const scanIdsInPlainText = (text: string): string[] => {
      const results: string[] = [];
      let i = 0;
      while (i < text.length) {
        const cp = codePointAt(text, i);
        const cpL = cpLen(cp);
        if (!isIdsOperator(cp)) { i += cpL; continue; }
        if (i > 0 && text[i - 1] === "\\") { i += cpL; continue; }
        const arity = idsOperatorArity(cp);
        let compEnd = i + 1;
        let valid = true;
        for (let k = 0; k < arity; k++) {
          const compLen = idsComponentLen(text, compEnd);
          if (compLen === 0 || compEnd + compLen > text.length) { valid = false; break; }
          compEnd += compLen;
        }
        if (!valid) { i += cpL; continue; }
        // 部件验证 (对齐 scanForward): 每个码点必须是表意文字或嵌套运算符
        for (let j = i; j < compEnd; j++) {
          const c = codePointAt(text, j);
          const cl = cpLen(c);
          if (!isIdeographic(c)) { valid = false; break; }
          j += cl - 1;
        }
        const raw = text.slice(i, compEnd);
        if (!valid || !validateIds(raw)) { i += cpL; continue; }
        results.push(raw);
        i = compEnd;
      }
      return results;
    };

    /** 注册单个 IDS 表达式: 已入 U → 显示映射; 未入 U → KAGE 渲染分配 PUA */
    const registerIds = (idsText: string): boolean => {
      const normalized = db.normalize(idsText);
      if (!normalized) return false;

      const unicode = db.lookup(normalized);
      if (unicode && unicode !== normalized) {
        glyphFontManager.registerIdsDisplay(normalized, unicode);
        if (normalized !== idsText) glyphFontManager.registerIdsDisplay(idsText, unicode);
        return true;
      }

      const pua = glyphFontManager.getPua(idsText);
      if (pua > 0) {
        // 已分配 PUA (正文合成过): 补显示映射, 不重复 KAGE 渲染
        glyphFontManager.registerIdsDisplay(idsText, String.fromCodePoint(pua));
        return true;
      }

      const engine = (window as any).__kageEngine;
      if (!engine?.ready) return false;
      let svgData = "";
      try {
        svgData = engine.renderSvg(idsText) || "";
      } catch {
        return false;
      }
      if (!svgData) return false;
      const newPua = glyphFontManager.getOrCreatePua(idsText, svgData);
      if (newPua <= 0) return false;
      glyphFontManager.registerIdsDisplay(idsText, String.fromCodePoint(newPua));
      scheduleFontRebuild(); // 新 PUA → 字体需重建
      return true;
    };

    /** 扫描并注册文本中的全部表达式 */
    const registerIdsInText = (text: string): { changed: boolean; count: number } => {
      const exprs = scanIdsInPlainText(text);
      if (exprs.length === 0) return { changed: false, count: 0 };
      let changed = false;
      for (const ids of exprs) {
        if (registerIds(ids)) changed = true;
      }
      return { changed, count: exprs.length };
    };

    /** 遍历文档, 注册块内 IDS 表达式; 对含表达式的块 setNodeMarkup 强制重建 DOM
     *  (renderHTML 渲染时查映射, 重建后块内表达式才显示为合成字) */
    const scanAndMarkBlocks = (view: any): void => {
      if (!view || view.isDestroyed) return;
      const { doc } = view.state;
      const rebuild: number[] = [];
      let total = 0;

      doc.descendants((node: any, pos: number) => {
        if (node.type.name === "rubyBlock") {
          const a = node.attrs as { base: string; rt: string };
          const rb = registerIdsInText(a.base);
          const rr = registerIdsInText(a.rt);
          total += rb.count + rr.count;
          if (rb.count + rr.count > 0) rebuild.push(pos);
        } else if (node.type.name === "doubleLine") {
          const a = node.attrs as { text: string };
          const rd = registerIdsInText(a.text);
          total += rd.count;
          if (rd.count > 0) rebuild.push(pos);
        }
        return true;
      });

      if (rebuild.length === 0) {
        if (total > 0) console.log(`[idsCompose] scanAndMarkBlocks: registered ${total} expression(s), no rebuild needed`);
        return;
      }

      // setNodeMarkup 等长替换不偏移位置; attrs 加 _v 强制 DOM 重建 (pm-view 对 sameMarkup 相同 attrs 会跳过更新)
      const tr = view.state.tr;
      tr.setMeta("idsCompose", true);
      for (let i = rebuild.length - 1; i >= 0; i--) {
        const pos = rebuild[i];
        const node = tr.doc.nodeAt(pos);
        if (!node) continue;
        tr.setNodeMarkup(pos, null, { ...node.attrs, _v: ((node.attrs as any)._v || 0) + 1 });
      }
      try {
        view.dispatch(tr);
        console.log(`[idsCompose] scanAndMarkBlocks: registered ${total} expression(s), rebuilt ${rebuild.length} block(s)`);
      } catch (e: any) {
        if (!e?.message?.includes("mismatched transaction")) throw e;
        console.warn("[idsCompose] scanAndMarkBlocks: state changed, skipping");
      }
    };

    // ============================================================
    // composeEntireDocument — 初始全文档扫描合成
    // ============================================================

    const composeEntireDocument = (view: any) => {
      // 重试循环: setTimeout 异步调用时 state 可能已被 appendTransaction 等改变
      for (let attempt = 0; attempt < 5; attempt++) {
        const stateAtStart = view.state;
        const { doc } = stateAtStart;

        console.log(`[idsCompose] composeEntireDocument attempt=${attempt}, docSize=${doc.content.size}, stateId=${(stateAtStart as any).$$hash || "?"}`);

        // 将文档转为文本摘要辅助排查
        if (attempt === 0) {
          const textSample = doc.textContent.slice(0, 200);
          console.log(`[idsCompose] composeEntireDocument text sample: "${textSample}"`);
        }

        const results = scanForward(doc, 0);
        if (results.length === 0) {
          console.log("[idsCompose] composeEntireDocument: no expressions found");
          return;
        }

        console.log(`[idsCompose] composeEntireDocument: found ${results.length} expressions:`, results.map(r => r.idsSource).join(", "));

        // 从后往前替换 (避免位置偏移)
        const tr = stateAtStart.tr;
        let composed = 0;

        for (let i = results.length - 1; i >= 0; i--) {
          const r = results[i];
          const c = composeSingle(stateAtStart, r.idsSource);
          if (!c) {
            console.log(`[idsCompose]   SKIP [${r.from},${r.to}] "${r.idsSource}" — composeSingle returned null`);
            continue;
          }

          tr.setMeta("idsCompose", true);
          tr.replaceWith(r.from, r.to, c.node);
          composed++;
          console.log(`[idsCompose]   composed [${r.from},${r.to}] "${r.idsSource}" → ${c.unicode || "glyph"}`);
        }

        if (composed > 0) {
          // 检查创建 tr 的 state 是否与当前 view.state 一致
          if (stateAtStart !== view.state) {
            console.warn(`[idsCompose] STATE MISMATCH before dispatch! tr created from state with docSize=${doc.content.size}, current view.state docSize=${view.state.doc.content.size}`);
          }
          try {
            view.dispatch(tr);
            scheduleFontRebuild();
            console.log(`[idsCompose] initial scan composed ${composed} expressions`);
            return;
          } catch (e: any) {
            console.warn(`[idsCompose] dispatch failed (attempt ${attempt}):`, e.message);
            if (attempt < 4 && e?.message?.includes("mismatched transaction")) {
              console.warn(`[idsCompose] composeEntireDocument: state changed, retrying...`);
              continue;
            }
            throw e;
          }
        }
        return;
      }
    };

    // ============================================================
    // recomposeGlyphNodes — KAGE 就绪后补充 SVG
    // ============================================================

    const recomposeGlyphNodes = (view: any) => {
      const engine = (window as any).__kageEngine;
      if (!engine?.ready) return;

      const { doc } = view.state;
      type GlyphTarget = { from: number; to: number; idsSource: string; kageData: string; isKageNode: boolean };
      const targets: GlyphTarget[] = [];

      doc.descendants((node: any, pos: number) => {
        if (node.type.name === "idsGlyph") {
          const attrs = node.attrs as { idsSource: string; svgData: string };
          if (attrs.idsSource && !attrs.svgData) {
            targets.push({ from: pos, to: pos + node.nodeSize, idsSource: attrs.idsSource, kageData: "", isKageNode: false });
          }
        }
        if (node.type.name === "kageGlyph") {
          const attrs = node.attrs as { kageData: string; glyphName: string };
          if (attrs.kageData) {
            // kageGlyph 有 glyphName 则用其做 idsSource, 否则用 kageData 哈希
            const idsSource = attrs.glyphName || `_kage_${attrs.kageData.slice(0, 32).replace(/[^a-zA-Z0-9]/g, "")}`;
            targets.push({ from: pos, to: pos + node.nodeSize, idsSource, kageData: attrs.kageData, isKageNode: true });
          }
        }
        return true;
      });

      if (targets.length === 0) {
        console.log("[idsCompose] recomposeGlyphNodes: no targets found");
        return;
      }

      console.log(`[idsCompose] recomposeGlyphNodes: found ${targets.length} targets (${targets.filter(t => t.isKageNode).length} kageGlyph)`);

      const tr = view.state.tr;
      let updated = 0;
      for (let i = targets.length - 1; i >= 0; i--) {
        const t = targets[i];
        let svgData = "";
        try {
          if (t.kageData) {
            svgData = engine.renderKageData(t.kageData) || "";
          } else {
            svgData = engine.renderSvg(t.idsSource) || "";
          }
        } catch (e) {
          console.warn("[idsCompose] recompose render failed:", e);
        }
        if (svgData) {
          const pua = t.kageData
            ? glyphFontManager.updatePuaSvg(t.idsSource, svgData, t.kageData)
            : glyphFontManager.getOrCreatePua(t.idsSource, svgData);
          if (pua > 0 && view.state.schema.marks.idsMark) {
            const mark = view.state.schema.marks.idsMark.create({ idsSource: t.idsSource, pua });
            const textNode = view.state.schema.text(String.fromCodePoint(pua), [mark]);
            tr.setMeta("idsCompose", true);
            tr.replaceWith(t.from, t.to, textNode);
          } else {
            // PUA 耗尽或 mark 不可用 → idsGlyph 兜底
            const glyphNode = view.state.schema.nodes.idsGlyph?.create({
              idsSource: t.idsSource, svgData, unicode: "", pua,
            });
            if (glyphNode) {
              tr.setMeta("idsCompose", true);
              tr.replaceWith(t.from, t.to, glyphNode);
            }
          }
          updated++;
        }
      }

      if (updated > 0) {
        try {
          view.dispatch(tr);
          scheduleFontRebuild();
          console.log(`[idsCompose] recompose updated ${updated} glyphs`);
        } catch (e: any) {
          if (e?.message?.includes("mismatched transaction")) {
            console.warn("[idsCompose] recomposeGlyphNodes: state changed, skipping (will retry on next recompose)");
          } else {
            throw e;
          }
        }
      }
    };

    // ============================================================
    // tryComposeAtCursor — 找离光标最近的表达式并合成
    // ============================================================

    const tryComposeAtCursor = (
      state: any,
      desc: string,
      overridePos?: number,
    ) => {
      const cursorPos = overridePos ?? state.selection.from;
      console.group(`[idsCompose] tryComposeAtCursor(${desc}) cursor=${cursorPos}`);

      // 扫描整个文档, 找 to 最接近光标 (但不超过) 的表达式
      const results = scanForward(state.doc, 0);
      console.log(`  scanForward found ${results.length} expressions`);

      if (results.length === 0) {
        console.log("  -> null (no expressions)");
        console.groupEnd();
        return null;
      }

      // 找 to ≤ cursorPos 且 to 最大的那个 (离光标最近的)
      let best: ScanResult | null = null;
      for (const r of results) {
        if (r.to > cursorPos) continue; // 在光标之后, 跳过
        if (!best || r.to > best.to) best = r;
      }

      if (!best) {
        console.log(`  -> null (no expression ends before cursor ${cursorPos})`);
        for (const r of results) {
          console.log(`    candidate [${r.from},${r.to}] "${r.idsSource}" (to > cursor, skip)`);
        }
        console.groupEnd();
        return null;
      }

      // 光标必须在表达式末尾附近 (容差 1 位置)
      if (cursorPos - best.to > 1) {
        console.log(`  -> null (cursor too far from expression end: to=${best.to}, cursor=${cursorPos})`);
        console.groupEnd();
        return null;
      }

      console.log(`  best: [${best.from},${best.to}] "${best.idsSource}"`);

      const c = composeSingle(state, best.idsSource);
      if (!c) {
        console.log("  -> null (composeSingle failed)");
        console.groupEnd();
        return null;
      }

      const tr = state.tr;
      tr.setMeta("idsCompose", true);
      tr.replaceWith(best.from, best.to, c.node);
      console.log(`  -> replaceWith [${best.from},${best.to}] ${c.unicode || "glyph"}`);
      console.groupEnd();
      return tr;
    };

    // ============================================================
    // Plugin
    // ============================================================

    let pluginView: any = null;

    return [
      new Plugin({
        key: new PluginKey("idsCompose"),

        view(editorView) {
          pluginView = editorView;
          const loadData = async () => {
            console.log("[idsCompose] loading IDS database...");
            const files = ["ids_lv0.txt", "ids_lv1.txt", "ids_lv2.txt", "ids_lv4.txt"];
            for (const fn of files) {
              try {
                const resp = await fetch(`/${fn}`);
                if (resp.ok) {
                  const text = await resp.text();
                  db.load(text);
                  console.log(`[idsCompose]   ${fn} loaded (${db.size} entries so far)`);
                }
              } catch {
                console.warn(`[idsCompose] failed to load ${fn}`);
              }
            }
            loaded = true;
            console.log(`[idsCompose] database ready: ${db.size} IDS entries`);

            try {
              composeEntireDocument(editorView);
            } catch (e) {
              console.warn("[idsCompose] initial scan error:", e);
            }
            try {
              scanAndMarkBlocks(editorView);
            } catch (e) {
              console.warn("[idsCompose] initial block scan error:", e);
            }

            let recomposeRetries = 0;

            (window as any).__recomposeIds = (optView?: any) => {
              if (!loaded) {
                console.log("[idsCompose] __recomposeIds: database not loaded, retrying in 300ms (attempt " + (recomposeRetries + 1) + ")");
                if (recomposeRetries < 10) {
                  recomposeRetries++;
                  setTimeout(() => (window as any).__recomposeIds?.(optView), 300);
                } else {
                  console.warn("[idsCompose] __recomposeIds: gave up after 10 retries");
                }
                return;
              }
              recomposeRetries = 0;
              // 优先使用调用方传入的 view (避免 React StrictMode 下 pluginView 指向旧实例)
              const view = optView || pluginView;
              if (!view) {
                console.warn("[idsCompose] __recomposeIds: view is null, cannot recompose");
                return;
              }
              try {
                console.log(`[idsCompose] __recomposeIds: starting (optView=${!!optView}, docSize=${view.state.doc.content.size})`);
                composeEntireDocument(view);
                recomposeGlyphNodes(view);
                scanAndMarkBlocks(view);
                console.log("[idsCompose] __recomposeIds: done");
              } catch (e) {
                console.warn("[idsCompose] recompose error:", e);
              }
            };

            // 块扫描 hook: 编辑 ruby/双行块内容后调用, 即时注册块内新 IDS 表达式
            (window as any).__scanBlocks = (optView?: any) => {
              const view = optView || pluginView;
              if (!view) return;
              try {
                scanAndMarkBlocks(view);
              } catch (e) {
                console.warn("[idsCompose] __scanBlocks error:", e);
              }
            };

            if ((window as any).__kageEngine?.ready) {
              try {
                recomposeGlyphNodes(editorView);
              } catch (e) {
                console.warn("[idsCompose] initial recompose error:", e);
              }
            }
          };
          loadData();

          return {};
        },

        props: {
          handleDOMEvents: {
            compositionend: (view: any, _event: Event) => {
              setTimeout(() => {
                if (!loaded || !pluginView || view.isDestroyed) return;
                const tr = tryComposeAtCursor(view.state, "compositionend");
                if (tr) {
                  try {
                    view.dispatch(tr);
                    scheduleFontRebuild();
                    view.focus();
                  } catch (e: any) {
                    if (!e?.message?.includes("mismatched transaction")) throw e;
                  }
                }
              }, 0);
              return false;
            },
          },

          decorations(state: any) {
            const { from, to } = state.selection;
            if (from === to) return DecorationSet.empty;

            const decos: any[] = [];
            state.doc.nodesBetween(from, to, (node: any, pos: number) => {
              // idsGlyph 已改用 PUA 字符文本渲染, 原生选中即可, 不需要装饰器模拟
              if (node.type.name === "kageGlyph") {
                decos.push(
                  Decoration.node(pos, pos + node.nodeSize, {
                    class: "glyph-selected",
                  }),
                );
              }
            });
            return DecorationSet.create(state.doc, decos);
          },
        },

        appendTransaction(transactions, oldState, newState) {
          if (!loaded) return null;

          let docChanged = false;
          let selOnlyChanged = false;
          for (const tr of transactions) {
            if (tr.docChanged && !tr.getMeta("idsCompose")) {
              docChanged = true;
              console.log(`[idsCompose] appendTransaction: detected docChanged (meta=${JSON.stringify(Object.keys(tr.getMeta("idsCompose") ? {} : {}))}), oldDocSize=${oldState.doc.content.size} → newDocSize=${newState.doc.content.size}`);
            }
            if (!tr.docChanged && tr.selectionSet) {
              selOnlyChanged = true;
            }
          }

          if (docChanged) {
            delete (window as any).__expandRange;
            const tr = tryComposeAtCursor(newState, "append");
            if (tr) {
              console.log("[idsCompose] appendTransaction: returning compose transaction");
              scheduleFontRebuild();
            } else {
              console.log("[idsCompose] appendTransaction: tryComposeAtCursor returned null");
            }
            return tr;
          }

          if (selOnlyChanged) {
            const expandRange = (window as any).__expandRange as
              | { from: number; to: number }
              | undefined;
            if (!expandRange) return null;

            const oldPos = oldState.selection.from;
            const newPos = newState.selection.from;
            if (oldPos === newPos) return null;

            const { from, to } = expandRange;
            if (
              oldPos >= to - 1 &&
              oldPos <= to + 1 &&
              (newPos < from || newPos > to)
            ) {
              delete (window as any).__expandRange;
              const tr = tryComposeAtCursor(newState, "expandAway", to);
              if (tr) scheduleFontRebuild();
              return tr;
            }
          }

          return null;
        },
      }),
    ];
  },
});
