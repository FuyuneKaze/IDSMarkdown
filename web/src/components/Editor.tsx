import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { WritingMode } from "../App";
import { useImperativeHandle, forwardRef, useEffect, useState, useRef, useLayoutEffect, useCallback } from "react";
import type { Editor as TipTapEditor } from "@tiptap/core";
import { IdsNumpad } from "../editor/idsNumpad";
import { IdsGlyphNode } from "../editor/idsGlyph";
import { KageGlyphNode } from "../editor/kageGlyph";
import { IdsComposeExtension } from "../editor/idsCompose";
import { IdsMark } from "../editor/idsMark";
import { glyphFontManager } from "../editor/glyphFontManager";
import { KageEngine } from "../editor/kageEngine";
import { MarkdownStyle } from "../editor/markdownStylePlugin";
import { HangulBlock } from "../editor/hangulBlockPlugin";
import { ipaDatabase, logicalNameFromCode } from "../editor/ipaDatabase";
import { candidateEngine } from "../editor/candidateEngine";
import { RubyBlock } from "../editor/rubyBlock";
import { DoubleLine } from "../editor/doubleLine";
// import { TextSelection } from "@tiptap/pm/state"; // 原右键"双行小字注释"插入用, 入口已移到工具栏
import CandidatePopup from "./CandidatePopup";
import type { CandPopupState } from "./CandidatePopup";

export interface RubyTarget { pos: number; base: string; rt: string; }
export interface AnnotationTarget { pos: number; text: string; }

const PUA_START = 0xE000;
const PUA_END = 0xE8FF;

export interface EditorHandle {
  insertAtCursor: (text: string) => void;
  getEditor: () => TipTapEditor | null;
  getHTML: () => string;
  setContent: (html: string) => void;
  insertRubyBlock?: (base?: string, rt?: string) => void;
  insertDoubleLine?: (text?: string) => void;
  updateRubyNode?: (pos: number, base: string, rt: string) => void;
  updateDoubleLineNode?: (pos: number, text: string) => void;
}

interface EditorProps {
  writingMode: WritingMode;
  onEditorUpdate?: () => void;
  onRubyTargetChange?: (target: RubyTarget | null) => void;
  onAnnotationTargetChange?: (target: AnnotationTarget | null) => void;
}

const initialContent = [
  '<p># IDS 文本编辑器</p>',
  '<p>1. 输入U内字符ids表达式可实现替换：⿰ 白 勺→⿰白勺</p>',
  '<p>2. 可通过`alt+Numpad0~9/+/-`输入**二元**ids运算符，`ctrl+alt+Numpad+/-`输入**三元**运算符</p>',
  '<p>3. 可输入合法裸ids表达式与普通文本混排，立即合成，退格展开，可修改。比如“我的⿰名字是⿵代物”</p>',
  '<p>4. 点击右上角*“KAGE”*按钮可自定义字形与名称并插入文本，光标在合成字形附近右键亦可对其进行编辑</p>',
  '<p>5. 英文输入法下`alt+若干下主键盘字母/数字键`可输入IPA符号</p>',
  '<p>6. 下拉*“候选”*可点选四种候选框开启，使用英文输入法输入拉丁字母即可联想</p>',
].join('\n');

