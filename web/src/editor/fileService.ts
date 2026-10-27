/**
 * fileService — .idsmd 文件序列化/反序列化/IO
 *
 * 格式兼容 C++ 版:
 *   <glyph>
 *   "NAME": "KAGE_STROKE_DATA"
 *   </glyph>
 *   <text>
 *   HTML内容
 *   </text>
 */

import { glyphFontManager } from "./glyphFontManager";
import { storeHandle, getHandle, isFsaAvailable } from "./fileHandleStore";

export interface OpenResult {
  name: string;
  content: string;
  handleId?: number;
}

export interface SaveResult {
  handleId?: number;
  newName?: string;
}

export interface IdsmdGlyphEntry {
  name: string;
  kageData: string;
}

export interface IdsmdDocument {
  glyphs: IdsmdGlyphEntry[];
  textHtml: string;
}

// ============================================================
// 序列化
// ============================================================

function escapeJsonString(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function unescapeJsonString(s: string): string {
  return s.replace(/\\(.)/g, "$1");
}

/** HTML 实体解码 (amp 最后, 防止 &amp;quot; 二次解码) */
function decodeHtmlEntities(s: string): string {
  return s
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_m, code) => String.fromCodePoint(parseInt(code, 10)))
    .replace(/&amp;/g, "&");
}

