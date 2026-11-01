import { ipaDatabase, logicalNameFromCode } from "./ipaDatabase";
import { idsOpFromKey } from "./idsShortcuts";

/**
 * 普通输入框（Ruby / 夹注面板里的 <input>）的快捷键桥接
 *
 * 主编辑器的快捷键是挂在 ProseMirror 的 keydown 上的，面板里的裸 <input> 收不到。
 * 这里把同一套字典翻译成"要插入的文本"，由调用方在 caret 处写入。
 *
 * 支持:
 *   Alt + Numpad…/M/T/J  → IDS 算符（与主编辑器一致）
 *   Alt + Ctrl + =/-     → 三聚算符 ⿳ / ⿲
 *   Alt + 字母/数字      → IPA 符号（取该逻辑键的第一个候选）
 */
export function panelKeyInsert(e: KeyboardEvent): string | null {
  if (e.metaKey) return null;

  const op = idsOpFromKey({
    altKey: e.altKey, ctrlKey: e.ctrlKey, metaKey: e.metaKey, code: e.code,
  });
  if (op) return op;

  // IPA: Alt + 字母/数字（主编辑器里是 Alt+key 循环候选，这里取第一个）
  if (e.altKey && !e.ctrlKey && ipaDatabase.isReady()) {
    const logical = logicalNameFromCode(e.code);
    if (logical) {
      const cands = ipaDatabase.candidates(logical, e.shiftKey);
      if (cands.length > 0) return cands[0];
    }
  }
  return null;
}

/**
 * 在 <input>/<textarea> 的 caret 处插入文本（替换选区），并保持光标在插入之后。
 * onValue 把新值交给 React 的受控 state。
 */
export function insertIntoField(
  el: HTMLInputElement | HTMLTextAreaElement,
  text: string,
  onValue: (v: string) => void,
): void {
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? start;
  const next = el.value.slice(0, start) + text + el.value.slice(end);
  onValue(next);
  const caret = start + text.length;
  requestAnimationFrame(() => {
    try {
      el.selectionStart = caret;
      el.selectionEnd = caret;
    } catch {
      /* 某些浏览器在受控组件更新后暂时不允许设置，忽略 */
    }
  });
}
