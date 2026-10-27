import { Node } from "@tiptap/core";
import { glyphFontManager } from "./glyphFontManager";

/**
 * rubyBlock: 内联原子节点, 多个汉字共享一段注音 (整块 ruby)
 *
 * 属性:
 *   base — 文字部分 (如 "漢字文化")
 *   rt   — 注音部分 (如 "かんじぶんか"), 与 base 整块共享
 *
 * 渲染: <span data-type="ruby-block"><span class="rb-rt">注音</span><span class="rb-base">文字</span></span>
 * 横排: rb-rt 在上 (block 流从上到下); 竖排: 继承 vertical-rl, rb-rt 在右
 */
export const RubyBlock = Node.create({
  name: "rubyBlock",

  group: "inline",
  inline: true,
  atom: true,
  selectable: false,

  addAttributes() {
    return {
      base: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-base") || "",
        renderHTML: (attrs) => ({ "data-base": attrs.base }),
      },
      rt: {
        default: "",
        parseHTML: (el) => el.getAttribute("data-rt") || "",
        renderHTML: (attrs) => ({ "data-rt": attrs.rt }),
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
    return [{ tag: "span[data-type='ruby-block']" }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = node.attrs as { base: string; rt: string };
    // 渲染时把已映射的 IDS 表达式替换为 PUA 字 (侧栏编辑/序列化保持表达式)
    const displayBase = glyphFontManager.renderIdsToPua(attrs.base);
    const displayRt = glyphFontManager.renderIdsToPua(attrs.rt);
    const hasBase = attrs.base.length > 0;
    // 子 span 必须平铺为多个 content 项; 二维数组会被 renderSpec 误解析为 [tag, ...] 而抛
    // "Invalid array passed to renderSpec" (仅在输入文字后触发, 空块占位是字符串不会暴露)
    const children = hasBase
      ? [
          ["span", { class: "rb-rt" }, displayRt],
          ["span", { class: "rb-base" }, displayBase],
        ]
      : ["[注音]"];
    return [
      "span",
      {
        "data-type": "ruby-block",
        class: hasBase ? "ruby-block" : "ruby-block ruby-block-placeholder",
        contenteditable: "false",
        ...HTMLAttributes,
      },
      ...children,
    ];
  },

  renderText({ node }: any) {
    return (node.attrs as { base: string }).base || "";
  },
});
