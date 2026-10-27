import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";

const IDS_ALT_NUMPAD: Record<string, string> = {
  Numpad0: "⿰",       // ⿰ 左右
  Numpad1: "⿱",       // ⿱ 上下
  Numpad2: "⿲",       // ⿲ 左中右
  Numpad3: "⿳",       // ⿳ 上中下
  Numpad4: "⿴",       // ⿴ 全包围
  Numpad5: "⿵",       // ⿵ 上三包围
  Numpad6: "⿶",       // ⿶ 下三包围
  Numpad7: "⿷",       // ⿷ 左三包围
  Numpad8: "⿸",       // ⿸ 左上包围
  Numpad9: "⿹",       // ⿹ 右上包围
  NumpadAdd: "⿺",     // ⿺ 左下包围
  NumpadSubtract: "⿻", // ⿻ 重叠
};

export const IdsNumpad = Extension.create({
  name: "idsNumpad",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("idsNumpad"),
        props: {
          handleDOMEvents: {
            keydown: (view, event) => {
              if (event.altKey && !event.ctrlKey && !event.shiftKey && !event.metaKey) {
                const op = IDS_ALT_NUMPAD[event.code];
                if (op) {
                  event.preventDefault();
                  event.stopPropagation();
                  const tr = view.state.tr.insertText(op);
                  view.dispatch(tr);
                  return true;
                }
              }
              return false;
            },
          },
        },
      }),
    ];
  },
});
