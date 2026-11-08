import { useEffect, useMemo, useState } from "react";
import { assetUrl } from "../editor/assetUrl";

/** 数据: group(符号表) → [folder] → item；folder 只为兼容旧表, 渲染时摊平 */
export interface SymItem { slogan: string; name: string; insert: string }
interface SymFolder { id: string; title: string; items: SymItem[] }
interface SymGroup { id: string; title: string; folders?: SymFolder[]; items?: SymItem[] }
interface SymTable { groups: SymGroup[] }

interface Section { id: string; title: string; items: SymItem[] }

/** 不区分「元音/辅音」「笔画/偏旁」: 一节的格子全部摊平 */
function toSections(t: SymTable): Section[] {
  return t.groups.map((g) => ({
    id: g.id,
    title: g.title,
    items: g.folders?.length ? g.folders.flatMap((f) => f.items) : (g.items ?? []),
  }));
}

/**
 * 「符号」面板
 *
 * 每个符号表 = 一条与面板同宽的可折叠标题条 (▶/▼ + 标题);
 * 展开后是紧凑格子阵: 上字形框、下名称条; 点一下插入 `item.insert`
 * (插入内容可不等于显示字形, 便于把组合符/变体放进同一格)。
 */
export default function SymbolPanel({ onInsert }: { onInsert: (text: string) => void }) {
  const [table, setTable] = useState<SymTable | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let alive = true;
    // cache: "no-cache" → 每次都做协商请求(GitHub Pages 的 max-age=600 会让旧表滞留 10 分钟)
    fetch(assetUrl("/data/symbols.json"), { cache: "no-cache" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((j: SymTable) => {
        if (!alive) return;
        setTable(j);
        const first = j.groups[0]?.id;
        if (first) setOpen({ [first]: true });
      })
      .catch((e) => { if (alive) setErr(String(e)); });
    return () => { alive = false; };
  }, []);

  const sections = useMemo(() => (table ? toSections(table) : []), [table]);

  if (err) return <p className="form-hint">符号表加载失败：{err}</p>;
  if (!table) return <p className="form-hint">正在加载符号表…</p>;

  return (
    <div className="sym-panel">
      {sections.map((sec) => {
        const expanded = !!open[sec.id];
        return (
          <section key={sec.id} className="sym-section">
            <button
              className={"sym-head" + (expanded ? " open" : "")}
              onClick={() => setOpen((v) => ({ ...v, [sec.id]: !v[sec.id] }))}
            >
              <span className="sym-tri">{expanded ? "▼" : "▶"}</span>
              <span className="sym-title">{sec.title}</span>
            </button>
            {expanded && (
              <div className="sym-body">
                <div className="sym-grid">
                  {sec.items.map((it, i) => (
                    <button
                      key={sec.id + "-" + i}
                      className="sym-cell"
                      title={it.name || it.slogan}
                      onClick={() => onInsert(it.insert)}
                    >
                      <span className="sym-glyph">{it.slogan}</span>
                      <span className="sym-name">{it.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        );
      })}
    </div>
  );
}