/** 属性值转义 (写入 data-* 属性) */
function escapeAttr(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * PUA 合成字 → 数字实体: 行 63 的裸 PUA 全局替换会改写语法内容,
 * 转成 &#NNN; 后不被匹配, 由行 102 的实体解码还原
 */
function escapePua(s: string): string {
  return [...s]
    .map((ch) => {
      const cp = ch.codePointAt(0)!;
      return cp >= 0xe000 && cp <= 0xf8ff ? `&#${cp};` : ch;
    })
    .join("");
}

/** HTML → Markdown (兼容 C++ 版 .idsmd 的 <text> 块格式) */
function htmlToMarkdown(html: string): string {
  let md = html;
  console.log("[fileService] htmlToMarkdown input:", JSON.stringify(md.slice(0, 400)));

  // idsGlyph PUA span → IDS 表达式
  md = md.replace(/<span[^>]*\bclass="ids-glyph"[^>]*\bdata-ids-source="([^"]*)"[^>]*>[^<]*<\/span>/gi, "$1");
  // kageGlyph span → @KAGE@
  md = md.replace(/<span[^>]*\bdata-type="kage-glyph"[^>]*\bdata-kage-data="([^"]*)"[^>]*>[^<]*<\/span>/gi,
    (_m, data) => `@${data.replace(/&quot;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">")}@`);

  console.log("[fileService] after glyph spans:", JSON.stringify(md.slice(0, 400)));

  // rubyBlock span → 〔base‖rt〕 (内容保持实体编码, 由后方全局清理在标签剥离后解码; PUA 转实体防下方裸 PUA 替换改写)
  // 必须精确匹配内层子 span 结构, 非贪婪 [\s\S]*? 会停在第一个 </span> 导致外层残留重复文字
  // 子结构分支外提供 [^<]* 分支以匹配空块占位文本 ([注音])
  md = md.replace(
    /<span[^>]*\bdata-type="ruby-block"[^>]*\bdata-base="([^"]*)"[^>]*\bdata-rt="([^"]*)"[^>]*>(?:\s*<span class="rb-rt"[^>]*>[^<]*<\/span>\s*<span class="rb-base"[^>]*>[^<]*<\/span>\s*|[^<]*)?<\/span>/gi,
    (_m, base, rt) => `〔${escapePua(base)}‖${escapePua(rt)}〕`);
  // doubleLine span → ⟦text⟧
  md = md.replace(
    /<span[^>]*\bdata-type="double-line"[^>]*\bdata-text="([^"]*)"[^>]*>(?:\s*<span class="dl-line1"[^>]*>[^<]*<\/span>\s*<span class="dl-line2"[^>]*>[^<]*<\/span>\s*|[^<]*)?<\/span>/gi,
    (_m, text) => `⟦${escapePua(text)}⟧`);

  console.log("[fileService] after annotation spans:", JSON.stringify(md.slice(0, 400)));

  // 裸 PUA 码点 → IDS 表达式 (处理 code 标签内无 ids-glyph span 的情况)
  md = md.replace(/[-]/g, (ch) => {
    const cp = ch.codePointAt(0);
    if (cp !== undefined) {
      const ids = glyphFontManager.getIdsSource(cp);
      if (ids) return ids;
    }
    return ch;
  });

  // 行内格式 (源码模式下不再产生, 保留兼容旧文件)
  // md = md.replace(/<\/?strong>/gi, "**");
  // md = md.replace(/<\/?em>/gi, "*");
  // md = md.replace(/<code>([^<]*)<\/code>/gi, "`$1`");

  // 标题 (源码模式下不再产生, 保留兼容旧文件)
  // md = md.replace(/<h1>([^<]*)<\/h1>/gi, "# $1\n\n");
  // md = md.replace(/<h2>([^<]*)<\/h2>/gi, "## $1\n\n");
  // md = md.replace(/<h3>([^<]*)<\/h3>/gi, "### $1\n\n");
  // md = md.replace(/<h4>([^<]*)<\/h4>/gi, "#### $1\n\n");

  // 段落: </p> 后双换行 (Markdown 段落分隔), 移除 <p> 标签
  md = md.replace(/<\/p>/gi, "\n\n");
  md = md.replace(/<p[^>]*>/gi, "");

  console.log("[fileService] after p/br:", JSON.stringify(md.slice(0, 400)));

  // 换行
  md = md.replace(/<br\s*\/?>/gi, "\n");

  // 移除其余 HTML 标签 (保留内容)
  md = md.replace(/<[^>]+>/g, "");

  console.log("[fileService] after tag removal:", JSON.stringify(md.slice(0, 400)));

  // 清理 HTML 实体
  md = md.replace(/&amp;/g, "&");
  md = md.replace(/&lt;/g, "<");
  md = md.replace(/&gt;/g, ">");
  md = md.replace(/&quot;/g, '"');
  md = md.replace(/&#(\d+);/g, (_m, code) => String.fromCodePoint(parseInt(code, 10)));

  // 连续空行压缩
  md = md.replace(/\n{3,}/g, "\n\n");

  // 清除首尾空行 (保留内容中的前导空格/缩进)
  md = md.replace(/^\n+/, "").replace(/\n+$/, "\n");

  console.log("[fileService] final markdown:", JSON.stringify(md.slice(0, 400)));
  return md;
}

export function serializeIdsmd(glyphs: IdsmdGlyphEntry[], textHtml: string): string {
  const glyphLines = glyphs
    .filter((g) => g.kageData)
    .map((g) => `"${escapeJsonString(g.name)}": "${escapeJsonString(g.kageData)}"`);
  const textMd = htmlToMarkdown(textHtml);
  return `<glyph>\n${glyphLines.join("\n")}\n</glyph>\n<text>\n${textMd}\n</text>\n`;
}

// ============================================================
// 反序列化
// ============================================================

/** 将文本中的 @KAGE_DATA@ 内联语法转为 HTML span (供 TipTap parseHTML 还原为 kageGlyph 节点) */
function convertInlineKage(text: string): string {
  return text.replace(/@([^@]+)@/g, (_match, data) => {
    if (!data.trim()) return _match;
    const escaped = data.replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/&/g, "&amp;");
    return `<span data-type="kage-glyph" data-kage-data="${escaped}">[KAGE]</span>`;
  });
}

