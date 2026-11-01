import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { idsOpFromKey } from "./idsShortcuts";

/**
 * 桌面端 IDS 算符快捷键（Alt+Numpad… 二元 / Alt+Ctrl+=、Alt+Ctrl+- 三聚）
 *
 * 字典在 `idsShortcuts.ts`（唯一真理）：手机工具条的宫格、Ruby/夹注面板里的
 * 普通输入框，都用同一份映射，避免多处各写一份。
 */
export const IdsNumpad = Extension.create({
  name: "idsNumpad",

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey("idsNumpad"),
        props: {
          handleDOMEvents: {
            keydown: (view, event) => {
              if (!event.altKey || event.metaKey || event.shiftKey) return false;
              const op = idsOpFromKey({
                altKey: event.altKey,
                ctrlKey: event.ctrlKey,
                metaKey: event.metaKey,
                code: event.code,
              });
              if (!op) return false;
              event.preventDefault();
              event.stopPropagation();
              view.dispatch(view.state.tr.insertText(op));
              return true;
            },
          },
        },
      }),
    ];
  },
});
