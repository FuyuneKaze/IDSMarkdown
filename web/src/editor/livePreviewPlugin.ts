/**
 * livePreviewPlugin — Obsidian 风格实时预览
 *
 * 当光标位于格式化范围内时，显示淡化的 Markdown 语法标记。
 * 支持: bold(**, **), italic(*, *), code(`, `), heading(#, ##, ###, ####)
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";

const LIVE_PREVIEW_KEY = new PluginKey("livePreview");

interface SyntaxPair {
  start: string;
  end: string;
}

const INLINE_SYNTAX: Record<string, SyntaxPair> = {
  bold: { start: "**", end: "**" },
  italic: { start: "*", end: "*" },
  code: { start: "`", end: "`" },
};

const HEADING_MARKER: Record<number, string> = {
  1: "# ",
  2: "## ",
  3: "### ",
  4: "#### ",
};

/**
 * 字符级位置遍历: 找到光标所在 mark 的起止位置。
 * 从光标处向左右逐字符检查 mark 是否连续存在。
 */
function findInlineMarkRange(
  doc: any,
  pos: number,
  markName: string
): { from: number; to: number } | null {
  const $pos = doc.resolve(pos);

  // 先检查光标处是否有这个 mark
  const hasMark = $pos.marks().some((m: any) => m.type.name === markName);
  if (!hasMark) return null;

  // 向左扫描
  let from = pos;
  while (from > 0) {
    try {
      const prev = doc.resolve(from - 1);
      if (!prev.marks().some((m: any) => m.type.name === markName)) break;
      from--;
    } catch {
      break;
    }
  }

  // 向右扫描
  let to = pos;
  const docSize = doc.content.size;
  while (to < docSize) {
    try {
      const next = doc.resolve(to + 1);
      if (!next.marks().some((m: any) => m.type.name === markName)) break;
      to++;
    } catch {
      break;
    }
  }

  if (from >= to) return null;
  return { from, to };
}

/** 创建淡化标记的 DOM 元素 */
function makeMarker(text: string, extraClass: string): HTMLElement {
  const span = document.createElement("span");
  span.className = `live-preview-marker ${extraClass}`;
  span.textContent = text;
  span.contentEditable = "false";
  return span;
}

export const LivePreview = Extension.create({
  name: "livePreview",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: LIVE_PREVIEW_KEY,

        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, oldSet, _oldState, newState) {
            // 选区或文档变化时重新计算
            if (!tr.selectionSet && !tr.docChanged) return oldSet;

            const { selection } = newState;
            if (!selection.empty) return DecorationSet.empty;

            const cursorPos = selection.from;
            const { doc } = newState;
            const decos: any[] = [];

            // ── 行内标记 ──
            for (const [markName, syntax] of Object.entries(INLINE_SYNTAX)) {
              const range = findInlineMarkRange(doc, cursorPos, markName);
              if (!range) continue;
              console.log(`[livePreview] ${markName} range: [${range.from}, ${range.to}]`);

              decos.push(
                Decoration.widget(range.from, () => makeMarker(syntax.start, `live-preview-marker-${markName}`))
              );
              decos.push(
                Decoration.widget(range.to, () => makeMarker(syntax.end, `live-preview-marker-${markName}`))
              );
            }

            // ── 标题标记 ──
            const $cp = doc.resolve(cursorPos);
            for (let d = $cp.depth; d >= 0; d--) {
              const node = $cp.node(d);
              if (node.type.name === "heading") {
                const level = node.attrs.level as number;
                const marker = HEADING_MARKER[level];
                if (marker) {
                  const hStart = $cp.start(d) + 1;
                  console.log(`[livePreview] heading H${level} at ${hStart}`);
                  decos.push(
                    Decoration.widget(hStart, () => makeMarker(marker, "live-preview-marker-heading"))
                  );
                }
                break;
              }
            }

            console.log(`[livePreview] total decorations: ${decos.length}, cursor at ${cursorPos}`);
            return DecorationSet.create(doc, decos);
          },
        },

        props: {
          decorations(state) {
            return LIVE_PREVIEW_KEY.getState(state) ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});