/**
 * 将行内语法转为 HTML span (供 TipTap parseHTML 还原为 rubyBlock/doubleLine 节点):
 *   〔base‖rt〕 → ruby-block,  ⟦text⟧ → double-line
 */
export function convertInlineAnnotations(text: string): string {
  return text
    .replace(/〔([^〕]*)〕/g, (_match, inner) => {
      const sep = (inner as string).indexOf("‖");
      const base = sep >= 0 ? inner.slice(0, sep) : inner;
      const rt = sep >= 0 ? inner.slice(sep + 1) : "";
      return `<span data-type="ruby-block" data-base="${escapeAttr(decodeHtmlEntities(base))}" data-rt="${escapeAttr(decodeHtmlEntities(rt))}"></span>`;
    })
    .replace(/⟦([^⟧]*)⟧/g, (_match, t) =>
      `<span data-type="double-line" data-text="${escapeAttr(decodeHtmlEntities(t))}"></span>`);
}

/** Markdown → HTML 转换 (仅段落拆分, 格式标记保持为源文本) */
export function markdownToHtml(md: string): string {
  let html = md;
  // 代码块
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="language-$1">$2</code></pre>');

  // 按双换行分段; 段内单换行转 <br>
  const blocks = html.split(/\n\n+/);
  html = blocks.map((b) => {
    const trimmed = b.trim();
    if (!trimmed) return '';
    if (/^<pre/.test(trimmed)) return trimmed;
    // 已有 <p> 包裹则跳过
    if (/^<p[> ]/.test(trimmed) && /<\/p>$/.test(trimmed)) return trimmed;
    const withBreaks = trimmed.replace(/\n/g, '<br>');
    return `<p>${withBreaks}</p>`;
  }).join('\n');

  return html;
}

export function parseIdsmd(content: string): IdsmdDocument {
  const glyphs: IdsmdGlyphEntry[] = [];
  let textHtml = "";

  // 提取 <glyph> 块
  const glyphMatch = content.match(/<glyph>([\s\S]*?)<\/glyph>/);
  if (glyphMatch) {
    const glyphBlock = glyphMatch[1];
    const lineRe = /^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*$/gm;
    let m;
    while ((m = lineRe.exec(glyphBlock)) !== null) {
      const name = unescapeJsonString(m[1]);
      const kageData = unescapeJsonString(m[2]);
      if (name && kageData) {
        glyphs.push({ name, kageData });
      }
    }
  }

  // 提取 <text> 块
  const textMatch = content.match(/<text>([\s\S]*?)<\/text>/);
  if (textMatch) {
    const rawText = textMatch[1].trim();
    textHtml = convertInlineAnnotations(convertInlineKage(markdownToHtml(rawText)));
  } else {
    // 无标签: 整段内容当作 HTML
    textHtml = convertInlineAnnotations(convertInlineKage(markdownToHtml(content.trim())));
  }

  return { glyphs, textHtml };
}

// ============================================================
// 浏览器文件 IO
// ============================================================

export function downloadFile(content: string, filename: string): void {
  const name = filename.endsWith(".idsmd") ? filename : `${filename}.idsmd`;
  const blob = new Blob([content], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

export function openFileDialog(): Promise<{ name: string; content: string } | null> {
  return new Promise((resolve) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".idsmd,.txt,.md,.html";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) {
        resolve(null);
        return;
      }
      try {
        const text = await file.text();
        resolve({ name: file.name, content: text });
      } catch {
        resolve(null);
      }
    };
    input.click();
  });
}

// ============================================================
// File System Access API (Chrome/Edge) — 原地读写
// ============================================================

