# 部署笔记（DEPLOY）

> ⚠️ **本机服务器是宝塔面板（BT Panel）的 Nginx。所有 Nginx 操作一律使用下面两条，禁止 `systemctl ... nginx`**：
>
> ```bash
> /www/server/nginx/sbin/nginx -t        # 语法检查
> /etc/init.d/nginx reload               # 重载（不是 systemctl reload nginx！）
> ```
>
> 系统自带的 `nginx.service` 是**已禁用的另一个实例**，用 systemctl 会报
> `nginx.service is not active, cannot reload`，或操作到错误的实例。

## 1. 宝塔上的常见路径

| 用途 | 路径 |
| --- | --- |
| Nginx 二进制 | `/www/server/nginx/sbin/nginx` |
| 重载脚本 | `/etc/init.d/nginx reload` |
| **站点配置**（不要改 `/etc/nginx/conf.d/`） | `/www/server/panel/vhost/nginx/<域名>.conf` |
| 站点根目录 | `/www/wwwroot/<域名>/` |
| 访问日志 | `/www/wwwlogs/<域名>.log` |

宝塔里改配置的**推荐方式**：面板 → 网站 → 对应站点 → 设置 → **配置文件**（直接编辑上面那个 vhost 文件），保存后面板会自动 reload。手动改完一定要：

```bash
/www/server/nginx/sbin/nginx -t && /etc/init.d/nginx reload
```

## 2. 把字形数据放到服务器（供网页跨域读取）

### 2.1 放文件

```bash
# 服务器上
mkdir -p /www/wwwroot/utai.space/glyphs
# 本地（Windows PowerShell）
cd D:\2026harucpp\web\public
gzip -k -9 -f core_glyphs.json                     # 生成 core_glyphs.json.gz（约 15MB）
scp core_glyphs.json    root@47.79.77.70:/www/wwwroot/utai.space/glyphs/
scp core_glyphs.json.gz root@47.79.77.70:/www/wwwroot/utai.space/glyphs/
```

> `scp` 语法：`scp 本地文件 用户@主机:远端路径`。主机**不能**写 `https://`，目标目录必须先存在。

### 2.2 站点配置里加一段（宝塔 → 网站 → 配置文件）

```nginx
# 数据目录：允许跨域 + 直接发预压缩文件
location /glyphs/ {
    add_header Access-Control-Allow-Origin *;
    add_header Cache-Control "public, max-age=31536000, immutable";
    gzip_static on;          # 有 .gz 就发它，自动带 Content-Encoding: gzip
    default_type application/octet-stream;
    try_files $uri =404;
}
```

改完：

```bash
/www/server/nginx/sbin/nginx -t && /etc/init.d/nginx reload
curl -sI https://utai.space/glyphs/core_glyphs.json | head -5
# 期望: HTTP/1.1 200 + Content-Encoding: gzip + Access-Control-Allow-Origin: *
```

### 2.3 让 GitHub Pages 上的站点用这份数据

仓库 → Settings → Secrets and variables → Actions → **Variables** 标签 → New repository variable：

```
Name : GLYPH_BASE
Value: https://utai.space/glyphs/
```

然后 **Actions → Deploy to GitHub Pages → Run workflow** 重新构建（工作流里已经接了
`VITE_GLYPH_BASE: ${{ vars.GLYPH_BASE }}`）。

> 如果网页和数据显示在**同一个域名**下（都放 `utai.space`），就**不需要** CORS 头，也不需要
> `GLYPH_BASE`——同源即可。

## 3. 把整个网页也放到服务器（替代 GitHub Pages）

```bash
# 本地构建：独立域名根部署，**不要**设 GHPAGES（那是给 /IDSMarkdown/ 子路径的）
cd D:\2026harucpp\web
npm run build
scp -r dist/* root@47.79.77.70:/www/wwwroot/utai.space/ids/

# 服务器上（宝塔 → 网站 → 配置文件）加 SPA 兜底
location /ids/ {
    try_files $uri $uri/ /ids/index.html;
}
```

## 4. GitHub Pages（当前线上）

- 站点：<https://fuyunekaze.github.io/IDSMarkdown/>
- 工作流：`.github/workflows/deploy.yml`（push 到 `main` 自动构建发布）
- 子路径部署靠 `base: process.env.GHPAGES ? "/IDSMarkdown/" : "/"`，代码里所有
  `fetch("/...")` 必须走 `assetUrl()`，否则会 404。
- **构建时不会带** `core_glyphs.json`（103MB）和字体（未入库）→ 线上靠
  GlyphWiki API 逐字取；`kage-bundle.js`、`ids_lv0/1/2.txt` 必须入库（已入库）。

## 5. 排错清单

| 现象 | 检查 |
| --- | --- |
| `nginx.service is not active` | 用了 systemctl，改用 `/etc/init.d/nginx reload` |
| `/glyphs/` 404 | `ls -lh /www/wwwroot/utai.space/glyphs/`；`/www/server/nginx/sbin/nginx -T \| grep -A8 "location /glyphs"` |
| 网页资源 404（子路径） | 是否漏了 `assetUrl()`；构建时有没有设 `GHPAGES=1` |
| 字缺笔画 | 线上没带完整 bundle；子件（`-j` 等）不会递归取 → 需 `GLYPH_BASE` |
| 字一直"等待数据" | Console 看 `[KageEngine] __recomposeIds` 与 `[idsCompose] database not loaded` |
