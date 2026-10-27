import { Node } from "@tiptap/core";
import { IdsGlyphNodeView } from "./idsGlyphView";

/**
 * idsGlyph: 内联原子节点，承载 IDS 合成字形
 *
 * 属性:
 *   idsSource  — 原始 IDS 表达式文本，如 "⿰石另"
 *   svgData    — KAGE 渲染的 SVG 字符串（尚无时为 ""）
 *   unicode    — 对应 Unicode 字符（如已编码则为该字符，否则为 ""）
 *
 * 行为:
 *   - atom: true — 整体选中，不可编辑内部
 *   - 退格删除: 还原为 idsSource 文本
 */
export const IdsGlyphNode = Node.create({
  name: "idsGlyph",

  group: "inline",
  inline: true,
  atom: true,
  selectable: false,

  addAttributes() {
    return {
      idsSource: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-ids-source") || "",
        renderHTML: (attrs) => ({ "data-ids-source": attrs.idsSource }),
      },
      svgData: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-svg") || "",
        renderHTML: (attrs) => ({ "data-svg": attrs.svgData }),
      },
      unicode: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-unicode") || "",
        renderHTML: (attrs) => ({ "data-unicode": attrs.unicode }),
      },
      pua: {
        default: -1,
        parseHTML: (el) => {
          const v = el.getAttribute("data-pua");
          return v ? parseInt(v, 10) : -1;
        },
        renderHTML: (attrs) => {
          if (attrs.pua > 0) return { "data-pua": String(attrs.pua) };
          return {};
        },
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-type='ids-glyph']" }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = node.attrs as { idsSource: string; svgData: string; unicode: string; pua: number };

    if (attrs.unicode) {
      return [
        "span",
        { "data-type": "ids-glyph", ...HTMLAttributes },
        attrs.unicode,
      ];
    }

    // PUA 码点已分配 → 渲染为字体字符 (选中表现与普通文字一致)
    if (attrs.pua > 0) {
      return [
        "span",
        {
          "data-type": "ids-glyph",
          class: "ids-glyph",
          style: `font-family: IDSGlyphFont, "IDSGlyphFont-fallback"`,
          ...HTMLAttributes,
        },
        String.fromCodePoint(attrs.pua),
      ];
    }

    if (attrs.svgData) {
      return [
        "span",
        {
          "data-type": "ids-glyph",
          class: "ids-glyph",
          ...HTMLAttributes,
        },
        attrs.idsSource || "",
      ];
    }

    return [
      "span",
      {
        "data-type": "ids-glyph",
        class: "ids-glyph ids-glyph-placeholder",
        title: attrs.idsSource,
        ...HTMLAttributes,
      },
      `[${attrs.idsSource}]`,
    ];
  },

  // 纯文本序列化: 还原为 idsSource, 避免复制时出现空白/多余换行
  renderText({ node }: any) {
    return node.attrs.unicode || node.attrs.idsSource || "";
  },

  addNodeView() {
    // TipTap v3 / ProseMirror 新版: NodeView 工厂接收单个 props 对象
    // props = { node, view, getPos, decorations, innerDecorations, ... }
    return (props: any) => {
      const { node, view, getPos, decorations, innerDecorations } = props;
      console.log(`[IdsGlyph] NodeView: node.type=${node?.type?.name}, attrs=`, JSON.stringify(node?.attrs));
      return new IdsGlyphNodeView(node, view, getPos, decorations, innerDecorations);
    };
  },
});
