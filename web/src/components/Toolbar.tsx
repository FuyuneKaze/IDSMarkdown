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

const IDS_OPERATORS = [
  { label: "⿰", title: "左右结构 — Alt+Numpad0" },
  { label: "⿱", title: "上下结构 — Alt+Numpad1" },
  { label: "⿲", title: "左中右 — Alt+Numpad2" },
  { label: "⿳", title: "上中下 — Alt+Numpad3" },
  { label: "⿴", title: "全包围 — Alt+Numpad4" },
  { label: "⿵", title: "上三包围 — Alt+Numpad5" },
  { label: "⿶", title: "下三包围 — Alt+Numpad6" },
  { label: "⿷", title: "左三包围 — Alt+Numpad7" },
  { label: "⿸", title: "左上包围 — Alt+Numpad8" },
  { label: "⿹", title: "右上包围 — Alt+Numpad9" },
  { label: "⿺", title: "左下包围 — Alt+Numpad+" },
  { label: "⿻", title: "重叠 — Alt+Numpad-" },
  { label: "⿾", title: "镜像 — " },
  { label: "⿿", title: "旋转 — " },
  { label: "㇯", title: "减去 — " },
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
