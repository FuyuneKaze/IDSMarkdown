import { useEffect, useRef } from "react";
import type { PanelMode } from "../App";
import type { RubyTarget, AnnotationTarget } from "./Editor";
import KageEditorPanel from "./KageEditorPanel";
import RubyEditorPanel from "./RubyEditorPanel";
import AnnotationEditorPanel from "./AnnotationEditorPanel";

interface SidePanelProps {
  mode: PanelMode;
  onClose: () => void;
  onInsertKageGlyph?: (kageData: string, glyphName: string) => void;
  kageInitialName?: string;
  kageInitialData?: string;
  kageKey?: number;
  rubyTarget?: RubyTarget | null;
  annotationTarget?: AnnotationTarget | null;
  onInsertRuby?: (base: string, rt: string) => void;
  onUpdateRuby?: (pos: number, base: string, rt: string) => void;
  onInsertAnnotation?: (text: string) => void;
  onUpdateAnnotation?: (pos: number, text: string) => void;
}

const PANEL_TITLES: Record<string, string> = {
  kage: "KAGE 字形编辑",
  ruby: "Ruby 注音编辑",
  annotation: "双行小字注释",
  search: "部件搜索",
};

const MIN_WIDTH = 240;
const MAX_WIDTH = 600;

function SidePanel({
  mode, onClose, onInsertKageGlyph, kageInitialName, kageInitialData, kageKey,
  rubyTarget, annotationTarget, onInsertRuby, onUpdateRuby, onInsertAnnotation, onUpdateAnnotation,
}: SidePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;

    // 优先取前兄弟节点, 否则用 querySelector 兜底
    let handle = panel.previousElementSibling as HTMLElement | null;
    if (!handle || !handle.classList.contains("panel-resize-handle")) {
      handle = document.querySelector(".panel-resize-handle") as HTMLElement | null;
    }
    if (!handle) return;

    let startX = 0;
    let startWidth = 0;

    const onPointerDown = (e: PointerEvent) => {
      handle!.setPointerCapture(e.pointerId);
      startX = e.clientX;
      startWidth = panel.offsetWidth;
      document.body.style.cursor = "ew-resize";
      document.body.style.userSelect = "none";
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!handle!.hasPointerCapture(e.pointerId)) return;
      const delta = startX - e.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidth + delta));
      panel.style.width = `${newWidth}px`;
    };

    const onPointerUp = (e: PointerEvent) => {
      handle!.releasePointerCapture(e.pointerId);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    handle.addEventListener("pointerdown", onPointerDown);
    handle.addEventListener("pointermove", onPointerMove);
    handle.addEventListener("pointerup", onPointerUp);

    return () => {
      handle?.removeEventListener("pointerdown", onPointerDown);
      handle?.removeEventListener("pointermove", onPointerMove);
      handle?.removeEventListener("pointerup", onPointerUp);
    };
  }, []);

  return (
    <div className="side-panel" ref={panelRef}>
      <div className="panel-header">
        <span>{PANEL_TITLES[mode || ""] || "面板"}</span>
        <button className="panel-close" onClick={onClose}>×</button>
      </div>
      <div className={`panel-body${mode === "kage" ? " kage-panel" : mode === "ruby" || mode === "annotation" ? " form-panel" : ""}`}>
        {mode === "kage" && onInsertKageGlyph ? (
          <KageEditorPanel
            key={kageKey}
            onGlyphSubmit={({ kageData, name }) => onInsertKageGlyph(kageData, name)}
            initialName={kageInitialName}
            initialData={kageInitialData}
          />
        ) : mode === "ruby" ? (
          <RubyEditorPanel
            target={rubyTarget ?? null}
            onInsert={(base, rt) => onInsertRuby?.(base, rt)}
            onUpdate={(pos, base, rt) => onUpdateRuby?.(pos, base, rt)}
          />
        ) : mode === "annotation" ? (
          <AnnotationEditorPanel
            target={annotationTarget ?? null}
            onInsert={(text) => onInsertAnnotation?.(text)}
            onUpdate={(pos, text) => onUpdateAnnotation?.(pos, text)}
          />
        ) : (
          <span>
            {mode === "search" ? "功能开发中..." : "选择文字后可在此编辑 Ruby 注音"}
          </span>
        )}
      </div>
    </div>
  );
}

export default SidePanel;
