import { useEffect, useRef, useCallback, useState } from "react";

interface KageEditorPanelProps {
  /** 用户 Ctrl+S 保存时回传 KAGE 数据 */
  onGlyphSubmit: (data: { name: string; kageData: string; related: string }) => void;
  /** 初始 KAGE 数据 (编辑已有字形, 可为空打开空白编辑器) */
  initialData?: string;
  /** 初始字形名 */
  initialName?: string;
}

const GLYPHWIKI_HOST = "zhs.glyphwiki.org";

/** 获取 KAGE 引擎引用 (加载在 Editor.tsx 的 useEffect 中) */
function getKageEngine() {
  return (window as any).__kageEngine;
}

export default function KageEditorPanel({
  onGlyphSubmit,
  initialData,
  initialName,
}: KageEditorPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loaded, setLoaded] = useState(false);

  // ============================================================
  // 构建初始 URL
  // ============================================================

  const buildUrl = useCallback(() => {
    const params = [`host=${GLYPHWIKI_HOST}`];
    if (initialData) {
      params.push(`data=${encodeURIComponent(initialData)}`);
    }
    return assetUrl(`/kage-editor/index.html#${params.join("&")}`);
  }, [initialData]);

  // ============================================================
  // postMessage 协议处理
  // ============================================================

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (!msg || typeof msg !== "object") return;

      switch (msg.type) {
        // ----- kage-editor 请求部件源数据 -----
        case "get-source": {
          const engine = getKageEngine();
          const data = engine?.getGlyphSource?.(msg.name) || null;
          iframeRef.current?.contentWindow?.postMessage(
            { type: "source-result", id: msg.id, data },
            "*"
          );
          break;
        }

        // ----- kage-editor 搜索部件名 -----
        case "search": {
          const engine = getKageEngine();
          const query = msg.query || "";
          console.log(`[KagePanel] search query: "${query}", engine ready: ${engine?.ready ?? false}, glyphs: ${engine?.ready ? "loaded" : "pending"}`);
          let data = "";
          if (engine?.ready) {
            data = engine.searchGlyphNames(query);
            console.log(`[KagePanel] search result length: ${data.length}`);
          } else {
            console.warn("[KagePanel] search: engine not ready yet");
          }
          iframeRef.current?.contentWindow?.postMessage(
            { type: "search-result", id: msg.id, data },
            "*"
          );
          break;
        }

        // ----- Ctrl+S 保存 -----
        case "glyph-submit": {
          onGlyphSubmit({
            name: msg.name || "",
            kageData: msg.data || "",
            related: msg.related || "u3013",
          });
          break;
        }

        // ----- Enter 改名通知 (暂不做实时处理) -----
        case "name-change":
          break;
      }
    };

    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [onGlyphSubmit]);

  // ============================================================
  // iframe 加载完成后发送 set-name (如果有)
  // ============================================================

  const injectFontCss = useCallback(() => {
    try {
      const doc = iframeRef.current?.contentDocument;
      if (doc) {
        const style = doc.createElement("style");
        style.textContent = `
          body, button, input, select, textarea {
            font-size: 10px !important;
          }
          .cm-editor, .cm-content, .CodeMirror {
            font-size: 9px !important;
          }
        `;
        doc.head.appendChild(style);
      }
    } catch (_) { /* 跨域则忽略 */ }
  }, []);

  const handleLoad = useCallback(() => {
    setLoaded(true);
    injectFontCss();
    if (initialName && iframeRef.current?.contentWindow) {
      // 延迟发送: iframe onLoad 时 React 可能还没挂载, message listener 未注册
      setTimeout(() => {
        iframeRef.current?.contentWindow?.postMessage(
          { type: "set-name", name: initialName },
          "*"
        );
      }, 300);
    }
  }, [initialName, injectFontCss]);

  // ============================================================
  // 外部可以在 initialData 变化时重新加载 iframe
  // ============================================================

  const src = buildUrl();

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {!loaded && (
        <div style={{
          padding: "12px", fontSize: "13px", color: "var(--text-muted)",
          textAlign: "center",
        }}>
          KAGE 编辑器加载中...
        </div>
      )}
      <iframe
        ref={iframeRef}
        src={src}
        onLoad={handleLoad}
        style={{
          flex: 1,
          border: "none",
          display: loaded ? "block" : "none",
          minHeight: 0,
        }}
        title="KAGE Glyph Editor"
      />
    </div>
  );
}
