/**
 * markdownStylePlugin — 源码模式 Markdown 格式化
 *
 * 文档中保留 **bold** / *italic* / `code` / # heading 等源文本标记，
 * 通过 Decoration.inline 渲染视觉样式。
 *
 * 标记可见性: 光标在范围内 → 可见(font-size:inherit, opacity:0.38)
 *              光标不在范围内 → 隐藏(font-size:0, opacity:0, 零宽度)
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";

const MD_STYLE_KEY = new PluginKey("markdownStyle");

// ============================================================
// 模式定义
// ============================================================

interface SyntaxDef {
  name: string;
  open: string;
  close: string;
}

const INLINE_DEFS: SyntaxDef[] = [
  { name: "bold-italic", open: "***", close: "***" },
  { name: "bold", open: "**", close: "**" },
  { name: "italic", open: "*", close: "*" },
  { name: "code", open: "`", close: "`" },
];

// 标题: #{1,4} 后跟空格 (m 标志匹配行首, 允许标题行后跟更多内容)
const HEADING_RE = /^(#{1,4})\s+(.+)$/m;

// 正则缓存: 按 open/close 长度生成
function buildRegex(open: string, close: string): RegExp {
  const eo = escapeRegex(open);
  const ec = escapeRegex(close);
  return new RegExp(`${eo}(.+?)${ec}`, "g");
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// ============================================================
// 扫描
// ============================================================

// 连续文本 run: 合并相邻 text nodes (如 **PUA字** 中 PUA 是独立 text node),
// text 为拼接文本, pos[i] 为第 i 个字符的绝对位置
interface TextRun {
  text: string;
  pos: number[];
}

// ============================================================
// Plugin
// ============================================================

export const MarkdownStyle = Extension.create({
  name: "markdownStyle",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: MD_STYLE_KEY,

        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, oldSet, _oldState, newState) {
            if (!tr.selectionSet && !tr.docChanged) return oldSet;

            const cursorPos = newState.selection.empty ? newState.selection.from : -1;
            return computeDecorations(newState, cursorPos);
          },
        },

        props: {
          decorations(state) {
            return MD_STYLE_KEY.getState(state) ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});

// ============================================================
// Decoration 计算
// ============================================================

interface Range {
  from: number;
  to: number;
}

function computeDecorations(state: any, cursorPos: number): DecorationSet {
  const decos: any[] = [];
  const { doc } = state;

  // 收集所有光标所在 ranges (用于判断标记可见性)
  const cursorRanges: Range[] = [];

  // ── 行内 pattern (按段落扫描, 合并相邻 text nodes, 支持跨节点匹配) ──
  doc.descendants((node: any, nodePos: number) => {
    if (node.type.name !== "paragraph") return true;
    if (node.content.size === 0) return true;

    // 收集段落内连续文本 runs。ruby/双行块不切断 run (其 renderText 文本参与匹配,
    // 块内无 doc 位置, 字符位置全部填块起始, 使 Decoration 边界不越过 base+1)
    const runs: TextRun[] = [];
    let cur: TextRun | null = null;
    node.forEach((child: any, offset: number) => {
      if (child.isText) {
        if (!cur) { cur = { text: "", pos: [] }; runs.push(cur); }
        const t = child.text || "";
        const base = nodePos + 1 + offset;
        for (let i = 0; i < t.length; i++) {
          cur.text += t[i];
          cur.pos.push(base + i);
        }
      } else if (child.type.name === "rubyBlock" || child.type.name === "doubleLine") {
        if (!cur) { cur = { text: "", pos: [] }; runs.push(cur); }
        const t = child.type.name === "rubyBlock"
          ? (child.attrs.base || "")
          : (child.attrs.text || "");
        const base = nodePos + 1 + offset;
        for (let i = 0; i < t.length; i++) {
          cur.text += t[i];
          cur.pos.push(base);
        }
      } else {
        cur = null;
      }
    });

    // 已覆盖位置 (避免重叠匹配)
    const covered = new Set<number>();
    for (const run of runs) {
      for (const def of INLINE_DEFS) {
        const re = buildRegex(def.open, def.close);
        for (const m of run.text.matchAll(re)) {
          const idx = m.index!;
          const mFrom = run.pos[idx];
          const mTo = run.pos[idx + m[0].length - 1] + 1;
          // 检查是否与已有匹配重叠
          let overlap = false;
          for (let p = mFrom; p < mTo; p++) {
            if (covered.has(p)) { overlap = true; break; }
          }
          if (overlap) continue;
          for (let p = mFrom; p < mTo; p++) covered.add(p);

          const contentFrom = run.pos[idx + def.open.length];
          const contentTo = run.pos[idx + m[0].length - def.close.length - 1] + 1;
          const styleClass = `md-style-${def.name}`;
          // 内容装饰 (inline 跨 atom 节点时不应用, 块需补节点装饰)
          decos.push(Decoration.inline(contentFrom, contentTo, { class: styleClass }));
          doc.nodesBetween(contentFrom, contentTo, (bn: any, bpos: number) => {
            if (bn.type.name === "rubyBlock" || bn.type.name === "doubleLine") {
              decos.push(Decoration.node(bpos, bpos + bn.nodeSize, { class: styleClass }));
              return false;
            }
            return true;
          });

          // 标记装饰 (根据光标位置决定显隐)
          const inRange = cursorPos >= mFrom && cursorPos <= mTo;
          const markerClass = inRange ? "md-marker md-marker-active" : "md-marker";
          decos.push(Decoration.inline(mFrom, contentFrom, { class: markerClass }));
          decos.push(Decoration.inline(contentTo, mTo, { class: markerClass }));

          if (inRange) {
            cursorRanges.push({ from: mFrom, to: mTo });
          }
        }
      }
    }
    return true;
  });

  // ── 标题 ──
  doc.descendants((node: any, nodePos: number) => {
    if (node.type.name !== "paragraph") return true;
    const text = node.textContent || "";
    const m = text.match(HEADING_RE);
    if (!m) return true;

    // 段落内容从 nodePos + 1 开始; 若段首有 ruby/双行块 (textContent 不含块文本,
    // 但 doc 位置被块占 1 个), 标记位置需越过所有前导块, 否则 marker 装饰会贴到块元素上。
    // 注意: Fragment 无迭代器, 必须用 forEach
    let leadingBlocks = 0;
    let hitNonBlock = false;
    node.forEach((ch: any) => {
      if (hitNonBlock) return;
      if (ch.type.name === "rubyBlock" || ch.type.name === "doubleLine") leadingBlocks++;
      else hitNonBlock = true;
    });
    const textNodeStart = nodePos + 1 + leadingBlocks;
    const markerEnd = textNodeStart + m[1].length; // 标记结束位置
    const contentFrom = textNodeStart + m[0].indexOf(m[2]); // 内容开始
    // contentTo 取段落末尾而非 textNodeStart + m[0].length: node.textContent 不含
    // ruby/双行块文本 (TipTap renderText 映射到 schema.toText, 非 spec.leafText),
    // 块在 doc 中占 1 个位置, 按 m[0].length 算会截断在最后一块之前 → 标题格式覆盖不到块。
    // 标题匹配整段, 段末即标题行结束
    const contentTo = nodePos + node.nodeSize;

    const level = m[1].length;
    const styleClass = `md-style-heading md-style-h${level}`;
    const inRange = cursorPos >= textNodeStart && cursorPos <= contentTo;
    const markerClass = inRange ? "md-marker md-marker-active" : "md-marker";

    // 内容装饰
    decos.push(Decoration.inline(contentFrom, contentTo, { class: styleClass }));
    // 标记装饰
    decos.push(Decoration.inline(textNodeStart, markerEnd, { class: markerClass }));

    if (inRange) {
      cursorRanges.push({ from: textNodeStart, to: contentTo });
    }
    return true;
  });

  return DecorationSet.create(doc, decos);
}
