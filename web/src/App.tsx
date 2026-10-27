import { useState, useCallback, useRef, useEffect } from "react";
import Toolbar from "./components/Toolbar";
import Editor from "./components/Editor";
import type { EditorHandle, RubyTarget, AnnotationTarget } from "./components/Editor";
import SidePanel from "./components/SidePanel";
import FileSidebar, { loadRecentFiles, saveRecentFile } from "./components/FileSidebar";
import type { RecentFile } from "./components/FileSidebar";
import { glyphFontManager } from "./editor/glyphFontManager";
import { serializeIdsmd, parseIdsmd, markdownToHtml, convertInlineAnnotations, openFileWithPicker, saveFileWithHandle, saveFileAs, reopenFile } from "./editor/fileService";
import { cleanupOrphans, updateHandleName } from "./editor/fileHandleStore";
import { setHangulWritingMode } from "./editor/hangulBlockPlugin";
import { candidateEngine } from "./editor/candidateEngine";
import type { CandidateSource, CandidateSourceState } from "./editor/candidateEngine";
import "./App.css";

export type PanelMode = "kage" | "ruby" | "annotation" | "search" | null;
export type WritingMode = "horizontal" | "vertical";

function App() {
  const [writingMode, setWritingMode] = useState<WritingMode>("horizontal");
  const [panelMode, setPanelMode] = useState<PanelMode>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [kageInitial, setKageInitial] = useState<{ name: string; data: string }>({ name: "", data: "" });
  const [kageKey, setKageKey] = useState(0);
  const editorRef = useRef<EditorHandle>(null);

  // 文件管理状态
  const [showFileSidebar, setShowFileSidebar] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [currentFileName, setCurrentFileName] = useState("");
  const [recentFiles, setRecentFiles] = useState<RecentFile[]>(() => loadRecentFiles());
  const [fileHandleId, setFileHandleId] = useState<number | undefined>();

  // 格式激活状态 (Toolbar 高亮)
  const [boldActive, setBoldActive] = useState(false);
  const [italicActive, setItalicActive] = useState(false);
  const [headingLevel, setHeadingLevel] = useState(0);

  // 候选数据源开关 (Toolbar 下拉)
  const [candEnabled, setCandEnabled] = useState<CandidateSourceState>(() => candidateEngine.getEnabled());

  // 侧栏编辑目标 (ruby / 双行小字)
  const [rubyTarget, setRubyTarget] = useState<RubyTarget | null>(null);
  const [annotationTarget, setAnnotationTarget] = useState<AnnotationTarget | null>(null);

  const toggleCandidateSource = useCallback((source: CandidateSource, on: boolean) => {
    candidateEngine.setEnabled(source, on);
    setCandEnabled(candidateEngine.getEnabled());
  }, []);

  // 全局回调: 编辑器右键 → 打开 KAGE 面板并传入字形数据
  (window as any).__sendToKage = (name: string, data: string) => {
    setKageInitial({ name, data });
    setKageKey((v) => v + 1);
    setPanelMode("kage");
    setShowPanel(true);
  };

  // 全局回调: 右键"双行小字注释" → 打开双行编辑面板
  (window as any).__openAnnotationPanel = () => {
    setPanelMode("annotation");
    setShowPanel(true);
  };

  const toggleWritingMode = useCallback(() => {
    setWritingMode((prev) => (prev === "horizontal" ? "vertical" : "horizontal"));
  }, []);

  const openPanel = useCallback((mode: PanelMode) => {
    if (panelMode === mode && showPanel) {
      setShowPanel(false);
      setPanelMode(null);
    } else {
      setPanelMode(mode);
      setShowPanel(true);
    }
  }, [panelMode, showPanel]);

  const insertText = useCallback((text: string) => {
    editorRef.current?.insertAtCursor(text);
  }, []);

  /** 选区是否含 ruby/双行块 (含块时格式只能包块外, 不能改写块内容) */
  const selectionHasBlock = useCallback((from: number, to: number): boolean => {
    const editor = editorRef.current?.getEditor();
    if (!editor) return false;
    let has = false;
    editor.state.doc.nodesBetween(from, to, (n) => {
      if (n.type.name === "rubyBlock" || n.type.name === "doubleLine") { has = true; return false; }
      return true;
    });
    return has;
  }, []);

  const toggleBold = useCallback(() => {
    const editor = editorRef.current?.getEditor();
    if (!editor) return;
    const { state } = editor;
    const { from, to, empty } = state.selection;
    if (empty) {
      // 无选区: 不生效, 仅聚焦
      editor.chain().focus().run();
      return;
    }
    if (selectionHasBlock(from, to)) {
      // 选区含块: 保留块, 只在前后插 ** 标记 (markdown 作用于块外整体)
      editor.chain().focus().insertContentAt(from, "**").insertContentAt(to + 2, "**").run();
    } else {
      // 选区: 包裹 **...**
      const text = state.doc.textBetween(from, to);
      editor.chain().focus().deleteRange({ from, to }).insertContent(`**${text}**`).run();
    }
  }, [selectionHasBlock]);
  const toggleItalic = useCallback(() => {
    const editor = editorRef.current?.getEditor();
    if (!editor) return;
    const { state } = editor;
    const { from, to, empty } = state.selection;
    if (empty) {
      // 无选区: 不生效, 仅聚焦
      editor.chain().focus().run();
      return;
    }
    if (selectionHasBlock(from, to)) {
      editor.chain().focus().insertContentAt(from, "*").insertContentAt(to + 1, "*").run();
    } else {
      const text = state.doc.textBetween(from, to);
      editor.chain().focus().deleteRange({ from, to }).insertContent(`*${text}*`).run();
    }
  }, [selectionHasBlock]);
  const cycleHeading = useCallback(() => {
    const editor = editorRef.current?.getEditor();
    if (!editor) return;
    const { state } = editor;
    const { from } = state.selection;
    const $pos = state.doc.resolve(from);
    // 找到实际段落节点 (避免 hardcoded depth=1)
    let paraDepth = -1;
    for (let d = $pos.depth; d >= 0; d--) {
      if ($pos.node(d).type.name === "paragraph") { paraDepth = d; break; }
    }
    if (paraDepth < 0) {
      editor.chain().focus().insertContent("# ").run();
      return;
    }
    const para = $pos.node(paraDepth);
    const text: string = para.textContent || "";
    const m = text.match(/^(#{1,4})\s/);
    // 段落内容起点 (node.start() 即内容起始位置, 无需 +1)
    const contentStart = $pos.start(paraDepth);
    const tr = state.tr;
    if (m) {
      const currentLevel = m[1].length;
      if (currentLevel >= 4) {
        tr.delete(contentStart, contentStart + m[0].length);
      } else {
        const newMarker = "#".repeat(currentLevel + 1);
        tr.replaceWith(contentStart, contentStart + m[1].length, state.schema.text(newMarker));
      }
    } else {
      tr.insertText("# ", contentStart);
    }
    editor.view.dispatch(tr);
    editor.view.focus();
  }, []);

  /** KAGE 编辑器 Ctrl+S → 更新字体映射; 仅全新字形才插入光标处 */
  const insertKageGlyph = useCallback((kageData: string, glyphName: string) => {
    const editor = editorRef.current?.getEditor();
    if (!editor) return;

    let svgData = "";
    const engine = (window as any).__kageEngine;
    if (engine?.ready) {
      try {
        svgData = engine.renderKageData(kageData) || "";
      } catch (e) {
        console.warn("[App] renderKageData failed:", e);
      }
    }

    if (svgData && glyphName) {
      const exists = glyphFontManager.hasMapping(glyphName);
      const pua = glyphFontManager.updatePuaSvg(glyphName, svgData, kageData);
      if (pua > 0) {
        glyphFontManager.buildFont();
        // 已有字形: 只更新字体, 文档中所有该 PUA 字符自动刷新; 全新字形: 插入光标处
        if (!exists) {
          const { state } = editor;
          const mark = state.schema.marks.idsMark.create({ idsSource: glyphName, pua });
          const textNode = state.schema.text(String.fromCodePoint(pua), [mark]);
          editor.chain().focus().insertContent(textNode).run();
        }
        return;
      }
    }

    // 兜底: 无 SVG 或无名称 → 插入 kageGlyph 节点
    editor.chain().focus().insertContent({
      type: "kageGlyph",
      attrs: { kageData, svgData, glyphName },
    }).run();
  }, []);

  // ============================================================
  // 文件操作
  // ============================================================

  const handleEditorUpdate = useCallback(() => {
    setIsDirty(true);
    const ed = editorRef.current?.getEditor();
    if (ed) {
      // 源码模式: 简单检测光标周围是否有 ** / * / # 标记
      const { state } = ed;
      const { from, empty } = state.selection;
      let bold = false, italic = false, hLv = 0;
      if (empty) {
        const $pos = state.doc.resolve(from);
        const ctx = state.doc.textBetween(Math.max(0, from - 10), Math.min(state.doc.content.size, from + 10));
        bold = /\*\*/.test(ctx);
        italic = /(?<!\*)\*(?!\*)/.test(ctx);
        const para = $pos.node(1);
        if (para?.type.name === "paragraph") {
          const m = (para.textContent || "").match(/^(#{1,4})\s/);
          if (m) hLv = m[1].length;
        }
      }
      setBoldActive(bold);
      setItalicActive(italic);
      setHeadingLevel(hLv);
    }
  }, []);

  const handleNew = useCallback(() => {
    glyphFontManager.clearAll();
    editorRef.current?.setContent("");
    setCurrentFileName("");
    setFileHandleId(undefined);
    setIsDirty(false);
  }, []);

  // 共享的加载逻辑: parse + render glyphs + setContent
  const loadDocument = useCallback(async (name: string, content: string, handleId?: number) => {
    const doc = parseIdsmd(content);
    if (!doc) return;

    const textMatch = content.match(/<text>([\s\S]*?)<\/text>/);
    const rawText = textMatch ? textMatch[1].trim() : content.trim();

    glyphFontManager.clearAll();
    const engine = (window as any).__kageEngine;

    for (const g of doc.glyphs) {
      if (g.kageData && engine?.ready) {
        try {
          const svg = engine.renderKageData(g.kageData) || "";
          if (svg) glyphFontManager.updatePuaSvg(g.name, svg, g.kageData);
        } catch { /* skip */ }
      }
    }

    let processedText = rawText;
    const kageRe = /@([^@]+)@/g;
    const inlineReplacements: { match: string; replacement: string }[] = [];

    let km;
    while ((km = kageRe.exec(rawText)) !== null) {
      const kageData = km[1].trim();
      if (!kageData) continue;

      let gname = "";
      for (const g of doc.glyphs) {
        if (g.kageData === kageData) { gname = g.name; break; }
      }
      if (!gname) {
        let hash = 0;
        for (let i = 0; i < kageData.length; i++) {
          hash = ((hash << 5) - hash) + kageData.charCodeAt(i);
          hash |= 0;
        }
        gname = `_kage_${Math.abs(hash).toString(36)}`;
      }

      let pua = -1;
      if (engine?.ready) {
        try {
          const svg = engine.renderKageData(kageData) || "";
          if (svg) pua = glyphFontManager.updatePuaSvg(gname, svg, kageData);
        } catch { /* skip */ }
      }

      if (pua > 0) {
        inlineReplacements.push({
          match: km[0],
          replacement: `<span class="ids-glyph" data-ids-source="${gname.replace(/"/g, '&quot;')}" data-pua="${pua}">${String.fromCodePoint(pua)}</span>`,
        });
      }
    }

    for (let i = inlineReplacements.length - 1; i >= 0; i--) {
      processedText = processedText.split(inlineReplacements[i].match).join(inlineReplacements[i].replacement);
    }

    await glyphFontManager.buildFont();

    const html = convertInlineAnnotations(markdownToHtml(processedText));
    editorRef.current?.setContent(html);
    setCurrentFileName(name);
    setFileHandleId(handleId);
    setShowFileSidebar(false);

    if (handleId != null) {
      saveRecentFile({ name, handleId, timestamp: Date.now() });
      setRecentFiles(loadRecentFiles());
    }

    const editorView = editorRef.current?.getEditor()?.view;
    const tryRecompose = (retries: number) => {
      if ((window as any).__recomposeIds) {
        (window as any).__recomposeIds(editorView);
        setIsDirty(false);
      } else if (retries > 0) {
        setTimeout(() => tryRecompose(retries - 1), 300);
      } else {
        console.warn("[App] __recomposeIds not available after retries");
        setIsDirty(false);
      }
    };
    setTimeout(() => tryRecompose(10), 300);
  }, []);

  const handleOpen = useCallback(async () => {
    const result = await openFileWithPicker();
    if (!result) return;
    await loadDocument(result.name, result.content, result.handleId);
  }, [loadDocument]);

  const handleSave = useCallback(async () => {
    const html = editorRef.current?.getHTML() ?? "";
    const entries = glyphFontManager.getAllKageEntries();
    const glyphs = entries.map(([name, _pua, kageData]) => ({
      name,
      kageData: kageData ?? "",
    }));
    const content = serializeIdsmd(glyphs, html);
    const filename = currentFileName || "未命名";

    const result = await saveFileWithHandle(content, filename, fileHandleId);
    if (result.handleId) {
      setFileHandleId(result.handleId);
    }
    const savedName = result.newName || filename;

    saveRecentFile({ name: savedName, handleId: result.handleId ?? fileHandleId, timestamp: Date.now() });
    setRecentFiles(loadRecentFiles());
    if (result.newName) setCurrentFileName(result.newName);
    setIsDirty(false);

    // 清理 IndexedDB 中无效的句柄
    const validIds = loadRecentFiles().map(f => f.handleId).filter((id): id is number => id != null);
    if (result.handleId && !validIds.includes(result.handleId)) validIds.push(result.handleId);
    cleanupOrphans(validIds);
  }, [currentFileName, fileHandleId]);

  const handleSaveAs = useCallback(async () => {
    const html = editorRef.current?.getHTML() ?? "";
    const entries = glyphFontManager.getAllKageEntries();
    const glyphs = entries.map(([name, _pua, kageData]) => ({
      name,
      kageData: kageData ?? "",
    }));
    const content = serializeIdsmd(glyphs, html);
    const filename = currentFileName || "未命名";

    const result = await saveFileAs(content, filename);
    if (result.handleId) {
      setFileHandleId(result.handleId);
      if (result.newName) setCurrentFileName(result.newName);
      saveRecentFile({ name: result.newName || filename, handleId: result.handleId, timestamp: Date.now() });
      setRecentFiles(loadRecentFiles());
    }
  }, [currentFileName]);

  const handleOpenRecent = useCallback(async (entry: RecentFile) => {
    if (entry.handleId == null) {
      // 降级: 尝试从 localStorage 备份恢复
      const backup = localStorage.getItem(`idsmd_backup_${entry.name}`);
      if (backup) {
        await loadDocument(entry.name, backup);
        return;
      }
      alert(`无法直接打开 "${entry.name}"。\n\n该文件是在不支持文件系统访问的浏览器中保存的，请使用"打开"按钮重新选择文件。`);
      return;
    }

    const result = await reopenFile(entry.handleId);
    if (result) {
      await loadDocument(result.name, result.content, result.handleId);
      saveRecentFile({ name: result.name, handleId: result.handleId, timestamp: Date.now() });
      setRecentFiles(loadRecentFiles());
    } else {
      alert(`无法打开 "${entry.name}"。\n\n文件可能已被移动、重命名或删除。请使用"打开"按钮重新选择文件。`);
      // 移除失效的句柄
      const files = loadRecentFiles().filter(f => f.handleId !== entry.handleId);
      localStorage.setItem("idsmd_recent_files", JSON.stringify(files));
      setRecentFiles(files);
    }
  }, [loadDocument]);

  const handleRename = useCallback((newName: string) => {
    setCurrentFileName(newName);
    if (fileHandleId != null) {
      updateHandleName(fileHandleId, newName);
    }
  }, [fileHandleId]);

  // 键盘快捷键
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const ctrl = e.ctrlKey || e.metaKey;
      if (!ctrl) return;

      if (e.key === "n" || e.key === "N") {
        e.preventDefault();
        handleNew();
      } else if (e.key === "o" || e.key === "O") {
        e.preventDefault();
        handleOpen();
      } else if (e.key === "s" || e.key === "S") {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleNew, handleOpen, handleSave]);

  // 同步书写模式到 hangulBlockPlugin + 触发重新装饰
  useEffect(() => {
    setHangulWritingMode(writingMode);
    // 下发空事务强制 ProseMirror 插件重新计算 decorations
    const ed = editorRef.current?.getEditor();
    if (ed) {
      const { state } = ed;
      ed.view.dispatch(state.tr.setMeta("hangulBlock", writingMode));
    }
  }, [writingMode]);

  return (
    <div className={`app ${writingMode}`}>
      <Toolbar
        writingMode={writingMode}
        onToggleWritingMode={toggleWritingMode}
        onOpenPanel={openPanel}
        panelMode={showPanel ? panelMode : null}
        onInsertText={insertText}
        onNewFile={handleNew}
        onOpenFile={handleOpen}
        onSaveFile={handleSave}
        onToggleFileSidebar={() => setShowFileSidebar((v) => !v)}
        showFileSidebar={showFileSidebar}
        onToggleBold={toggleBold}
        onToggleItalic={toggleItalic}
        onCycleHeading={cycleHeading}
        boldActive={boldActive}
        italicActive={italicActive}
        headingLevel={headingLevel}
        candEnabled={candEnabled}
        onToggleCandidate={toggleCandidateSource}
      />
      <div className="main-area">
        {showFileSidebar && (
          <FileSidebar
            currentFileName={currentFileName}
            isDirty={isDirty}
            onNew={handleNew}
            onOpen={handleOpen}
            onSave={handleSave}
            onSaveAs={handleSaveAs}
            onClose={() => setShowFileSidebar(false)}
            onOpenRecent={handleOpenRecent}
            onRename={handleRename}
            recentFiles={recentFiles}
          />
        )}
        <Editor
          ref={editorRef}
          writingMode={writingMode}
          onEditorUpdate={handleEditorUpdate}
          onRubyTargetChange={setRubyTarget}
          onAnnotationTargetChange={setAnnotationTarget}
        />
        {showPanel && (
          <>
            <div className="panel-resize-handle" />
            <SidePanel
              mode={panelMode!}
              onClose={() => { setShowPanel(false); setPanelMode(null); }}
              onInsertKageGlyph={insertKageGlyph}
              kageInitialName={kageInitial.name}
              kageInitialData={kageInitial.data}
              kageKey={kageKey}
              rubyTarget={rubyTarget}
              annotationTarget={annotationTarget}
              onInsertRuby={(base, rt) => { /* console.log("[App] onInsertRuby", JSON.stringify({ base, rt })); // DEBUG */ editorRef.current?.insertRubyBlock?.(base, rt); }}
              onUpdateRuby={(pos, base, rt) => { /* console.log("[App] onUpdateRuby", pos, JSON.stringify({ base, rt })); // DEBUG */ editorRef.current?.updateRubyNode?.(pos, base, rt); }}
              onInsertAnnotation={(text) => { /* console.log("[App] onInsertAnnotation", JSON.stringify(text)); // DEBUG */ editorRef.current?.insertDoubleLine?.(text); }}
              onUpdateAnnotation={(pos, text) => { /* console.log("[App] onUpdateAnnotation", pos, JSON.stringify(text)); // DEBUG */ editorRef.current?.updateDoubleLineNode?.(pos, text); }}
            />
          </>
        )}
      </div>
      <div className="status-bar">
        <span className="status-item">{currentFileName || "未命名"}{isDirty ? " *" : ""}</span>
        <span className="status-item">{writingMode === "horizontal" ? "横排" : "竖排"}</span>
        <span className="status-item">第 1 行, 第 1 列</span>
      </div>
    </div>
  );
}

export default App;
