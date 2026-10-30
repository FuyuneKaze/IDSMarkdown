# -*- coding: utf-8 -*-
"""把 loadCoreGlyphs 改成「分块 Range 下载 + 重试 + 解压」

根因: 3.8MB 单文件在跨境/移动网络上经常中途卡死或连接重置, 浏览器报
      TypeError: Failed to fetch, 整个字形库加载失败。
做法: 直接取 .gz (nginx 以 application/octet-stream 发出, 不带 Content-Encoding,
      所以按字节做 Range 是安全的), 256KB 一块、4 路并行、每块重试 3 次,
      拼起来后用 DecompressionStream 解压。避免"Range + gzip 自动解压"导致的半截流。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KE = os.path.join(ROOT, "src", "editor", "kageEngine.ts")

s = io.open(KE, encoding="utf-8").read()

OLD = '''      async loadCoreGlyphs(): Promise<void> {
        try {
          const resp = await fetch(glyphBase() + "core_glyphs.json");
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          const json = await resp.json();
          const glyphs = json.glyphs as Record<string, string>;'''

NEW = '''      /**
       * 分块 + 重试地下载字形库
       *
       * 为什么不是一次 fetch: 3.8MB(压缩后)在跨境/移动网络上经常**中途卡死或连接重置**,
       * 浏览器报 `TypeError: Failed to fetch`, 整个字形库就加载失败 (实测 utai.space
       * 到大陆只有 12–250 KB/s, 单条长连接撑不住)。
       *
       * 为什么取 .gz 而不是 .json: 服务器对 `.json` 会带 `Content-Encoding: gzip`,
       * 此时按字节 Range 拿到的是**压缩流的片段**, 浏览器无法逐段解压 (拼接后也解不开);
       * 而 `.gz` 文件是以 `application/octet-stream` 原样发出的, Range 取到的就是
       * 原始 gzip 字节, 拼接后用 DecompressionStream 一次性解压即可。
       *
       * 失败策略: 每块独立重试 3 次, 单块失败不会拖死全局; 全部失败才抛, 由调用方
       * 退回"逐字走 GlyphWiki"的模式。
       */
      private async fetchBundle<T>(jsonUrl: string, gzUrl: string): Promise<T> {
        const CHUNK = 256 * 1024;
        const PARALLEL = 4;
        const RETRY = 3;

        const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

        const hasDecompress = typeof (globalThis as any).DecompressionStream === "function";

        // ① 优先: .gz 分块
        if (hasDecompress) {
          try {
            const head = await fetch(gzUrl, { method: "HEAD" });
            if (head.ok) {
              const len = Number(head.headers.get("content-length") || 0);
              if (len > 0) {
                const n = Math.ceil(len / CHUNK);
                const parts = new Array<Uint8Array | null>(n);
                let next = 0;
                const worker = async () => {
                  while (true) {
                    const i = next++;
                    if (i >= n) return;
                    const start = i * CHUNK;
                    const end = Math.min(start + CHUNK, len) - 1;
                    for (let attempt = 1; attempt <= RETRY; attempt++) {
                      try {
                        const r = await fetch(gzUrl, { headers: { Range: `bytes=${start}-${end}` } });
                        if (!r.ok) throw new Error(`HTTP ${r.status}`);
                        parts[i] = new Uint8Array(await r.arrayBuffer());
                        break;
                      } catch (e) {
                        if (attempt === RETRY) throw e;
                        await sleep(300 * attempt);
                      }
                    }
                  }
                };
                await Promise.all(Array.from({ length: Math.min(PARALLEL, n) }, worker));
                const total = parts.reduce((a, p) => a + (p ? p.length : 0), 0);
                const buf = new Uint8Array(total);
                let off = 0;
                for (const p of parts) {
                  if (!p) throw new Error("分块缺失");
                  buf.set(p, off);
                  off += p.length;
                }
                if (total !== len) throw new Error(`分块拼接不完整 ${total}/${len}`);
                console.log(`[KageEngine] bundle: ${n} 块 / ${(len / 1048576).toFixed(2)} MB (gzip)`);
                const ds = new (globalThis as any).DecompressionStream("gzip");
                const text = await new Response(new Blob([buf]).stream().pipeThrough(ds)).text();
                return JSON.parse(text) as T;
              }
            }
          } catch (e) {
            console.warn("[KageEngine] 分块下载失败, 退回整包下载:", e);
          }
        }

        // ② 兜底: 一次性整包
        const resp = await fetch(jsonUrl);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return (await resp.json()) as T;
      }

      async loadCoreGlyphs(): Promise<void> {
        try {
          const json = await this.fetchBundle<{ glyphs?: Record<string, string> }>(
            glyphBase() + "core_glyphs.json",
            glyphBase() + "core_glyphs.json.gz",
          );
          const glyphs = json.glyphs as Record<string, string>;'''

if OLD not in s:
    print("!! 未匹配到 loadCoreGlyphs 开头, 放弃")
else:
    s = s.replace(OLD, NEW, 1)
    io.open(KE, "w", encoding="utf-8", newline="").write(s)
    print("已改写 loadCoreGlyphs + 新增 fetchBundle()")
