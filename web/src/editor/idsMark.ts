import { Mark } from "@tiptap/core";

/**
 * idsMark: 包裹 PUA 字符的 ProseMirror Mark
 *
 * PUA 字符是普通文字（非 atom 节点），因此具有原生文本选中行为。
 * Mark 负责：
 *   1. 渲染为 <span class="ids-glyph" style="font-family:IDSGlyphFont"></span>
 *   2. 携带 idsSource 用于退格展开和复制粘贴
 *   3. 序列化/反序列化 (HTML parse/serialize)
 */
export const IdsMark = Mark.create({
  name: "idsMark",

  inclusive: false,

  addAttributes() {
    return {
      idsSource: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-ids-source") || "",
        renderHTML: (attrs) => {
          if (attrs.idsSource) return { "data-ids-source": attrs.idsSource };
          return {};
        },
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

  renderHTML({ mark, HTMLAttributes }) {
    const attrs = mark.attrs as { idsSource: string; pua: number };
    return [
      "span",
      {
        class: "ids-glyph",
        style: `font-family: IDSGlyphFont, "IDSGlyphFont-fallback"`,
        "data-ids-source": attrs.idsSource || "",
        "data-pua": attrs.pua > 0 ? String(attrs.pua) : "",
        title: attrs.idsSource || "",
        ...HTMLAttributes,
      },
      0,  // 内容占位符: ProseMirror 把 PUA 字符文本塞到这里
    ];
  },

  parseHTML() {
    return [{ tag: "span.ids-glyph[data-ids-source]" }];
  },
});
