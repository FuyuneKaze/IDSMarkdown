# -*- coding: utf-8 -*-
"""一次性补丁: GitHub Pages 子路径部署支持

1) 新增 src/editor/assetUrl.ts —— 把以 "/" 开头的静态资源路径补上部署 base
2) 七个硬编码 fetch("/...") 站点改用 assetUrl()
3) vite.config.ts 加条件 base (本地仍是 "/", CI 里 GHPAGES=1 才用 /IDSMarkdown/)
4) 新增 .github/workflows/deploy.yml
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # web/
ED = os.path.join(ROOT, "src", "editor")

ASSET = '''/**
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
  return base.replace(/\\/$/, "") + path;
}
'''

io.open(os.path.join(ED, "assetUrl.ts"), "w", encoding="utf-8", newline="\n").write(ASSET)
print("写出 src/editor/assetUrl.ts")

IMPORT = 'import { assetUrl } from "./assetUrl";\n'


def patch(fname, pairs):
    p = os.path.join(ED, fname)
    s = io.open(p, encoding="utf-8").read()
    n = 0
    for old, new in pairs:
        if old not in s:
            print(f"  !! {fname}: 未找到 {old[:50]!r}")
            continue
        s = s.replace(old, new)
        n += 1
    if "assetUrl" in s and IMPORT not in s:
        s = IMPORT + s
    io.open(p, "w", encoding="utf-8", newline="").write(s)
    print(f"  {fname}: 替换 {n} 处" + (" + 加 import" if IMPORT in s else ""))


patch("kageEngine.ts", [
    ('fetch("/core_glyphs.json")', 'fetch(assetUrl("/core_glyphs.json"))'),
])
patch("idsCompose.ts", [
    ("fetch(`/${fn}`)", "fetch(assetUrl(`/${fn}`))"),
])
patch("ipaDatabase.ts", [
    ("const resp = await fetch(path);", "const resp = await fetch(assetUrl(path));"),
])
patch("candidateEngine.ts", [
    ("const resp = await fetch(path);", "const resp = await fetch(assetUrl(path));"),
])

# ---- vite.config.ts: 条件 base ----
vp = os.path.join(ROOT, "vite.config.ts")
v = io.open(vp, encoding="utf-8").read()
if "GHPAGES" not in v:
    v = v.replace(
        "export default defineConfig({\n  plugins: [react()],\n})",
        "// 部署到 GitHub Pages 的**项目站**时用子路径 (如 /IDSMarkdown/)，本地开发仍是 /\n"
        "export default defineConfig({\n"
        "  base: process.env.GHPAGES ? \"/IDSMarkdown/\" : \"/\",\n"
        "  plugins: [react()],\n"
        "})",
    )
    io.open(vp, "w", encoding="utf-8", newline="").write(v)
    print("vite.config.ts: 已加条件 base")
else:
    print("vite.config.ts: 已有 GHPAGES, 跳过")

# ---- GitHub Actions 工作流 ----
wf_dir = os.path.join(os.path.dirname(ROOT), ".github", "workflows")
os.makedirs(wf_dir, exist_ok=True)
WF = """name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: web/package-lock.json
      - name: Install
        working-directory: web
        run: npm ci || npm install
      - name: Build (子路径 /IDSMarkdown/)
        working-directory: web
        env:
          GHPAGES: "1"
        run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web/dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
"""
io.open(os.path.join(wf_dir, "deploy.yml"), "w", encoding="utf-8", newline="\n").write(WF)
print("写出 .github/workflows/deploy.yml")
