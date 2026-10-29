import { useEffect, useState } from "react";
import type { PanelMode, WritingMode } from "../App";
import type { CandidateSource, CandidateSourceState } from "../editor/candidateEngine";

interface ToolbarProps {
  writingMode: WritingMode;
  onToggleWritingMode: () => void;
  onOpenPanel: (mode: PanelMode) => void;
  panelMode: PanelMode;
  onInsertText: (text: string) => void;
  onNewFile?: () => void;
  onOpenFile?: () => void;
  onSaveFile?: () => void;
  onToggleFileSidebar?: () => void;
  showFileSidebar?: boolean;
  onToggleBold?: () => void;
  onToggleItalic?: () => void;
  onCycleHeading?: () => void;
  boldActive?: boolean;
  italicActive?: boolean;
  headingLevel?: number;
  candEnabled?: CandidateSourceState;
  onToggleCandidate?: (source: CandidateSource, on: boolean) => void;
}

const CAND_SOURCES: { key: CandidateSource; label: string }[] = [
  { key: "ja", label: "日语 (音/訓)" },
  { key: "ko", label: "韩文" },
  { key: "jamo", label: "古谚文" },
  { key: "vi", label: "越南文" },
];

/**
 * IDS 算符按钮
 *
 * 顺序、快捷键、方向码全部对齐 `editor/idsNumpad.ts`：
 *   主字典 IDS_ALT_NUMPAD  → NumpadAdd(Numpad+) / NumpadSubtract(Numpad-) / 1…0 / M / T / J
 *   三聚字典 Trity_IDS_OPERATOR → Equal(=) 或 Ctrl+Numpad+ 得 ⿳，Minus(-) 或 Ctrl+Numpad- 得 ⿲
 *
 * title 里的两个字母是字典注释里的方向码：
 *   U/D/L/R = 上/下/左/右, O = open (开口方向), C = closed (全包围),
 *   XX = 重叠, MI = 镜像, RO = 旋转, SU = 减去, UU/LL = 上下三叠 / 左右三并
 * 所以 ⿸ = RD（向右下开口）、⿹ = LD、⿵ = OD、⿶ = OU、⿷ = OR、⿼ = OL、⿽ = LU、⿺ = RU。
 */
const IDS_OPERATORS = [
  { label: "⿱", title: "UD — Alt+Numpad+" },
  { label: "⿰", title: "LR — Alt+Numpad-" },
  { label: "⿺", title: "RU — Alt+Numpad1" },
  { label: "⿶", title: "OU — Alt+Numpad2" },
  { label: "⿽", title: "LU — Alt+Numpad3" },
  { label: "⿷", title: "OR — Alt+Numpad4" },
  { label: "⿴", title: "OC — Alt+Numpad5" },
  { label: "⿼", title: "OL — Alt+Numpad6" },
  { label: "⿸", title: "RD — Alt+Numpad7" },
  { label: "⿵", title: "OD — Alt+Numpad8" },
  { label: "⿹", title: "LD — Alt+Numpad9" },
  { label: "⿻", title: "XX — Alt+Numpad0" },
  { label: "⿾", title: "MI — Alt+M" },
  { label: "⿿", title: "RO — Alt+T" },
  { label: "㇯", title: "SU — Alt+J" },
  { label: "⿳", title: "UU — Alt+Ctrl+= || Alt+Ctrl+Numpad+" },
  { label: "⿲", title: "LL — Alt+Ctrl+- || Alt+Ctrl+Numpad-" },
];

