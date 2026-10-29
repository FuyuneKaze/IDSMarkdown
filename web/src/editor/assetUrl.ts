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
