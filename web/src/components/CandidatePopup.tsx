import { useEffect, useRef } from "react";
import type { RowResult } from "../editor/candidateEngine";

export interface CandPopupState {
  rows: RowResult[];
  selRow: number;
  selCol: number;
  queryPos: number;
}

interface Props {
  state: CandPopupState;
  left: number;
  top: number;
  onSelect: (row: number, col: number) => void;
  onAccept: (row: number, col: number) => void;
  onCancel: () => void;
}

export default function CandidatePopup({ state, left, top, onSelect, onAccept, onCancel }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  // 关闭事件外点击取消 (延迟绑定防止当前点击触发)
  useEffect(() => {
    const timer = setTimeout(() => {
      document.addEventListener("click", onCancel, { once: true });
    }, 0);
    return () => { clearTimeout(timer); };
  }, [onCancel]);

  // 选中项移出可视区时自动滚动到可见位置
  useEffect(() => {
    const selCell = ref.current?.querySelector(".candidate-cell.sel");
    if (selCell) {
      (selCell as HTMLElement).scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }, [state.selRow, state.selCol]);

  // 标音字号: 长标音缩小字号避免与相邻内容重叠
  const labelFontSize = (len: number) => (len > 4 ? 10 : len > 2 ? 12 : 14);

  return (
    <div
      ref={ref}
      className="candidate-popup"
      style={{ left: `${left}px`, top: `${top}px` }}
      onMouseDown={(e) => e.preventDefault()}
      onClick={(e) => {
        // 点击空白区取消
        const target = e.target as HTMLElement;
        if (!target.closest(".candidate-row")) {
          onCancel();
        }
      }}
    >
      {state.rows.map((row, ri) => {
        const isSel = ri === state.selRow;
        return (
          <div
            key={ri}
            className={`candidate-row${isSel ? " sel" : ""}`}
            onMouseMove={() => onSelect(ri, -1)}
          >
            <span className="candidate-label" style={{ color: row.color, fontSize: labelFontSize(row.label.length) }}>
              {row.label}
            </span>
            <span className="candidate-sublabel">{row.subLabel}</span>
            <div className="candidate-area">
              {row.candidates.map((cand, ci) => {
                const isLabel = cand.startsWith("\x00");
                const text = isLabel ? cand.slice(1) : cand;
                const sel = isSel && ci === state.selCol;
                return (
                  <span
                    key={ci}
                    className={`candidate-cell${sel ? " sel" : ""}${isLabel ? " label" : ""}`}
                    //style={isLabel ? { fontSize: labelFontSize(text.length) } : undefined}
                    onMouseMove={(e) => { e.stopPropagation(); onSelect(ri, ci); }}
                    onClick={(e) => { e.stopPropagation(); onAccept(ri, ci); }}
                  >
                    {text}
                  </span>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
