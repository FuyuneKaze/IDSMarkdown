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

/**
 * IDS 算符宫格
 *
 * 布局照 `ids_layout.txt`：
 *   ⿰⿱⿲⿳      ← 4 个（结构）
 *   ⿸⿵⿹        ← 3 个
 *   ⿷⿴⿼        ← 3 个
 *   ⿺⿶⿽        ← 3 个
 *     ⿻         ← 居中
 *   ⿾⿿㇯        ← 修饰（镜像/旋转/减去）
 *
 * span 是 12 栅格里的跨度：4 个一行用 3，3 个一行用 4，⿻ 居中占 5–8。
 * 顺序与快捷键说明见 `editor/idsNumpad.ts`（UD/LR/RU/OU/LU/OR/OC/OL/RD/OD/LD/XX/MI/RO/SU/UU/LL）。
 */
interface IdsPadItem {
  label: string;
  title: string;
  span: number;
  center?: boolean;
}

const IDS_PAD: IdsPadItem[] = [
  { label: "⿰", span: 3, title: "LR 左右结构 — Alt+Numpad-" },
  { label: "⿱", span: 3, title: "UD 上下结构 — Alt+Numpad+" },
  { label: "⿲", span: 3, title: "LL 左中右 — Alt+Ctrl+- 或 Alt+Ctrl+Numpad-" },
  { label: "⿳", span: 3, title: "UU 上中下 — Alt+Ctrl+= 或 Alt+Ctrl+Numpad+" },
  { label: "⿸", span: 4, title: "RD 左上包围 (向右下开口) — Alt+Numpad7" },
  { label: "⿵", span: 4, title: "OD 上三包围 (向下开口) — Alt+Numpad8" },
  { label: "⿹", span: 4, title: "LD 右上包围 (向左下开口) — Alt+Numpad9" },
  { label: "⿷", span: 4, title: "OR 左三包围 (向右开口) — Alt+Numpad4" },
  { label: "⿴", span: 4, title: "OC 全包围 — Alt+Numpad5" },
  { label: "⿼", span: 4, title: "OL 右二包围 (向左开口) — Alt+Numpad6" },
  { label: "⿺", span: 4, title: "RU 左下包围 (向右上开口) — Alt+Numpad1" },
  { label: "⿶", span: 4, title: "OU 下三包围 (向上开口) — Alt+Numpad2" },
  { label: "⿽", span: 4, title: "LU 右下包围 (向左上开口) — Alt+Numpad3" },
  { label: "⿻", span: 4, center: true, title: "XX 重叠 — Alt+Numpad0" },
  { label: "⿾", span: 4, title: "MI 镜像 — Alt+M" },
  { label: "⿿", span: 4, title: "RO 旋转 — Alt+T" },
  { label: "㇯", span: 4, title: "SU 减去 — Alt+J" },
];

type MenuKey = "file" | "md" | "ids" | "cand" | null;

function Toolbar({
  writingMode, onToggleWritingMode, onOpenPanel, panelMode, onInsertText,
  onNewFile, onOpenFile, onSaveFile, onToggleFileSidebar, showFileSidebar,
  onToggleBold, onToggleItalic, onCycleHeading,
  boldActive, italicActive, headingLevel,
  candEnabled, onToggleCandidate,
}: ToolbarProps) {
  const [openMenu, setOpenMenu] = useState<MenuKey>(null);
  // IDS 宫格是"浮层"：手机上它比按钮宽得多，绝对定位会被屏幕/父元素裁掉。
  // 打开时按按钮位置量一次，改成 position:fixed 并夹进视口内（等效居中）。
  const idsBtnRef = useRef<HTMLButtonElement>(null);
  const [idsPos, setIdsPos] = useState<{ left: number; top: number; width: number } | null>(null);

  const close = () => setOpenMenu(null);
  const toggle = (k: Exclude<MenuKey, null>) => setOpenMenu((v) => (v === k ? null : k));

  const openIds = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (openMenu === "ids") { close(); return; }
    const r = idsBtnRef.current?.getBoundingClientRect();
    const vw = window.innerWidth;
    const w = Math.min(300, vw - 12);
    if (r) {
      const left = Math.min(Math.max(6, r.left + r.width / 2 - w / 2), vw - w - 6);
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

      {/* IDS 算符: 触发按钮用 ⿻ (重叠)，宫格按 ids_layout.txt 排 */}
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
              {IDS_PAD.map((op) => (
                <button
                  key={op.label}
                  className={`ids-menu-btn${op.center ? " center" : ""}`}
                  style={{ gridColumn: op.center ? "5 / 9" : `span ${op.span}` }}
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