const Editor = forwardRef<EditorHandle, EditorProps>(function Editor(
  { writingMode, onEditorUpdate, onRubyTargetChange, onAnnotationTargetChange }, ref
) {
  const [kageStatus, setKageStatus] = useState("loading"); // "loading" | "ready" | "error"
  const editorRef = useRef<TipTapEditor | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // IPA 循环状态
  const ipaCycleRef = useRef<{ logical: string; index: number; insertPos: number; insertLen: number } | null>(null);

  // 候选状态
  const [candState, setCandState] = useState<CandPopupState | null>(null);
  const candStateRef = useRef<CandPopupState | null>(null);
  // 同步 ref 避免 handleKeyDown 闭包过期
  useEffect(() => { candStateRef.current = candState; }, [candState]);
  const [candPos, setCandPos] = useState<{ left: number; top: number } | null>(null);
  const candBufRef = useRef<{ query: string; queryPos: number; lastAcceptPos: number; opInProgress: boolean }>({
    query: "", queryPos: -1, lastAcceptPos: -1, opInProgress: false,
  });

  const isLatinChar = (s: string): boolean => /^[a-zA-Z']$/.test(s);

  // 侧栏目标检测回调 (保最新, 避免事件闭包过期)
  const rubyTargetRef = useRef(onRubyTargetChange);
  useEffect(() => { rubyTargetRef.current = onRubyTargetChange; }, [onRubyTargetChange]);
  const annotationTargetRef = useRef(onAnnotationTargetChange);
  useEffect(() => { annotationTargetRef.current = onAnnotationTargetChange; }, [onAnnotationTargetChange]);

  useEffect(() => {
    const engine = new KageEngine();
    (window as any).__kageEngine = engine;
    // core_glyphs.json 是 100+MB 的数据, 不进仓库; 部署时可能根本没有这个文件。
    // 打开远程兜底后, 缺失的字形会按需从 GlyphWiki API 取 (慢一点, 但纯静态可用)。
    engine.enableRemoteFallback();
    engine.loadCoreGlyphs()
      .then(() => {
        setKageStatus("ready");
        console.log("[Editor] KAGE engine ready (bundled + remote fallback)");
        // KAGE 就绪后重新合成文档中的未编码 IDS (补上 SVG 数据)
        setTimeout(() => {
          (window as any).__recomposeIds?.();
        }, 100);
      })
      .catch((e) => {
        console.error("[Editor] KAGE engine load failed:", e);
      });
  }, []);

  // 加载 IPA 和候选引擎
  useEffect(() => {
    ipaDatabase.load().catch((e: any) => console.error("[Editor] IPA load failed:", e));
    candidateEngine.loadData()
      .then(() => {
        console.log("[Editor] 候选引擎就绪, 检查是否有待查询的拉丁文本");
        updateCandidatePopup();
      })
      .catch((e: any) => console.error("[Editor] Candidate load failed:", e));
    // 注册就绪回调 (用于懒加载场景: query 触发加载, 就绪后自动弹出)
    candidateEngine.onReady(() => {
      console.log("[Editor] onReady 回调触发, 重新查询候选");
      updateCandidatePopup();
    });
  }, []);

  // Alt 松手重置 IPA 循环
  useEffect(() => {
    const onKeyUp = (e: KeyboardEvent) => {
      if (e.key === "Alt") ipaCycleRef.current = null;
    };
    window.addEventListener("keyup", onKeyUp);
    return () => window.removeEventListener("keyup", onKeyUp);
  }, []);

  // 竖排模式: 滚轮 deltaY → 水平滚动
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // DEBUG: 竖排滚轮日志 (2026-07-31)
    // console.log("[wheel] useEffect 安装, writingMode =", writingMode);
    // console.log("[wheel] container =", container.className,
    //   "| scrollWidth:", container.scrollWidth, "clientWidth:", container.clientWidth,
    //   "| overflow:", getComputedStyle(container).overflowX, getComputedStyle(container).overflowY);

    const onWheel = (e: WheelEvent) => {
      if (writingMode !== "vertical") {
        // console.log("[wheel] 跳过: writingMode =", writingMode);
        return;
      }

      // 从事件目标向上查找可水平滚动的元素
      let target = e.target as HTMLElement | null;
      // DEBUG: 遍历路径日志 (2026-07-31)
      // const path: string[] = [];
      while (target && target !== document.body) {
        // const cls = target.className?.toString?.() || target.tagName;
        // path.push(`${cls}(${target.scrollWidth}vs${target.clientWidth})`);
        if (target.scrollWidth > target.clientWidth) {
          // console.log("[wheel] 命中! path:", path.join(" → "),
          //   "| deltaY:", e.deltaY, "| scrollLeft:", target.scrollLeft,
          //   "→", target.scrollLeft + e.deltaY + e.deltaX);
          e.preventDefault();
          // 竖排阅读方向: 滚轮向下/双指左滑 = 翻下一页 (下一列在左侧) → 视口左移
          target.scrollLeft -= e.deltaY + e.deltaX;
          return;
        }
        if (target === container) break;
        target = target.parentElement;
      }
      // console.log("[wheel] 未找到可滚动元素! path:", path.join(" → "),
      //   "| deltaY:", e.deltaY);
    };

    container.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      // console.log("[wheel] useEffect 卸载");
      container.removeEventListener("wheel", onWheel);
    };
  }, [writingMode]);

  // 竖排: 内容右对齐, 初始滚动到最右端 (第一列)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const adjust = () => {
      container.scrollLeft = writingMode === "vertical" ? container.scrollWidth : 0;
    };
    adjust();
    requestAnimationFrame(adjust); // 布局完成后再次对齐 (字体/字形宽度可能延迟)
  }, [writingMode]);

  // ── 候选交互函数 ──

  const updateCandidatePopup = useCallback(() => {
    const buf = candBufRef.current;
    console.log("[cand] updateCandidatePopup: query=", buf.query, "queryPos=", buf.queryPos);
    const rows = buf.query ? candidateEngine.query(buf.query) : [];
    console.log("[cand] query result rows:", rows.length, "first:", rows[0]?.candidates?.slice(0, 3));
    if (rows.length > 0) {
      setCandState({ rows, selRow: 0, selCol: 0, queryPos: buf.queryPos });
    } else {
      setCandState(null);
    }
  }, []);

  const cancelCandidate = useCallback(() => {
    setCandState(null);
    setCandPos(null);
    const buf = candBufRef.current;
    buf.query = "";
    buf.queryPos = -1;
    buf.lastAcceptPos = -1;
  }, []);

  const candidateLetter = useCallback((event: KeyboardEvent) => {
    const ed = editorRef.current;
    if (!ed) { console.log("[cand] candidateLetter: no editor"); return; }
    const view = ed.view;
    const buf = candBufRef.current;
    buf.opInProgress = true;
    const letter = event.key.toLowerCase();
    console.log("[cand] candidateLetter key:", event.key, "-> letter:", letter, "| query:", buf.query, "| queryPos:", buf.queryPos);
    // 插入保留原始大小写, query 用小写匹配
    view.dispatch(view.state.tr.insertText(event.key));
    console.log("[cand] dispatch done, view.state.doc:", view.state.doc.textContent);

    if (buf.query) {
      buf.query += letter;
    } else {
      const pos = view.state.selection.from;
      let start = pos;
      const limit = buf.lastAcceptPos >= 0 ? buf.lastAcceptPos : 0;
      const doc = view.state.doc;
      while (start > limit) {
        const before = doc.textBetween(start - 1, start);
        if (isLatinChar(before)) start--;
        else break;
      }
      let end = pos;
      while (end < doc.content.size) {
        const after = doc.textBetween(end, end + 1);
        if (isLatinChar(after)) end++;
        else break;
      }
      buf.query = doc.textBetween(start, end).toLowerCase();
      buf.queryPos = start;
    }
    try {
      updateCandidatePopup();
    } catch (e) {
      console.error("[cand] updateCandidatePopup 崩溃:", e);
    }
    buf.opInProgress = false;
  }, [updateCandidatePopup]);

  const acceptCandidate = useCallback((row?: number, col?: number) => {
    const state = candStateRef.current;
    const ed = editorRef.current;
    if (!ed || !state) return;
    const r = row ?? state.selRow;
    const c = col ?? state.selCol;
    if (r < 0 || r >= state.rows.length) return;
    const rowData = state.rows[r];
    if (c < 0 || c >= rowData.candidates.length) return;

    const text = rowData.candidates[c].replace(/^\x00/, "");
    const buf = candBufRef.current;
    buf.opInProgress = true;

    const view = ed.view;
    const tr = view.state.tr;
    tr.replaceWith(buf.queryPos, buf.queryPos + rowData.consumeLen, view.state.schema.text(text));
    view.dispatch(tr);

    buf.lastAcceptPos = buf.queryPos + text.length;
    setCandState(null);

    // 剩余字母继续查询
    const remaining = buf.query.slice(rowData.consumeLen);
    if (remaining) {
      buf.query = remaining;
      buf.queryPos = buf.lastAcceptPos;
      try {
        const rows = candidateEngine.query(remaining);
        if (rows.length > 0) {
          setCandState({ rows, selRow: 0, selCol: 0, queryPos: buf.queryPos });
        }
      } catch (e) {
        console.error("[cand] acceptCandidate 剩余查询崩溃:", e);
      }
    } else {
      buf.query = "";
      buf.queryPos = -1;
    }
    buf.opInProgress = false;
  }, []);

  const moveCandidateSelection = useCallback((dRow: number, dCol: number) => {
    const state = candStateRef.current;
    if (!state) return;
    const nRows = state.rows.length;
    let newRow = state.selRow + dRow;
    if (newRow < 0) newRow = nRows - 1;
    if (newRow >= nRows) newRow = 0;
    let newCol: number;
    if (dCol !== 0) {
      // 左右: 越过行末 → 下一行开头, 越过行首 → 上一行末尾
      const curCols = state.rows[state.selRow].candidates.length;
      if (dCol > 0 && state.selCol >= curCols - 1) {
        newRow = state.selRow + 1;
        if (newRow >= nRows) newRow = 0;
        newCol = 0;
      } else if (dCol < 0 && state.selCol <= 0) {
        newRow = state.selRow - 1;
        if (newRow < 0) newRow = nRows - 1;
        newCol = state.rows[newRow].candidates.length - 1;
      } else {
        newCol = state.selCol + dCol;
      }
    } else {
      // 上下: 列归零
      newCol = 0;
    }
    setCandState(prev => prev ? { ...prev, selRow: newRow, selCol: newCol } : null);
  }, []);

  const selectCandidateRowByDigit = useCallback((digit: number) => {
    const state = candStateRef.current;
    if (!state) return;
    const idx = digit === 0 ? 9 : digit - 1;
    if (digit === 1 && state.selRow === 0 && state.selCol === 0) {
      acceptCandidate(0, 0);
      return;
    }
    if (idx < state.rows.length) {
      setCandState(prev => prev ? { ...prev, selRow: idx, selCol: 0 } : null);
    }
  }, [acceptCandidate]);

  const candidateBackspace = useCallback(() => {
    const buf = candBufRef.current;
    const ed = editorRef.current;
    if (!ed) return;
    // 同步删除文档中 query 的最后一个字符, 保持 query 与正文一致
    const view = ed.view;
    const delStart = buf.queryPos + buf.query.length - 1;
    const delEnd = buf.queryPos + buf.query.length;
    if (delStart >= buf.queryPos && delEnd <= view.state.doc.content.size) {
      buf.opInProgress = true;
      view.dispatch(view.state.tr.delete(delStart, delEnd));
      buf.opInProgress = false;
    }
    if (buf.query.length <= 1) {
      cancelCandidate();
    } else {
      buf.query = buf.query.slice(0, -1);
      try {
        updateCandidatePopup();
      } catch (e) {
        console.error("[cand] candidateBackspace updateCandidatePopup 崩溃:", e);
      }
    }
  }, [cancelCandidate, updateCandidatePopup]);

  // ── Popup 定位 ──
  const updateCandPos = useCallback(() => {
    const state = candStateRef.current;
    const ed = editorRef.current;
    const container = containerRef.current;
    if (!ed || !container || !state) return;
    const coords = ed.view.coordsAtPos(state.queryPos);
    const rect = container.getBoundingClientRect();
    const left = coords.left - rect.left;
    const top = coords.bottom - rect.top + 4;
    setCandPos({
      left: Math.max(4, Math.min(left, rect.width - 260)),
      top: Math.max(4, top),
    });
  }, []);

  useLayoutEffect(() => {
    updateCandPos();
  }, [candState?.queryPos, candState?.rows, updateCandPos]);

  // scroll/resize 重定位
  useEffect(() => {
    if (!candState) return;
    const container = containerRef.current;
    if (!container) return;
    const onScroll = () => updateCandPos();
    container.addEventListener("scroll", onScroll, { capture: true });
    window.addEventListener("resize", onScroll);
    return () => {
      container.removeEventListener("scroll", onScroll, { capture: true });
      window.removeEventListener("resize", onScroll);
    };
  }, [candState, updateCandPos]);

  // 失焦取消候选
  useEffect(() => {
    const ed = editorRef.current;
    if (!ed) return;
    const onBlur = () => { if (candBufRef.current.query) cancelCandidate(); };
    ed.on("blur", onBlur);
    return () => { ed.off("blur", onBlur); };
  }, [cancelCandidate]);

  // selectionUpdate 跟踪 (光标越界取消)
  useEffect(() => {
    const ed = editorRef.current;
    if (!ed) return;
    const onSelUpdate = () => {
      const buf = candBufRef.current;
      if (!buf.query || buf.opInProgress) return;
      const sel = ed.view.state.selection;
      if (!sel.empty) return;
      const pos = sel.from;
      if (pos < buf.queryPos || pos > buf.queryPos + buf.query.length) {
        cancelCandidate();
      }
    };
    ed.on("selectionUpdate", onSelUpdate);
    return () => { ed.off("selectionUpdate", onSelUpdate); };
  }, [cancelCandidate]);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        bold: false,
        italic: false,
        code: false,
        heading: false,
        blockquote: false,
        codeBlock: false,
        horizontalRule: false,
      }),
      IdsNumpad, IdsGlyphNode, KageGlyphNode, IdsMark, IdsComposeExtension, MarkdownStyle, HangulBlock,
      RubyBlock, DoubleLine,
    ],
    content: initialContent,
    onUpdate: () => {
      onEditorUpdate?.();
    },
    editorProps: {
      attributes: {
        class: "tiptap",
      },
      handleKeyDown: (view, event) => {
        console.log("[hkD] key:", event.key, "code:", event.code,
          "alt:", event.altKey, "ctrl:", event.ctrlKey, "meta:", event.metaKey,
          "composing:", event.isComposing,
          "candState:", !!candStateRef.current,
          "engineReady:", candidateEngine.isReady());
        // ── 1. 候选框可见时: 候选控制键 ──
        if (candStateRef.current) {
          if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
            acceptCandidate();
            return true;
          }
          if (event.key === "Escape") {
            cancelCandidate();
            return true;
          }
          if (event.key === " " && !event.ctrlKey && !event.altKey && !event.metaKey) {
            cancelCandidate();
            return false; // 放行空格
          }
          if (event.key === "ArrowUp") { moveCandidateSelection(-1, 0); return true; }
          if (event.key === "ArrowDown") { moveCandidateSelection(1, 0); return true; }
          if (event.key === "ArrowLeft") { moveCandidateSelection(0, -1); return true; }
          if (event.key === "ArrowRight") { moveCandidateSelection(0, 1); return true; }
          if (event.key >= "1" && event.key <= "9" && !event.ctrlKey && !event.altKey && !event.metaKey) {
            selectCandidateRowByDigit(parseInt(event.key));
            return true;
          }
          if (event.key === "Backspace" && !event.ctrlKey && !event.metaKey) {
            if (candBufRef.current.query.length > 0) {
              candidateBackspace();
              return true;
            }
            cancelCandidate();
            return false; // 落入现有字形展开
          }
          if (/^[a-zA-Z']$/.test(event.key) && !event.ctrlKey && !event.altKey && !event.metaKey && !event.isComposing) {
            candidateLetter(event);
            return true;
          }
        }

        // ── 2. Alt+Key (无 Ctrl/Meta, 非IME) → IPA 循环 ──
        if (event.altKey && !event.ctrlKey && !event.metaKey && !event.isComposing && ipaDatabase.isReady()) {
          const logical = logicalNameFromCode(event.code);
          if (logical) {
            const cands = ipaDatabase.candidates(logical, event.shiftKey);
            if (cands.length > 0) {
              const cycle = ipaCycleRef.current;
              const sel = view.state.selection;
              const sameCycle = !!cycle && cycle.logical === logical && sel.empty
                && sel.from === cycle.insertPos + cycle.insertLen;
              const idx = sameCycle ? (cycle.index + 1) % cands.length : 0;
              const insertPos = sameCycle ? cycle.insertPos : sel.from;
              const text = cands[idx];
              const tr = view.state.tr;
              if (sameCycle) {
                tr.replaceWith(insertPos, insertPos + cycle.insertLen, view.state.schema.text(text));
              } else {
                tr.insertText(text, insertPos);
              }
              view.dispatch(tr);
              ipaCycleRef.current = { logical, index: idx, insertPos, insertLen: text.length };
              return true;
            }
            // Alt+未映射键: 吞掉 (与C++一致)
            return true;
          }
        }

        // ── 3. 纯字母触发候选 ──
        if (/^[a-zA-Z']$/.test(event.key) && !event.ctrlKey && !event.altKey && !event.metaKey && !event.isComposing) {
          console.log("[hkD] step3: 纯字母触发候选, key:", event.key, "engineReady:", candidateEngine.isReady());
          candidateLetter(event);
          return true;
        }
        console.log("[hkD] step4+: 未匹配, key:", event.key, "| returning false");

        // ── 4. Backspace 时展开 IDS Glyph (原逻辑) ──
        if (event.key === "Backspace" && !event.ctrlKey && !event.metaKey) {
          const { selection } = view.state;
          if (!selection.empty) return false; // 有选区时不拦截

          const pos = selection.from;
          const node = view.state.doc.resolve(pos).nodeBefore;

          // ruby 块: 删最后一个汉字 + 最后一个注音字符; 只剩 1 字时删整块
          if (node?.type.name === "rubyBlock") {
            const from = pos - node.nodeSize;
            const baseCps = [...(node.attrs.base as string)];
            if (baseCps.length > 1) {
              const rtCps = [...(node.attrs.rt as string)];
              view.dispatch(view.state.tr.setNodeMarkup(
                from, null, { base: baseCps.slice(0, -1).join(""), rt: rtCps.slice(0, -1).join("") }));
            } else {
              view.dispatch(view.state.tr.delete(from, pos));
            }
            return true;
          }

          // 双行小字: 删最后一个字符; 只剩 1 字时删整块
          if (node?.type.name === "doubleLine") {
            const from = pos - node.nodeSize;
            const cps = [...(node.attrs.text as string)];
            if (cps.length > 1) {
              view.dispatch(view.state.tr.setNodeMarkup(from, null, { text: cps.slice(0, -1).join("") }));
            } else {
              view.dispatch(view.state.tr.delete(from, pos));
            }
            return true;
          }

          if (node?.type.name === "idsGlyph") {
            const idsSource = node.attrs.idsSource as string;
            const from = pos - node.nodeSize;
            const tr = view.state.tr;
            tr.setMeta("idsCompose", true);
            tr.replaceWith(from, pos, view.state.schema.text(idsSource));
            view.dispatch(tr);
            (window as any).__expandRange = { from, to: from + [...idsSource].length };
            return true;
          }

          // Mark-based PUA 文本: 只展开光标前一个字符 (避免合并的 text node 全部展开)
          if (node?.isText) {
            const text: string = node.text || "";
            const lastCharLen = text.length > 0 && text.charCodeAt(text.length - 1) >= 0xDC00 && text.charCodeAt(text.length - 1) <= 0xDFFF ? 2 : 1;
            const lastChar = text.slice(-lastCharLen);
            const lastCp = lastChar.codePointAt(0);

            const idsMark = node.marks.find((m: any) => m.type.name === "idsMark");
            if (idsMark) {
              const idsSource = idsMark.attrs.idsSource as string;
              const from = pos - lastCharLen;
              const tr = view.state.tr;
              tr.setMeta("idsCompose", true);
              tr.replaceWith(from, pos, view.state.schema.text(idsSource));
              view.dispatch(tr);
              (window as any).__expandRange = { from, to: from + [...idsSource].length };
              return true;
            }

            // 后备: code 标签内的 raw PUA 字符 (无 idsMark, 直接从 glyphFontManager 查)
            if (lastCp !== undefined && lastCp >= PUA_START && lastCp <= PUA_END) {
              const idsSource = glyphFontManager.getIdsSource(lastCp);
              if (idsSource) {
                const from = pos - lastCharLen;
                const tr = view.state.tr;
                tr.setMeta("idsCompose", true);
                tr.replaceWith(from, pos, view.state.schema.text(idsSource));
                view.dispatch(tr);
                (window as any).__expandRange = { from, to: from + [...idsSource].length };
                return true;
              }
            }
          }
        }
        return false;
      },
      // 右键: 检测字形 → 自定义菜单 "发送到 KAGE 编辑器"
      handleDOMEvents: {
        contextmenu: (view: any, event: MouseEvent) => {
          const pos = view.posAtCoords({ left: event.clientX, top: event.clientY });
          if (!pos) return false;

          const $pos = view.state.doc.resolve(pos.pos);
          let glyphName = "";
          let kageData = "";

          const engine = (window as any).__kageEngine;

          // 检查点击位置前后的节点
          for (const node of [$pos.nodeBefore, $pos.nodeAfter]) {
            if (!node) continue;

            if (node.type.name === "kageGlyph") {
              glyphName = node.attrs.glyphName || node.attrs.kageData?.slice(0, 20) || "glyph";
              kageData = node.attrs.kageData || "";
              break;
            }

            if (node.type.name === "idsGlyph") {
              const ids = node.attrs.idsSource || "";
              glyphName = ids;
              // 优先使用已编辑的 KAGE 数据, 否则从 IDS 重新生成
              kageData = glyphFontManager.getKageByIdsSource(ids)
                || (ids && engine?.ready ? engine.kageDataFromIds(ids) || "" : "");
              break;
            }

            if (node.isText) {
              const idsMark = node.marks.find((m: any) => m.type.name === "idsMark");
              if (idsMark) {
                const ids = idsMark.attrs.idsSource || "";
                const pua = idsMark.attrs.pua as number;
                glyphName = ids;
                // 优先使用已编辑的 KAGE 数据, 否则从 IDS 重新生成
                kageData = (pua > 0 ? glyphFontManager.getKageData(pua) : null)
                  || (ids && engine?.ready ? engine.kageDataFromIds(ids) || "" : "");
                break;
              }

              // 后备: code 标签内的 raw PUA 字符 (无 idsMark)
              const text: string = node.text || "";
              for (const ch of text) {
                const cp = ch.codePointAt(0);
                if (cp !== undefined && cp >= PUA_START && cp <= PUA_END) {
                  const idsSource = glyphFontManager.getIdsSource(cp);
                  if (idsSource) {
                    glyphName = idsSource;
                    kageData = glyphFontManager.getKageData(cp)
                      || (engine?.ready ? engine.kageDataFromIds(idsSource) || "" : "");
                    break;
                  }
                }
              }
              if (glyphName) break;
            }
          }

          // 未命中字形: 放行浏览器原生右键菜单 (复制/粘贴等), 双行注释入口在工具栏"注"按钮
          if (!glyphName) return false;

          event.preventDefault();

          // 移除旧菜单
          document.querySelector(".glyph-context-menu")?.remove();

          const menu = document.createElement("div");
          menu.className = "glyph-context-menu";
          menu.innerHTML = `<button>发送到 KAGE 编辑器</button>`;
          Object.assign(menu.style, {
            position: "fixed", left: `${event.clientX}px`, top: `${event.clientY}px`,
            zIndex: "10000", background: "var(--bg-surface, #2a2a2a)",
            border: "1px solid var(--border, #444)", borderRadius: "4px",
            padding: "4px", boxShadow: "0 4px 12px rgba(0,0,0,0.5)",
            minWidth: "180px",
          });

          const btn = menu.querySelector("button")!;
          Object.assign(btn.style, {
            padding: "6px 16px", border: "none", background: "transparent",
            color: "var(--text-primary, #ddd)", fontSize: "13px",
            cursor: "pointer", whiteSpace: "nowrap", borderRadius: "3px",
            width: "100%", textAlign: "left" as any,
          });
          btn.addEventListener("mouseenter", () => {
            btn.style.background = "var(--accent,rgb(128, 0, 21))";
            btn.style.color = "#fff";
          });
          btn.addEventListener("mouseleave", () => {
            btn.style.background = "transparent";
            btn.style.color = "var(--text-primary, #ddd)";
          });
          btn.addEventListener("click", () => {
            menu.remove();
            (window as any).__sendToKage?.(glyphName, kageData);
          });

          const dismiss = () => { menu.remove(); };
          setTimeout(() => document.addEventListener("click", dismiss, { once: true }), 0);

          document.body.appendChild(menu);
          return true;
        },
      },

      // 纯文本剪贴板: 原子节点回调 + PUA 后处理翻译为 IDS
      clipboardTextSerializer: (slice) => {
        let raw = slice.content.textBetween(0, slice.content.size, "\n", (node) => {
          if (node.type.name === "idsGlyph") {
            return node.attrs.unicode || node.attrs.idsSource || "";
          }
          if (node.type.name === "kageGlyph") {
            return node.attrs.glyphName || node.attrs.kageData || "";
          }
          if (node.type.name === "rubyBlock") {
            return node.attrs.base || "";
          }
          if (node.type.name === "doubleLine") {
            return node.attrs.text || "";
          }
          return "";
        });
        // 翻译 PUA 码点 → IDS 表达式 (textBetween 不对文本节点回调)
        const result: string[] = [];
        for (const ch of raw) {
          const cp = ch.codePointAt(0);
          if (cp !== undefined && cp >= PUA_START && cp <= PUA_END) {
            const ids = glyphFontManager.getIdsSource(cp);
            result.push(ids || ch);
          } else {
            result.push(ch);
          }
        }
        return result.join("");
      },
    },
  });

  editorRef.current = editor;

  // 光标旁节点检测: 上报侧栏正在编辑的 ruby/双行节点 (selectionUpdate + update 都要挂, undo/redo 只触发 update)
  const reportTargets = useCallback(() => {
    const ed = editorRef.current;
    if (!ed) return;
    const { selection } = ed.state;
    let rubyT: RubyTarget | null = null;
    let annoT: AnnotationTarget | null = null;
    // let beforeName = "-"; // DEBUG 与下方 [reportTargets] 日志配套
    // let afterName = "-"; // DEBUG
    if (selection.empty) {
      const $pos = ed.state.doc.resolve(selection.from);
      const before = $pos.nodeBefore;
      const after = $pos.nodeAfter;
      // beforeName = before?.type.name ?? "-"; // DEBUG
      // afterName = after?.type.name ?? "-"; // DEBUG
      if (before?.type.name === "rubyBlock") {
        rubyT = { pos: selection.from - before.nodeSize, base: before.attrs.base, rt: before.attrs.rt };
      } else if (after?.type.name === "rubyBlock") {
        rubyT = { pos: selection.from, base: after.attrs.base, rt: after.attrs.rt };
      }
      if (before?.type.name === "doubleLine") {
        annoT = { pos: selection.from - before.nodeSize, text: before.attrs.text };
      } else if (after?.type.name === "doubleLine") {
        annoT = { pos: selection.from, text: after.attrs.text };
      }
    }
    // console.log("[reportTargets] from:", selection.from, "empty:", selection.empty, "before:", beforeName, "after:", afterName, "→ ruby:", rubyT, "anno:", annoT); // DEBUG 侧栏目标检测
    rubyTargetRef.current?.(rubyT);
    annotationTargetRef.current?.(annoT);
  }, []);

  useEffect(() => {
    const ed = editorRef.current;
    if (!ed) return;
    reportTargets();
    ed.on("selectionUpdate", reportTargets);
    ed.on("update", reportTargets);
    return () => {
      ed.off("selectionUpdate", reportTargets);
      ed.off("update", reportTargets);
    };
  }, [reportTargets]);

  useImperativeHandle(ref, () => ({
    insertAtCursor: (text: string) => {
      editorRef.current?.chain().focus().insertContent(text).run();
    },
    getEditor: () => editorRef.current,
    getHTML: () => editorRef.current?.getHTML() ?? "",
    setContent: (html: string) => {
      editorRef.current?.commands.setContent(html);
    },
    insertRubyBlock: (base = "", rt = "") => {
      // console.log("[handle] insertRubyBlock:", JSON.stringify({ base, rt })); // DEBUG
      editorRef.current?.chain().focus()
        .insertContent({ type: "rubyBlock", attrs: { base, rt } }).run();
      // 块内 IDS 表达式即时注册 (新映射时强制重建块 DOM 显示合成字)
      (window as any).__scanBlocks?.();
    },
    insertDoubleLine: (text = "") => {
      // console.log("[handle] insertDoubleLine:", JSON.stringify(text)); // DEBUG
      editorRef.current?.chain().focus()
        .insertContent({ type: "doubleLine", attrs: { text } }).run();
      (window as any).__scanBlocks?.();
    },
    updateRubyNode: (pos, base, rt) => {
      // console.log("[handle] updateRubyNode:", pos, JSON.stringify({ base, rt })); // DEBUG
      const ed = editorRef.current;
      if (!ed) return;
      const node = ed.state.doc.nodeAt(pos);
      // if (!node || node.type.name !== "rubyBlock") console.log("[handle] updateRubyNode: node not found at", pos, node?.type.name); // DEBUG
      if (!node || node.type.name !== "rubyBlock") return;
      ed.view.dispatch(ed.state.tr.setNodeMarkup(pos, null, { base, rt }));
      (window as any).__scanBlocks?.();
    },
    updateDoubleLineNode: (pos, text) => {
      // console.log("[handle] updateDoubleLineNode:", pos, JSON.stringify(text)); // DEBUG
      const ed = editorRef.current;
      if (!ed) return;
      const node = ed.state.doc.nodeAt(pos);
      // if (!node || node.type.name !== "doubleLine") console.log("[handle] updateDoubleLineNode: node not found at", pos, node?.type.name); // DEBUG
      if (!node || node.type.name !== "doubleLine") return;
      ed.view.dispatch(ed.state.tr.setNodeMarkup(pos, null, { text }));
      (window as any).__scanBlocks?.();
    },
  }));

  return (
    <div className="editor-container" ref={containerRef}>
      <div className="editor-paper">
        <EditorContent editor={editor} />
        {kageStatus === "loading" && (
          <div style={{
            position: "fixed", bottom: "32px", right: "16px",
            padding: "6px 12px", background: "var(--bg-surface)",
            border: "1px solid var(--border)", borderRadius: "4px",
            fontSize: "12px", color: "var(--text-muted)", zIndex: 100,
          }}>
            字形数据加载中...
          </div>
        )}
      </div>
      {candState && candPos && (
        <CandidatePopup
          state={candState}
          left={candPos.left}
          top={candPos.top}
          onSelect={(r, c) => {
            setCandState(prev => prev ? { ...prev, selRow: r, selCol: Math.max(0, c) } : null);
          }}
          onAccept={(r, c) => acceptCandidate(r, c)}
          onCancel={cancelCandidate}
        />
      )}
    </div>
  );
});

export default Editor;