function Toolbar({
  writingMode, onToggleWritingMode, onOpenPanel, panelMode, onInsertText,
  onNewFile, onOpenFile, onSaveFile, onToggleFileSidebar, showFileSidebar,
  onToggleBold, onToggleItalic, onCycleHeading,
  boldActive, italicActive, headingLevel,
  candEnabled, onToggleCandidate,
}: ToolbarProps) {
  const [candMenuOpen, setCandMenuOpen] = useState(false);

  // 点击外部关闭候选源菜单
  useEffect(() => {
    if (!candMenuOpen) return;
    const close = () => setCandMenuOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [candMenuOpen]);

  return (
    <div className="toolbar">
      {/* Menu */}
      <div className="toolbar-group">
        <button className="toolbar-btn" title="菜单">≡</button>
      </div>

      {/* File ops */}
      <div className="toolbar-group">
        <button
          className={`toolbar-btn wide ${showFileSidebar ? "active" : ""}`}
          title="文件面板"
          onClick={onToggleFileSidebar}
        >
          文件
        </button>
        <button className="toolbar-btn wide" title="新建 (Ctrl+N)" onClick={onNewFile}>新建</button>
        <button className="toolbar-btn wide" title="打开 (Ctrl+O)" onClick={onOpenFile}>打开</button>
        <button className="toolbar-btn primary" title="保存 (Ctrl+S)" onClick={onSaveFile}>保存</button>
      </div>

      {/* Writing mode */}
      <div className="toolbar-group">
        <button
          className={`toolbar-btn wide ${writingMode === "vertical" ? "active" : ""}`}
          onClick={onToggleWritingMode}
          title="切换横排/竖排"
        >
          {writingMode === "horizontal" ? "横排" : "竖排"}
        </button>
      </div>

      {/* Markdown */}
      <div className="toolbar-group">
        <button className={`toolbar-btn ${boldActive ? "active" : ""}`} title="粗体 (Ctrl+B)" onClick={onToggleBold}><b>B</b></button>
        <button className={`toolbar-btn ${italicActive ? "active" : ""}`} title="斜体 (Ctrl+I)" onClick={onToggleItalic}><i>I</i></button>
        <button
          className={`toolbar-btn ${headingLevel ? "active" : ""}`}
          title="标题 (点击循环 H1→H2→H3→H4→关闭)"
          onClick={onCycleHeading}
        >
          {headingLevel ? `H${headingLevel}` : "H"}
        </button>
      </div>

      {/* 候选数据源开关 */}
      {candEnabled && onToggleCandidate && (
        <div className="toolbar-group">
          <div className="cand-toggle">
            <button
              className={`toolbar-btn wide${candMenuOpen ? " active" : ""}`}
              title="候选数据源开关"
              onClick={(e) => { e.stopPropagation(); setCandMenuOpen((v) => !v); }}
            >
              候选 ▾
            </button>
            {candMenuOpen && (
              <div className="cand-toggle-menu" onClick={(e) => e.stopPropagation()}>
                {CAND_SOURCES.map((s) => (
                  <div
                    key={s.key}
                    className={`cand-toggle-item${candEnabled[s.key] ? " active" : ""}`}
                    onClick={() => onToggleCandidate(s.key, !candEnabled[s.key])}
                  >
                    {s.label}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* IDS operators */}
      <div className="toolbar-group">
        {IDS_OPERATORS.map((op) => (
          <button
            key={op.label}
            className="toolbar-btn-idsop"
            title={op.title}
            onClick={() => onInsertText(op.label)}
          >
            {op.label}
          </button>
        ))}
      </div>

      <div className="toolbar-spacer" />

      {/* Special modes */}
      <div className="toolbar-group">
        <button
          className={`toolbar-btn ${panelMode === "ruby" ? "active" : ""}`}
          onClick={() => onOpenPanel("ruby")}
          title="Ruby 注音编辑"
        >
          Ruby
        </button>
        <button
          className={`toolbar-btn ${panelMode === "kage" ? "active" : ""}`}
          onClick={() => onOpenPanel("kage")}
          title="KAGE 字形编辑"
        >
          KAGE
        </button>
        <button
          className={`toolbar-btn ${panelMode === "annotation" ? "active" : ""}`}
          onClick={() => onOpenPanel("annotation")}
          title="双行小字注释"
        >
          注
        </button>
        <button className="toolbar-btn" title="IPA 输入 (Alt+key)">
          IPA
        </button>
      </div>
    </div>
  );
}

export default Toolbar;
