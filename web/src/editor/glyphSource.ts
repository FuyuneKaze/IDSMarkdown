/**
 * glyphSource.ts —— 字形数据的来源抽象（bundled → 缓存 → GlyphWiki API）
 *
 * 为什么需要: `core_glyphs.json` 有 100+ MB, 不可能进仓库 (GitHub 单文件上限 100 MiB)。
 * 所以数据必须**运行时获取**:
 *
 *   ① 内置 bundle (可选): `core_glyphs.json` 里已有的就先命中, 零延迟
 *   ② 本地缓存: 内存 Map (+ 可选 IndexedDB), 同一个字不重复请求
 *   ③ GlyphWiki API: `https://glyphwiki.org/api/glyph?name=u4e00`
 *      实测响应头带 `Access-Control-Allow-Origin: *`, 浏览器可直接跨域取
 *      → 纯静态部署可行, 不需要后端代理
 *
 * 取回来的 `data` 字段就是 kage 字形串 (形如 `99:0:0:0:0:200:200:u4e00-j`),
 * 可以直接塞进 KageEngine 的 glyphData (并通过 loadGlyph 注册进 kage-bundle)。
 *
 * 设计要点:
 *   · 渲染是同步的, 所以**取数据必须发生在渲染之前** —— 调用方先 await
 *     `ensure(names)` 把缺的字形补齐, 再同步渲染。不要在渲染路径里等网络。
 *   · 失败也要记住 (负缓存), 否则每次都重试会拖死一个字缺数据的字。
 *   · 并发上限默认 4: GlyphWiki 是公开服务, 别把它打爆。
 */

/** GlyphWiki API 的形态 (只取我们用得到的字段) */
export interface GlyphApiReply {
  name: string;
  data: string;
  version?: number;
  related?: string;
}

export const GLYPHWIKI_API = "https://glyphwiki.org/api/glyph";

/** 字形名 → API URL (名字里的 `@版本` 一并保留, API 支持) */
export function glyphWikiUrl(name: string, base = GLYPHWIKI_API): string {
  return `${base}?name=${encodeURIComponent(name)}`;
}

export interface FetchGlyphOptions {
  base?: string;
  /** 单次请求超时 (ms), 默认 8s */
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

/** 取一个字形; 失败/不存在返回 null (不抛) */
export async function fetchGlyphWikiGlyph(
  name: string,
  opts: FetchGlyphOptions = {},
): Promise<GlyphApiReply | null> {
  const f = opts.fetchImpl ?? fetch;
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), opts.timeoutMs ?? 8000);
  try {
    const resp = await f(glyphWikiUrl(name, opts.base), { signal: ctl.signal });
    if (!resp.ok) return null;
    const json = (await resp.json()) as Partial<GlyphApiReply>;
    if (!json || typeof json.data !== "string" || json.data.length === 0) return null;
    return { name: json.name ?? name, data: json.data, version: json.version, related: json.related };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** 可选的外部缓存 (例如用 dexie 存 IndexedDB); 不给就只用内存 */
export interface GlyphCache {
  get(name: string): Promise<string | undefined>;
  set(name: string, data: string): Promise<void>;
}

export interface EnsureResult {
  fetched: number;
  failed: string[];
}

export interface GlyphSourceOptions extends FetchGlyphOptions {
  cache?: GlyphCache;
  /** 每个取到的字形回调 (通常是 engine.addGlyph) */
  onGlyph?: (name: string, data: string) => void;
  concurrency?: number;
}

/**
 * 字形来源。用法:
 *
 * ```ts
 * const src = new GlyphSource({ onGlyph: (n, d) => engine.addGlyph(n, d) });
 * await src.ensure(["u4eba-06", "u56d7-05"]);   // 先把缺的补齐
 * engine.renderIdsGlyph("⿴囗人");                // 再同步渲染
 * ```
 */
export class GlyphSource {
  private mem = new Map<string, string>();
  private failed = new Set<string>();
  private inflight = new Map<string, Promise<string | null>>();
  private opts: GlyphSourceOptions;

  constructor(opts: GlyphSourceOptions = {}) {
    this.opts = opts;
  }

  /** 同步命中 (内存 / 负缓存不返回) */
  get(name: string): string | undefined {
    return this.mem.get(name);
  }

  has(name: string): boolean {
    return this.mem.has(name);
  }

  /** 记下失败过的名字, 便于 UI 显示"不可合成" */
  get failedNames(): string[] {
    return [...this.failed];
  }

  /** 手动注入 (内置 bundle 用) */
  put(name: string, data: string): void {
    this.mem.set(name, data);
    this.failed.delete(name);
  }

  private async loadOne(name: string): Promise<string | null> {
    const hit = this.mem.get(name);
    if (hit) return hit;

    const running = this.inflight.get(name);
    if (running) return running;

    const task = (async (): Promise<string | null> => {
      // ② 外部缓存
      if (this.opts.cache) {
        try {
          const cached = await this.opts.cache.get(name);
          if (cached) {
            this.put(name, cached);
            return cached;
          }
        } catch {
          /* 缓存坏了就当没命中 */
        }
      }
      // ③ GlyphWiki
      const reply = await fetchGlyphWikiGlyph(name, this.opts);
      if (!reply) {
        this.failed.add(name);
        return null;
      }
      this.put(name, reply.data);
      if (this.opts.cache) {
        try {
          await this.opts.cache.set(name, reply.data);
        } catch {
          /* 写缓存失败不影响本次渲染 */
        }
      }
      this.opts.onGlyph?.(name, reply.data);
      return reply.data;
    })();

    this.inflight.set(name, task);
    try {
      return await task;
    } finally {
      this.inflight.delete(name);
    }
  }

  /**
   * 把 names 里还缺的字形补齐 (并发上限默认 4)。
   * 已经在内存/负缓存里的会跳过。
   */
  async ensure(names: string[], concurrency?: number): Promise<EnsureResult> {
    const todo = [...new Set(names)].filter((n) => n && !this.mem.has(n) && !this.failed.has(n));
    const limit = Math.max(1, concurrency ?? this.opts.concurrency ?? 4);
    let fetched = 0;
    const failed: string[] = [];

    let idx = 0;
    const worker = async (): Promise<void> => {
      for (;;) {
        const i = idx++;
        if (i >= todo.length) return;
        const name = todo[i];
        const data = await this.loadOne(name);
        if (data) fetched++;
        else failed.push(name);
      }
    };
    await Promise.all(Array.from({ length: Math.min(limit, todo.length) }, worker));
    return { fetched, failed };
  }
}

/**
 * 从一个 IDS 串里猜出需要哪些字形名 (只处理 `uXXXX` 形式的部件)。
 *
 * 注意: 这里只是**预取提示**, 真正的部件名由 ids 解析 + 变体后缀 (-01/-05/-06…)
 * 决定。宁可多取几个, 别漏取 —— 漏了就要在渲染中途等网络。
 */
export function guessGlyphNames(ids: string, suffixes: string[] = [""]): string[] {
  const out = new Set<string>();
  const re = /[uU]([0-9a-fA-F]{4,6})/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(ids)) !== null) {
    for (const s of suffixes) out.add(`u${m[1].toLowerCase()}${s}`);
  }
  // 直接写的汉字也收进来 (u+hex)
  for (const ch of ids) {
    const cp = ch.codePointAt(0);
    if (cp && cp > 0x2e80) for (const s of suffixes) out.add(`u${cp.toString(16)}${s}`);
  }
  return [...out];
}
