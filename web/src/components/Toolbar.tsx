import { useEffect, useRef, useState } from "react";
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

/** IDS 算符表（顺序/方向码与 editor/idsShortcuts.ts 一致） */
const IDS_OPERATORS = [
  { label: "⿰", title: "LR 左右结构 — Alt+Numpad-" },
  { label: "⿱", title: "UD 上下结构 — Alt+Numpad+" },
  { label: "⿲", title: "LL 左中右 — Alt+Ctrl+-" },
  { label: "⿳", title: "UU 上中下 — Alt+Ctrl+=" },
  { label: "⿸", title: "RD 左上包围 — Alt+Numpad7" },
  { label: "⿵", title: "OD 上三包围 — Alt+Numpad8" },
  { label: "⿹", title: "LD 右上包围 — Alt+Numpad9" },
  { label: "⿷", title: "OR 左三包围 — Alt+Numpad4" },
  { label: "⿴", title: "OC 全包围 — Alt+Numpad5" },
  { label: "⿼", title: "OL 右二包围 — Alt+Numpad6" },
  { label: "⿺", title: "RU 左下包围 — Alt+Numpad1" },
  { label: "⿶", title: "OU 下三包围 — Alt+Numpad2" },
  { label: "⿽", title: "LU 右下包围 — Alt+Numpad3" },
  { label: "⿻", title: "XX 重叠 — Alt+Numpad0" },
  { label: "⿾", title: "MI 镜像 — Alt+M" },
  { label: "⿿", title: "RO 旋转 — Alt+T" },
  { label: "㇯", title: "SU 减去 — Alt+J" },
];

/** 窄屏下拉宫格的跨度：4 个结构 / 3+3+3 个包围 / 居中重叠 / 3 个修饰 */
const IDS_PAD_SPAN: Record<string, number> = {
  "⿰": 3, "⿱": 3, "⿲": 3, "⿳": 3,
  "⿸": 4, "⿵": 4, "⿹": 4,
  "⿷": 4, "⿴": 4, "⿼": 4,
  "⿺": 4, "⿶": 4, "⿽": 4,
  "⿻": 4,
  "⿾": 4, "⿿": 4, "㇯": 4,
};

type MenuKey = "md" | "ids" | "cand" | null;
const WIDE_QUERY = "(min-width: 761px)";

function Toolbar({
  writingMode, onToggleWritingMode, onOpenPanel, panelMode, onInsertText,
  onToggleFileSidebar, showFileSidebar,
  onToggleBold, onToggleItalic, onCycleHeading,
  boldActive, italicActive, headingLevel,
  candEnabled, onToggleCandidate,
}: ToolbarProps) {
  const [openMenu, setOpenMenu] = useState<MenuKey>(null);
  // 宽屏 / 窄屏：宽屏 IDS 算符铺成一横条，窄屏才收进下拉
  const [wide, setWide] = useState(() => window.matchMedia(WIDE_QUERY).matches);
  const idsBtnRef = useRef<HTMLButtonElement>(null);
  const [idsPos, setIdsPos] = useState<{ left: number; top: number; width: number } | null>(null);

  useEffect(() => {
    const mq = window.matchMedia(WIDE_QUERY);
    const h = (e: MediaQueryListEvent) => setWide(e.matches);
    mq.addEventListener("change", h);
    return () => mq.removeEventListener("change", h);
  }, []);

  const close = () => setOpenMenu(null);
  const toggle = (k: Exclude<MenuKey, null>) => setOpenMenu((v) => (v === k ? null : k));

  const openIds = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (openMenu === "ids") { close(); return; }
    const r = idsBtnRef.current?.getBoundingClientRect();
    const vw = window.innerWidth;
    const w = Math.min(300, vw - 12);
    if (r) {
      const left = Math.min(Math.max(6, r.left + r.width / 2 - w / 2), Math.max(6, vw - w - 6));
      setIdsPos({ left, top: r.bottom + 4, width: w });
    }
    setOpenMenu("ids");
  };

  useEffect(() => {
    if (!openMenu) return;
    const h = () => setOpenMenu(null);
    document.addEventListener("click", h);
    window.addEventListener("resize", h);
    return () => {
      document.removeEventListener("click", h);
      window.removeEventListener("resize", h);
    };
  }, [openMenu]);

  const stop = (e: React.MouseEvent) => e.stopPropagation();
  const mdLabel = headingLevel ? `H${headingLevel}` : "A";

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button className="toolbar-btn" title="菜单">≡</button>
      </div>

      {/* 文件:直接开合文件面板 (新建/打开/保存都在面板里) */}
      <div className="toolbar-group">
        <button
          className={`toolbar-btn wide ${showFileSidebar ? "active" : ""}`}
          title="文件面板"
          onClick={onToggleFileSidebar}
        >
          文件
        </button>
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

      {/* Markdown 下拉 */}
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

      {/* 候选数据源 */}
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

      {/* IDS 算符: 宽屏一横条 / 窄屏下拉 */}
      {wide ? (
        <div className="toolbar-group ids-inline">
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
      ) : (
        <div className="toolbar-group">
          <button
            ref={idsBtnRef}
            className={`toolbar-btn ids-trigger${openMenu === "ids" ? " active" : ""}`}
            title="IDS 组字算符"
            onClick={openIds}
          >
            ⿻ ▾
          </button>
          {openMenu === "ids" && idsPos && (
            <div
              className="ids-menu"
              style={{ position: "fixed", left: idsPos.left, top: idsPos.top, width: idsPos.width }}
              onClick={stop}
            >
              <div className="ids-menu-grid">
                {IDS_OPERATORS.map((op) => (
                  <button
                    key={op.label}
                    className="ids-menu-btn"
                    style={{ gridColumn: op.label === "⿻" ? "5 / 9" : `span ${IDS_PAD_SPAN[op.label] ?? 4}` }}
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
      )}

      <div className="toolbar-spacer" />

      {/* 右侧面板按钮 */}
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
        <button
          className={`toolbar-btn ${panelMode === "symbols" ? "active" : ""}`}
          onClick={() => onOpenPanel("symbols")}
          title="符号 (IPA / 难输入部件)"
        >
          符号
        </button>
      </div>
    </div>
  );
}

export default Toolbar;
