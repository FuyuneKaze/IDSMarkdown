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
 * IDS 算符表
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
  { label: "⿱", title: "UD 上下结构 — Alt+Numpad+" },
  { label: "⿰", title: "LR 左右结构 — Alt+Numpad-" },
  { label: "⿺", title: "RU 左下包围 (向右上开口) — Alt+Numpad1" },
  { label: "⿶", title: "OU 下三包围 (向上开口) — Alt+Numpad2" },
  { label: "⿽", title: "LU 右下包围 (向左上开口) — Alt+Numpad3" },
  { label: "⿷", title: "OR 左三包围 (向右开口) — Alt+Numpad4" },
  { label: "⿴", title: "OC 全包围 — Alt+Numpad5" },
  { label: "⿼", title: "OL 右二包围 (向左开口) — Alt+Numpad6" },
  { label: "⿸", title: "RD 左上包围 (向右下开口) — Alt+Numpad7" },
  { label: "⿵", title: "OD 上三包围 (向下开口) — Alt+Numpad8" },
  { label: "⿹", title: "LD 右上包围 (向左下开口) — Alt+Numpad9" },
  { label: "⿻", title: "XX 重叠 — Alt+Numpad0" },
  { label: "⿾", title: "MI 镜像 — Alt+M" },
  { label: "⿿", title: "RO 旋转 — Alt+T" },
  { label: "㇯", title: "SU 减去 — Alt+J" },
  { label: "⿳", title: "UU 上中下 — Alt+Ctrl+= 或 Alt+Ctrl+Numpad+" },
  { label: "⿲", title: "LL 左中右 — Alt+Ctrl+- 或 Alt+Ctrl+Numpad-" },
];

type MenuKey = "file" | "md" | "ids" | "cand" | null;

function Toolbar({
  writingMode, onToggleWritingMode, onOpenPanel, panelMode, onInsertText,
  onNewFile, onOpenFile, onSaveFile, onToggleFileSidebar, showFileSidebar,
  onToggleBold, onToggleItalic, onCycleHeading,
  boldActive, italicActive, headingLevel,
  candEnabled, onToggleCandidate,
}: ToolbarProps) {
  // 手机上工具条放不下: 文件 / Markdown / IDS 算符都收进下拉菜单。
  // 下拉外观统一用 .cand-toggle* 那套样式（与候选数据源菜单一致）。
  const [openMenu, setOpenMenu] = useState<MenuKey>(null);
  const toggle = (k: Exclude<MenuKey, null>) => setOpenMenu((v) => (v === k ? null : k));
  const close = () => setOpenMenu(null);

  useEffect(() => {
    if (!openMenu) return;
    const h = () => setOpenMenu(null);
    document.addEventListener("click", h);
    return () => document.removeEventListener("click", h);
  }, [openMenu]);

  const stop = (e: React.MouseEvent) => e.stopPropagation();
  const mdLabel = headingLevel ? `H${headingLevel}` : "A";

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button className="toolbar-btn" title="菜单">≡</button>
      </div>

      {/* 文件: 一个下拉代替 新建/打开/保存 三个按钮 */}
      <div className="toolbar-group">
        <div className="cand-toggle">
          <button
            className={`toolbar-btn wide${openMenu === "file" ? " active" : ""}`}
            title="文件"
            onClick={(e) => { stop(e); toggle("file"); }}
          >
            文件 ▾
          </button>
          {openMenu === "file" && (
            <div className="cand-toggle-menu" onClick={stop}>
              <div className="cand-toggle-item" onClick={() => { close(); onToggleFileSidebar?.(); }}>
                文件面板{showFileSidebar ? "（关）" : "（开）"}
              </div>
              <div className="cand-toggle-item" onClick={() => { close(); onNewFile?.(); }}>新建</div>
              <div className="cand-toggle-item" onClick={() => { close(); onOpenFile?.(); }}>打开</div>
              <div className="cand-toggle-item" onClick={() => { close(); onSaveFile?.(); }}>保存</div>
            </div>
          )}
        </div>
      </div>

      {/* 写作方向 */}
      <div className="toolbar-group">
        <button
          className={`toolbar-btn wide ${writingMode === "vertical" ? "active" : ""}`}
          onClick={onToggleWritingMode}
          title="切换横排/竖排"
        >
          {writingMode === "horizontal" ? "横排" : "竖排"}
        </button>
      </div>

      {/* Markdown: 下拉 */}
      <div className="toolbar-group">
        <div className="cand-toggle">
          <button
            className={`toolbar-btn${openMenu === "md" ? " active" : ""}`}
            title="格式"
            onClick={(e) => { stop(e); toggle("md"); }}
          >
            {mdLabel} ▾
          </button>
          {openMenu === "md" && (
            <div className="cand-toggle-menu" onClick={stop}>
              <div
                className={`cand-toggle-item${boldActive ? " active" : ""}`}
                onClick={() => { close(); onToggleBold?.(); }}
              >
                粗体 <b>B</b>
              </div>
              <div
                className={`cand-toggle-item${italicActive ? " active" : ""}`}
                onClick={() => { close(); onToggleItalic?.(); }}
              >
                斜体 <i>I</i>
              </div>
              <div
                className={`cand-toggle-item${headingLevel ? " active" : ""}`}
                onClick={() => { close(); onCycleHeading?.(); }}
              >
                标题 {headingLevel ? `H${headingLevel} → ${headingLevel >= 4 ? "关" : "H" + (headingLevel + 1)}` : "H1"}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 候选数据源开关 */}
      {candEnabled && onToggleCandidate && (
        <div className="toolbar-group">
          <div className="cand-toggle">
            <button
              className={`toolbar-btn wide${openMenu === "cand" ? " active" : ""}`}
              title="候选数据源开关"
              onClick={(e) => { stop(e); toggle("cand"); }}
            >
              候选 ▾
            </button>
            {openMenu === "cand" && (
              <div className="cand-toggle-menu" onClick={stop}>
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

      {/* IDS 算符: 下拉宫格 (外观与候选菜单一致) */}
      <div className="toolbar-group">
        <div className="cand-toggle">
          <button
            className={`toolbar-btn${openMenu === "ids" ? " active" : ""}`}
            title="IDS 组字算符"
            onClick={(e) => { stop(e); toggle("ids"); }}
          >
            ⿰ ▾
          </button>
          {openMenu === "ids" && (
            <div className="cand-toggle-menu ids-menu" onClick={stop}>
              <div className="ids-menu-grid">
                {IDS_OPERATORS.map((op) => (
                  <button
                    key={op.label}
                    className="ids-menu-btn"
                    title={op.title}
                    onClick={() => { close(); onInsertText(op.label); }}
                  >
                    {op.label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="toolbar-spacer" />

      {/* 右侧面板按钮: 竖屏时自动换行, 不再被裁掉 */}
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
