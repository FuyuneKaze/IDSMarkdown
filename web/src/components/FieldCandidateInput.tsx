import { useRef, useState } from "react";
import CandidatePopup from "./CandidatePopup";
import type { CandPopupState } from "./CandidatePopup";
import { candidateEngine } from "../editor/candidateEngine";
import { insertIntoField, panelKeyInsert } from "../editor/panelKeys";

/**
 * 带候选框的单行输入框
 *
 * 面板（Ruby / 夹注）里的 `<input>` 原本既没有候选框也收不到主编辑器的快捷键。
 * 这个组件把两者都补齐，同时保持普通 `<input>` 的使用方式：
 *
 *   - Alt+算符 / Alt+字母→IPA：走 `panelKeyInsert`（与主编辑器同一套字典）
 *   - 输入拉丁字母：取光标前那段 `[A-Za-z]+` 去 `candidateEngine.query()`，
 *     在输入框下方弹出同一个 `<CandidatePopup>`；
 *     ↑↓ 选行、←→ 选列、Enter 采纳、Esc 关闭、Backspace/空格 关闭
 *   - 采纳时替换掉那段拉丁字母，光标落到替换文本之后
 */
interface Props {
  value: string;
  onChange: (v: string) => void;
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
  /** 面板自己的额外按键处理（返回 true 表示已处理，不再走候选逻辑） */
  onExtraKeyDown?: (e: React.KeyboardEvent<HTMLInputElement>) => boolean;
}

const LATIN_TAIL = /[A-Za-z]+$/;

export default function FieldCandidateInput({
  value, onChange, className, placeholder, autoFocus, onExtraKeyDown,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [cand, setCand] = useState<{
    state: CandPopupState;
    left: number;
    top: number;
    /** 被替换的拉丁串在 value 里的起点 */
    start: number;
    end: number;
  } | null>(null);

  const close = () => setCand(null);

  /** 根据当前 value + caret 刷新候选 */
  const refresh = (nextValue: string, caret: number) => {
    if (!candidateEngine.isReady()) { close(); return; }
    const before = nextValue.slice(0, caret);
    const m = LATIN_TAIL.exec(before);
    if (!m) { close(); return; }
    const rows = candidateEngine.query(m[0]);
    if (rows.length === 0) { close(); return; }
    const el = inputRef.current;
    const r = el?.getBoundingClientRect();
    setCand({
      state: { rows, selRow: 0, selCol: 0, queryPos: caret - m[0].length },
      left: r ? r.left : 8,
      top: r ? r.bottom + 4 : 80,
      start: caret - m[0].length,
      end: caret,
    });
  };

  /** 采纳候选 */
  const accept = (rowIdx: number, colIdx: number) => {
    if (!cand) return;
    const row = cand.state.rows[rowIdx];
    const text = row?.candidates[colIdx];
    if (!text) return;
    const next = value.slice(0, cand.start) + text.replace(/^\x00/, "") + value.slice(cand.end);
    const caret = cand.start + text.replace(/^\x00/, "").length;
    onChange(next);
    close();
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (el) { el.selectionStart = caret; el.selectionEnd = caret; }
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (onExtraKeyDown?.(e)) return;

    // 候选面板打开时优先处理导航键
    if (cand) {
      const { rows, selRow, selCol } = cand.state;
      const row = rows[selRow];
      const cols = row?.candidates.length ?? 0;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const d = e.key === "ArrowDown" ? 1 : -1;
        const nr = (selRow + d + rows.length) % rows.length;
        setCand({ ...cand, state: { ...cand.state, selRow: nr, selCol: 0 } });
        return;
      }
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        const d = e.key === "ArrowRight" ? 1 : -1;
        const nc = cols > 0 ? (selCol + d + cols) % cols : 0;
        setCand({ ...cand, state: { ...cand.state, selCol: nc } });
        return;
      }
      if (e.key === "Enter" && row) {
        e.preventDefault();
        accept(selRow, selCol);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        close();
        return;
      }
    }

    // 面板里的 Alt 快捷键（IDS 算符 / IPA）
    const ins = panelKeyInsert(e.nativeEvent);
    if (ins) {
      e.preventDefault();
      insertIntoField(e.currentTarget, ins, onChange);
      return;
    }

    // 空格/退格/回车 → 关闭候选
    if (cand && (e.key === " " || e.key === "Backspace" || e.key === "Tab")) close();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    onChange(v);
    const caret = e.target.selectionStart ?? v.length;
    refresh(v, caret);
  };

  return (
    <>
      <input
        ref={inputRef}
        className={className}
        value={value}
        placeholder={placeholder}
        autoFocus={autoFocus}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={() => setTimeout(close, 150)}
      />
      {cand && (
        <CandidatePopup
          state={cand.state}
          left={cand.left}
          top={cand.top}
          onSelect={(r, c) => {
            const row = cand.state.rows[r];
            const cols = row?.candidates.length ?? 0;
            setCand({
              ...cand,
              state: { ...cand.state, selRow: r, selCol: c < 0 ? Math.min(cand.state.selCol, Math.max(0, cols - 1)) : c },
            });
          }}
          onAccept={(r, c) => accept(r, c)}
          onCancel={close}
        />
      )}
    </>
  );
}
