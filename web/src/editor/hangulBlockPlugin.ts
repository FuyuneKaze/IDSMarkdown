/**
 * hangulBlockPlugin — 竖排模式下古谚文 Jamo 音节包裹
 *
 * 竖排时浏览器无法正确组合 Jamo 字母成块 (字体缺竖排 OT 表)，
 * 此插件将每个 Jamo 序列包裹为 writing-mode: horizontal-tb 的容器，
 * 使韩文字母在内部按横排方式组合。
 */

import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "prosemirror-state";
import { Decoration, DecorationSet } from "prosemirror-view";

const HANGUL_BLOCK_KEY = new PluginKey("hangulBlock");

// ── 当前书写模式 (由 App.tsx 同步) ──
let currentWritingMode: "horizontal" | "vertical" = "horizontal";
let lastApplied: "horizontal" | "vertical" = "horizontal";

export function setHangulWritingMode(mode: "horizontal" | "vertical"): void {
  currentWritingMode = mode;
}

// ── Unicode 范围判断 ──

function isLeadingJamo(cp: number): boolean {
  return (cp >= 0x1100 && cp <= 0x115F) || // Hangul Jamo Choseong
         (cp >= 0xA960 && cp <= 0xA97C);   // Hangul Jamo Extended-A Choseong
}

function isJamo(cp: number): boolean {
  return (cp >= 0x1100 && cp <= 0x11FF) ||  // Hangul Jamo
         (cp >= 0xA960 && cp <= 0xA97F) ||  // Hangul Jamo Extended-A
         (cp >= 0xD7B0 && cp <= 0xD7FF);    // Hangul Jamo Extended-B
}

function isSyllable(cp: number): boolean {
  return (cp > 0xAC00 && cp <= 0xD7AF);
}

function charLen(cp: number): number {
  return cp > 0xFFFF ? 2 : 1;
}

// ── 音节扫描 ──

interface Syllable {
  from: number;
  to: number;
}

function scanSyllables(text: string, nodePos: number): Syllable[] {
  const syllables: Syllable[] = [];
  let i = 0;

  while (i < text.length) {
    const cp = text.codePointAt(i)!;
    const clen = charLen(cp);

    if (!isJamo(cp)) {
      i += clen;
      continue;
    }

    if (isLeadingJamo(cp) || isSyllable(cp)) {
      // 初声开头 → 新音节开始
      const start = i;
      i += clen;
      // 读取中声 + 终声
      while (i < text.length) {
        const nextCp = text.codePointAt(i)!;
        if (isJamo(nextCp) && !isLeadingJamo(nextCp)) {
          i += charLen(nextCp);
        } else {
          break;
        }
      }
      syllables.push({ from: nodePos + start, to: nodePos + i });
    } else {
      // 孤立的中声或终声/音节 → 单独包裹
      syllables.push({ from: nodePos + i, to: nodePos + i + clen });
      i += clen;
    }
  }

  return syllables;
}

// ── Extension ──

function computeDecorations(state: any): DecorationSet {
  if (currentWritingMode !== "vertical") {
    return DecorationSet.empty;
  }

  const decos: any[] = [];
  const { doc } = state;

  doc.descendants((node: any, nodePos: number) => {
    if (!node.isText) return true;
    const text: string = node.text || "";
    if (!text) return true;

    const syllables = scanSyllables(text, nodePos);
    for (const s of syllables) {
      decos.push(Decoration.inline(s.from, s.to, { class: "hangul-block" }));
    }
    return true;
  });

  return DecorationSet.create(doc, decos);
}

export const HangulBlock = Extension.create({
  name: "hangulBlock",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: HANGUL_BLOCK_KEY,

        state: {
          init() {
            return DecorationSet.empty;
          },
          apply(tr, oldSet, _oldState, newState) {
            const modeChanged = currentWritingMode !== lastApplied;
            lastApplied = currentWritingMode;

            if (!tr.selectionSet && !tr.docChanged && !modeChanged) return oldSet;
            return computeDecorations(newState);
          },
        },

        props: {
          decorations(state) {
            return HANGUL_BLOCK_KEY.getState(state) ?? DecorationSet.empty;
          },
        },
      }),
    ];
  },
});
