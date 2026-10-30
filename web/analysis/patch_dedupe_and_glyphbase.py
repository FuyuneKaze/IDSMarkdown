# -*- coding: utf-8 -*-
"""1) 精简重复的 IDS 表 (只留 web/public 一份, 程序改指它)
2) 支持把字形数据库放到自建服务器 (VITE_GLYPH_BASE)
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # web/
REPO = os.path.dirname(ROOT)
ED = os.path.join(ROOT, "src", "editor")


def rw(path, fn):
    s = io.open(path, encoding="utf-8").read()
    s2 = fn(s)
    if s2 != s:
        io.open(path, "w", encoding="utf-8", newline="").write(s2)
        print(f"  改: {os.path.relpath(path, REPO)}")
    else:
        print(f"  跳过(无变化): {os.path.relpath(path, REPO)}")


# ---------- assetUrl.ts: 增加 glyphBase ----------
au = os.path.join(ED, "assetUrl.ts")
s = io.open(au, encoding="utf-8").read()
if "glyphBase" not in s:
    s += '''
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
'''
    io.open(au, "w", encoding="utf-8", newline="").write(s)
    print("  改: web/src/editor/assetUrl.ts (+glyphBase)")

# ---------- kageEngine.ts: 用 glyphBase ----------
ke = os.path.join(ED, "kageEngine.ts")


def patch_ke(t):
    t = t.replace('import { assetUrl } from "./assetUrl";',
                  'import { assetUrl, glyphBase } from "./assetUrl";')
    t = t.replace('fetch(assetUrl("/core_glyphs.json"))',
                  'fetch(glyphBase() + "core_glyphs.json")')
    return t


rw(ke, patch_ke)

# ---------- scripts/extract_core_glyphs.py: 读 web/public ----------
ec = os.path.join(REPO, "scripts", "extract_core_glyphs.py")


def patch_ec(t):
    old = 'IDS_DIR = os.path.join(DATA_DIR, "ids")'
    new = ('# IDS 表只有一份, 在 web/public/ (运行时也要从这里取); data/ids/ 仅留 ts.txt\n'
           'IDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),\n'
           '                       "web", "public")\n'
           '_fallback = os.path.join(DATA_DIR, "ids")\n'
           'if not os.path.exists(os.path.join(IDS_DIR, "ids_lv0.txt")):\n'
           '    IDS_DIR = _fallback')
    return t.replace(old, new)


rw(ec, patch_ec)

# ---------- 工作流: 传 VITE_GLYPH_BASE (来自仓库变量 GLYPH_BASE) ----------
wf = os.path.join(REPO, ".github", "workflows", "deploy.yml")


def patch_wf(t):
    if "VITE_GLYPH_BASE" in t:
        return t
    return t.replace('          GHPAGES: "1"',
                     '          GHPAGES: "1"\n'
                     '          # 可选: 仓库 Settings → Variables 里设 GLYPH_BASE 指向自建数据服务器\n'
                     '          VITE_GLYPH_BASE: ${{ vars.GLYPH_BASE }}')


rw(wf, patch_wf)

# ---------- 文档: data/ids → web/public ----------
for doc, pairs in {
    os.path.join(REPO, "README.md"): [
        ("IDS 文本 `data/ids/ids_lv0/1/2.txt`、`ts.txt`", "IDS 文本 `web/public/ids_lv0/1/2.txt`、`data/ids/ts.txt`"),
        ("同目录下的 `ids_lv4.txt` / `TangutIDS.txt`", "`data/ids/` 下的 `ids_lv4.txt` / `TangutIDS.txt`"),
    ],
    os.path.join(REPO, "THIRD-PARTY.md"): [
        ("**已入库** `data/ids/`", "**已入库** `web/public/`（`ts.txt` 在 `data/ids/`）"),
    ],
}.items():
    s = io.open(doc, encoding="utf-8").read()
    for a, b in pairs:
        s = s.replace(a, b)
    io.open(doc, "w", encoding="utf-8", newline="").write(s.rstrip("\n") + "\n")
    print(f"  改: {os.path.relpath(doc, REPO)}")
