/**
 * 静态资源 URL
 *
 * GitHub Pages 的**项目站**部署在子路径下（如 /IDSMarkdown/），此时以 "/" 开头的
 * 绝对路径会指到域名根、404。Vite 的 import.meta.env.BASE_URL 在构建时被替换成
 * 正确前缀（本地开发是 "/"）。
 *
 * 用法: fetch(assetUrl("/data/jap_cjk.json"))、fetch(assetUrl(`/${fn}`))
 */
export function assetUrl(path: string): string {
  if (!path.startsWith("/")) return path;
  const base = import.meta.env.BASE_URL || "/";
  return base.replace(/\/$/, "") + path;
}

/**
 * 字形数据根 URL
 *
 * 构建时可用环境变量 VITE_GLYPH_BASE 指向自建服务器，例如:
 *   VITE_GLYPH_BASE=https://data.example.com/glyphs/
 * 未设置则使用同源站点（把 core_glyphs.json 放在 public/ 就自动生效）。
 *
 * 服务器只需静态托管 + `Access-Control-Allow-Origin: *`，不必写后端。
 * 建议同时放一份 core_glyphs.json.gz 并开启 nginx 的 gzip_static:
 * 浏览器会自动解压（Content-Encoding: gzip），传输量从 103MB 降到约 15MB。
 */
export function glyphBase(): string {
  const env = (import.meta.env.VITE_GLYPH_BASE as string | undefined) ?? "";
  if (!env) return assetUrl("/");
  return env.endsWith("/") ? env : env + "/";
}
