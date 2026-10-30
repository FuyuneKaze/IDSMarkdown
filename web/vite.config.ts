import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// 部署到 GitHub Pages 的**项目站**时用子路径 (如 /IDSMarkdown/)，本地开发仍是 /
export default defineConfig({
  // 部署路径:
  //   GitHub Pages 项目站 → GHPAGES=1  → base = /IDSMarkdown/
  //   自己的域名子目录    → VITE_BASE=/ids/ → base = /ids/
  //   域名根 / 本地开发   → 都不设       → base = /
  base: process.env.GHPAGES
    ? "/IDSMarkdown/"
    : (process.env.VITE_BASE || "/"),
  plugins: [react()],
})
