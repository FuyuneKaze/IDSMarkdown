import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// 部署到 GitHub Pages 的**项目站**时用子路径 (如 /IDSMarkdown/)，本地开发仍是 /
export default defineConfig({
  base: process.env.GHPAGES ? "/IDSMarkdown/" : "/",
  plugins: [react()],
})
