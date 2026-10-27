import { useState, useRef, useCallback, useEffect } from "react";

export interface RecentFile {
  name: string;
  handleId?: number;
  timestamp: number;
}

interface FileSidebarProps {
  currentFileName: string;
  isDirty: boolean;
  onNew: () => void;
  onOpen: () => void;
  onSave: () => void;
  onSaveAs: () => void;
  onClose: () => void;
  onOpenRecent: (entry: RecentFile) => void;
  onRename: (newName: string) => void;
  recentFiles: RecentFile[];
}

const RECENT_KEY = "idsmd_recent_files";
const MAX_RECENT = 10;

export function loadRecentFiles(): RecentFile[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

export function saveRecentFile(entry: RecentFile): void {
  const files = loadRecentFiles().filter((f) => f.name !== entry.name || f.handleId !== entry.handleId);
  files.unshift({ ...entry, timestamp: Date.now() });
  localStorage.setItem(RECENT_KEY, JSON.stringify(files.slice(0, MAX_RECENT)));
}

export default function FileSidebar({
  currentFileName,
  isDirty,
  onNew,
  onOpen,
  onSave,
  onSaveAs,
  onClose,
  onOpenRecent,
  onRename,
  recentFiles,
}: FileSidebarProps) {
  const [width, setWidth] = useState(260);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const dragging = useRef(false);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    const startX = e.clientX;
    const startWidth = width;
    const onMouseMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const delta = ev.clientX - startX;
      const next = Math.max(200, Math.min(450, startWidth + delta));
      setWidth(next);
    };
    const onMouseUp = () => {
      dragging.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }, [width]);

  useEffect(() => {
    const el = sidebarRef.current;
    if (!el) return;
    const onDragStart = (e: Event) => e.preventDefault();
    el.addEventListener("selectstart", onDragStart);
    return () => el.removeEventListener("selectstart", onDragStart);
  }, []);

  // 聚焦编辑 input
  useEffect(() => {
    if (editingName && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [editingName]);

  const startRename = () => {
    setNameDraft(currentFileName || "");
    setEditingName(true);
  };

  const confirmRename = () => {
    setEditingName(false);
    const trimmed = nameDraft.trim();
    if (trimmed && trimmed !== currentFileName) {
      onRename(trimmed);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const displayName = currentFileName || "（未命名）";
  const hasFsa = typeof window !== "undefined" && "showOpenFilePicker" in window;

  return (
    <div className="file-sidebar" ref={sidebarRef} style={{ width }}>
      <div className="file-sidebar-header">
        <span>文件</span>
        <button className="file-sidebar-close" onClick={onClose} title="关闭面板">
          ×
        </button>
      </div>

      <div className="file-sidebar-actions">
        <button className="file-sidebar-btn" onClick={onNew} title="新建 (Ctrl+N)">
          新建
        </button>
        <button className="file-sidebar-btn" onClick={onOpen} title="打开 (Ctrl+O)">
          打开
        </button>
        <button
          className={`file-sidebar-btn${isDirty ? " file-sidebar-btn-dirty" : ""}`}
          onClick={onSave}
          title="保存 (Ctrl+S)"
        >
          保存{isDirty ? " *" : ""}
        </button>
        <button className="file-sidebar-btn" onClick={onSaveAs} title="另存为...">
          另存为
        </button>
      </div>

      <div className="file-sidebar-section">
        <div className="file-sidebar-section-title">当前文件</div>
        {editingName ? (
          <input
            ref={nameInputRef}
            className="file-sidebar-name-input"
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            onBlur={confirmRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirmRename();
              if (e.key === "Escape") setEditingName(false);
            }}
          />
        ) : (
          <div
            className="file-sidebar-current file-sidebar-current-editable"
            onClick={startRename}
            title="点击编辑文件名"
          >
            {displayName}
            {isDirty && <span className="file-sidebar-dirty-dot" title="有未保存的更改"> ●</span>}
          </div>
        )}
      </div>

      {recentFiles.length > 0 && (
        <div className="file-sidebar-section">
          <div className="file-sidebar-section-title">
            最近文件
            {!hasFsa && <span style={{ fontSize: "10px", color: "var(--text-muted)" }}> (当前浏览器不支持直接打开)</span>}
          </div>
          <ul className="file-sidebar-list">
            {recentFiles.map((f) => (
              <li
                key={`${f.name}-${f.handleId ?? "noid"}-${f.timestamp}`}
                className={`file-sidebar-item${f.handleId != null ? " file-sidebar-item-clickable" : ""}`}
                onClick={() => f.handleId != null ? onOpenRecent(f) : null}
                title={f.handleId != null ? `打开 ${f.name}` : `${f.name}（需重新打开）`}
              >
                <span className="file-sidebar-item-name">{f.name}</span>
                <span className="file-sidebar-item-time">{formatTime(f.timestamp)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="file-resize-handle" onMouseDown={onMouseDown} />
    </div>
  );
}