export async function openFileWithPicker(): Promise<OpenResult | null> {
  if (isFsaAvailable()) {
    try {
      const [handle] = await (window as any).showOpenFilePicker({
        types: [{
          description: "IDS Markdown",
          accept: { "application/octet-stream": [".idsmd", ".txt", ".md", ".html"] },
        }],
        multiple: false,
      });
      const file = await handle.getFile();
      const content = await file.text();
      const handleId = await storeHandle(file.name, handle);
      return { name: file.name, content, handleId };
    } catch (e) {
      // 用户取消
      if ((e as DOMException).name === "AbortError") return null;
      console.warn("[fileService] showOpenFilePicker failed, falling back:", e);
    }
  }

  // 降级: 传统 <input type="file">
  const result = await openFileDialog();
  if (!result) return null;
  // 降级模式: 尝试存内容到 localStorage 以便最近文件可恢复
  try {
    localStorage.setItem(`idsmd_backup_${result.name}`, result.content);
  } catch { /* ignore */ }
  return { name: result.name, content: result.content };
}

export async function saveFileWithHandle(
  content: string,
  fileName: string,
  handleId?: number,
): Promise<SaveResult> {
  if (isFsaAvailable()) {
    let handle: FileSystemFileHandle | null = null;

    if (handleId != null) {
      handle = await getHandle(handleId);
    }

    if (!handle) {
      // 首次保存: 弹出保存对话框
      try {
        handle = await (window as any).showSaveFilePicker({
          suggestedName: fileName.endsWith(".idsmd") ? fileName : `${fileName}.idsmd`,
          types: [{
            description: "IDS Markdown",
            accept: { "application/octet-stream": [".idsmd"] },
          }],
        });
      } catch (e) {
        if ((e as DOMException).name === "AbortError") return {};
        console.warn("[fileService] showSaveFilePicker failed, falling back:", e);
        downloadFile(content, fileName);
        return {};
      }
    }

    // TS 收窄: 上方 picker 未赋值成功时兜底
    if (!handle) {
      downloadFile(content, fileName);
      return {};
    }

    try {
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();

      const newName = handle.name;
      const newHandleId = await storeHandle(newName, handle);
      return { handleId: newHandleId, newName };
    } catch (e) {
      console.warn("[fileService] write failed, falling back to download:", e);
      downloadFile(content, fileName);
      return {};
    }
  }

  // 降级: 强制下载
  downloadFile(content, fileName);
  // 降级模式: 存备份
  try {
    localStorage.setItem(`idsmd_backup_${fileName}`, content);
  } catch { /* ignore */ }
  return {};
}

export async function saveFileAs(
  content: string,
  fileName: string,
): Promise<SaveResult> {
  if (isFsaAvailable()) {
    try {
      const handle = await (window as any).showSaveFilePicker({
        suggestedName: fileName.endsWith(".idsmd") ? fileName : `${fileName}.idsmd`,
        types: [{
          description: "IDS Markdown",
          accept: { "application/octet-stream": [".idsmd"] },
        }],
      });
      const writable = await handle.createWritable();
      await writable.write(content);
      await writable.close();
      const newName = handle.name;
      const handleId = await storeHandle(newName, handle);
      return { handleId, newName };
    } catch (e) {
      if ((e as DOMException).name === "AbortError") return {};
      console.warn("[fileService] saveFileAs failed, falling back:", e);
    }
  }

  // 降级: 触发下载
  downloadFile(content, fileName);
  return {};
}

export async function reopenFile(handleId: number): Promise<OpenResult | null> {
  if (!isFsaAvailable()) {
    // 降级: 尝试从 localStorage 备份恢复
    return null;
  }

  const handle = await getHandle(handleId);
  if (!handle) return null;

  // 检查/请求权限 (lib.dom 类型缺失, 运行时存在)
  const opts: any = { mode: "read" };
  const fh = handle as any;
  if ((await fh.queryPermission(opts)) === "granted" ||
      (await fh.requestPermission(opts)) === "granted") {
    try {
      const file = await handle.getFile();
      const content = await file.text();
      return { name: file.name, content, handleId };
    } catch (e) {
      console.warn("[fileService] reopenFile read failed:", e);
      return null;
    }
  }

  return null;
}
