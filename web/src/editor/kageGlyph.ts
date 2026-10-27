import { Node } from "@tiptap/core";
import { KageGlyphNodeView } from "./kageGlyphView";

/**
 * kageGlyph: 内联原子节点，承载原始 KAGE 笔画数据字形
 *
 * 属性:
 *   kageData  — 原始 KAGE 笔画数据, 如 "1:0:2:40:37:143:37$..."
 *   svgData   — 渲染后的 SVG 字符串（尚无时为 ""）
 *   glyphName — 字形名（可选, 用于 placeholder 显示）
 *
 * 与 idsGlyph 的区别:
 *   idsGlyph 通过 IDS 表达式合成 (需要 buildComposite)
 *   kageGlyph 直接使用原始笔画数据渲染 (renderKageData)
 */
export const KageGlyphNode = Node.create({
  name: "kageGlyph",

  group: "inline",
  inline: true,
  atom: true,
  selectable: false,

  addAttributes() {
    return {
      kageData: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-kage-data") || "",
        renderHTML: (attrs) => ({ "data-kage-data": attrs.kageData }),
      },
      svgData: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-svg") || "",
        renderHTML: (attrs) => ({ "data-svg": attrs.svgData }),
      },
      glyphName: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-glyph-name") || "",
        renderHTML: (attrs) => ({ "data-glyph-name": attrs.glyphName }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-type='kage-glyph']" }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = node.attrs as { kageData: string; svgData: string; glyphName: string };

    if (attrs.svgData) {
      return [
        "span",
        { "data-type": "kage-glyph", ...HTMLAttributes },
        attrs.glyphName || "[KAGE]",
      ];
    }

    return [
      "span",
      {
        "data-type": "kage-glyph",
        class: "ids-glyph ids-glyph-placeholder",
        title: attrs.glyphName || attrs.kageData,
        ...HTMLAttributes,
      },
      attrs.glyphName ? `[${attrs.glyphName}]` : "[KAGE]",
    ];
  },

  renderText({ node }: any) {
    return node.attrs.glyphName || "[KAGE]";
  },

  addNodeView() {
    return (props: any) => {
      const { node, view, getPos, decorations, innerDecorations } = props;
      return new KageGlyphNodeView(node, view, getPos, decorations, innerDecorations);
    };
  },
});
