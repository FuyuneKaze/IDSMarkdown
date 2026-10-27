import { Node } from "@tiptap/core";
import { glyphFontManager } from "./glyphFontManager";

/**
 * doubleLine: 内联原子节点, 双行小字注释 (仿古籍)
 *
 * 属性:
 *   text — 注释全文
 *
 * 渲染时按码点分割: 前半 (ceil(n/2)) 为 line1, 后半为 line2。
 * 横排: line1 在上 (block 流从上到下); 竖排: 继承 vertical-rl, line1 在右 (古籍先右半行)
 */
export const DoubleLine = Node.create({
  name: "doubleLine",

  group: "inline",
  inline: true,
  atom: true,
  selectable: false,

  addAttributes() {
    return {
      text: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-text") || "",
        renderHTML: (attrs) => ({ "data-text": attrs.text }),
      },
      // 内部重建版本号: 块扫描后强制 DOM 重建 (不输出到 DOM, 不影响序列化)
      _v: {
        default: 0,
        parseHTML: () => 0,
        renderHTML: () => ({}),
      },
    };
  },

  parseHTML() {
    return [{ tag: "span[data-type='double-line']" }];
  },

  renderHTML({ node, HTMLAttributes }) {
    // 渲染时把已映射的 IDS 表达式替换为 PUA 字 (侧栏编辑/序列化保持表达式)
    const display = glyphFontManager.renderIdsToPua((node.attrs as { text: string }).text);
    const cps = [...display];
    const half = Math.ceil(cps.length / 2);
    const line1 = cps.slice(0, half).join("");
    const line2 = cps.slice(half).join("");
    const hasText = (node.attrs as { text: string }).text.length > 0;
    // 子 span 必须平铺为多个 content 项; 二维数组会被 renderSpec 误解析为 [tag, ...] 而抛
    // "Invalid array passed to renderSpec" (仅在输入文字后触发, 空块占位是字符串不会暴露)
    const children = hasText
      ? [
          ["span", { class: "dl-line1" }, line1],
          ["span", { class: "dl-line2" }, line2],
        ]
      : ["[双行]"];
    return [
      "span",
      {
        "data-type": "double-line",
        class: hasText ? "double-line" : "double-line double-line-placeholder",
        contenteditable: "false",
        ...HTMLAttributes,
      },
      ...children,
    ];
  },

  renderText({ node }: any) {
    return (node.attrs as { text: string }).text || "";
  },
});
