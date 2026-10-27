// 候选引擎: 加载 4 词典 → romaji 前缀匹配 → 返回分行候选
// 移植自 C++ CandidateEngine.h/cpp

export interface RowResult {
  label: string;
  subLabel: string;
  color: string;
  candidates: string[];
  consumeLen: number;
}

export type CandidateSource = "ja" | "ko" | "jamo" | "vi";
export type CandidateSourceState = Record<CandidateSource, boolean>;

// interface _JaEntry { syllable: string; on: string[]; kun: string[] }
// interface _KoEntry { romaji: string; hangul: string; cjk: string[] }
interface _ViEntry { reading: string; stripped: string; chars: string[] }

const COLORS = { on: "#E05555", kun: "#5599E0", ko: "#55C055", jamo: "#55C0C0", vi: "#E09955" };

// 二分查找: 返回 sortedKeys 中 >= target 的第一个索引
function lowerBound(sortedKeys: string[], target: string): number {
  let lo = 0, hi = sortedKeys.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (sortedKeys[mid] < target) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function commonPrefixLen(a: string, b: string): number {
  const n = Math.min(a.length, b.length);
  let i = 0;
  while (i < n && a[i] === b[i]) i++;
  return i;
}

// 音节组相似度排序: 完整匹配优先 → 公共前缀长优先 → 长度差小优先
function similarityCompare(a: string, b: string, ref: string): number {
  if (a === ref) return -1;
  if (b === ref) return 1;
  const ca = commonPrefixLen(a, ref);
  const cb = commonPrefixLen(b, ref);
  if (ca !== cb) return cb - ca;
  const da = Math.abs(a.length - ref.length);
  const db = Math.abs(b.length - ref.length);
  if (da !== db) return da - db;
  return a < b ? -1 : a > b ? 1 : 0;
}

class CandidateEngine {
  private ready = false;

  // 候选数据源开关 (工具栏下拉控制, 默认全部关闭)
  private enabled: CandidateSourceState = { ja: false, ko: false, jamo: false, vi: false };

  setEnabled(source: CandidateSource, on: boolean): void {
    this.enabled[source] = on;
    this.cache.clear(); // 开关变化后旧缓存失效
  }

  getEnabled(): CandidateSourceState {
    return { ...this.enabled };
  }

  // 日语: syllable → {on, kun}
  private jaKeys: string[] = [];
  private jaMap = new Map<string, { on: string[]; kun: string[] }>();

  // 韩文: romaji → {hangul, cjk}
  private koKeys: string[] = [];
  private koMap = new Map<string, { hangul: string; cjk: string[] }>();

  // 越南文: 按 stripped 排序的条目
  private viStripped: string[] = [];
  private viEntries: _ViEntry[] = [];

  // 古谚文 Jamo
  private jamoInit = new Map<string, string>();
  private jamoMed = new Map<string, string>();
  private jamoFinal = new Map<string, string>();
  private jamoInitKeys: string[] = [];
  private jamoMedKeys: string[] = [];
  private jamoFinKeys: string[] = [];

  // romaji → kana 表 (按 romaji 长度降序)
  private romajiToKana: [string, string][] = [];

  // query LRU 缓存
  private cache = new Map<string, RowResult[]>();
  // kana 转换缓存
  private kanaCache = new Map<string, string>();

  // 就绪回调
  private readyCallbacks: Array<() => void> = [];
  onReady(cb: () => void) { this.readyCallbacks.push(cb); }
  private _loading = false;

  async loadData(dir = "/data"): Promise<void> {
    const tLoad = performance.now();
    console.log("[CandEngine] loadData 开始, dir=", dir);
    this.initRomajiKanaTables();
    console.log("[CandEngine] romajiToKana 表初始化完成, 共", this.romajiToKana.length, "条");
    let japOk = false, korOk = false, vietOk = false;
    try {
      const t = performance.now();
      await this.loadJapanese(`${dir}/jap_cjk.json`);
      japOk = true;
      console.log("[CandEngine] jap_cjk.json 加载成功,", this.jaKeys.length, "条, 耗时", (performance.now() - t).toFixed(0), "ms");
    } catch (e) { console.warn("[CandEngine] jap_cjk.json 加载失败:", e); }
    try {
      const t = performance.now();
      await this.loadKorean(`${dir}/hangul_cjk.json`);
      korOk = true;
      console.log("[CandEngine] hangul_cjk.json 加载成功,", this.koKeys.length, "条, 耗时", (performance.now() - t).toFixed(0), "ms");
    } catch (e) { console.warn("[CandEngine] hangul_cjk.json 加载失败:", e); }
    try {
      const t = performance.now();
      await this.loadVietnamese(`${dir}/viet_cjk.txt`);
      vietOk = true;
      console.log("[CandEngine] viet_cjk.txt 加载成功,", this.viEntries.length, "条, 耗时", (performance.now() - t).toFixed(0), "ms");
    } catch (e) { console.warn("[CandEngine] viet_cjk.txt 加载失败:", e); }
    try {
      await this.loadJamo(`${dir}/extend_hangul_map.json`);
    } catch (e) { console.warn("[CandEngine] extend_hangul_map.json 加载失败:", e); }

    this.ready = japOk || korOk || vietOk;
    this._loading = false;
    console.log(`[CandEngine] 加载完成: ready=${this.ready} JA=${this.jaKeys.length} KO=${this.koKeys.length} VI=${this.viEntries.length}, 总耗时 ${(performance.now() - tLoad).toFixed(0)}ms`);
    if (this.ready) {
      for (const cb of this.readyCallbacks) cb();
      this.readyCallbacks = [];
    }
  }

  isReady(): boolean {
    const r = this.ready;
    if (!r) console.log("[CandEngine] isReady() = false, jaKeys:", this.jaKeys.length, "koKeys:", this.koKeys.length, "romajiToKana:", this.romajiToKana.length);
    return r;
  }

  // ── 公共 ──

  toKatakana(romaji: string): string {
    if (!romaji || !this.romajiToKana) return "";
    const cached = this.kanaCache.get(romaji);
    if (cached !== undefined) return cached;
    let result = "";
    let pos = 0;
    while (pos < romaji.length) {
      let matched = false;
      for (const [rk, kana] of this.romajiToKana) {
        if (romaji.slice(pos, pos + rk.length).toLowerCase() === rk) {
          result += kana;
          pos += rk.length;
          matched = true;
          break;
        }
      }
      if (!matched) { result += romaji[pos]; pos++; }
    }
    this.kanaCache.set(romaji, result);
    return result;
  }

  toHiragana(romaji: string): string {
    const kata = this.toKatakana(romaji);
    let hira = "";
    for (const ch of kata) {
      const cp = ch.codePointAt(0)!;
      if (cp >= 0x30A1 && cp <= 0x30F6) {
        hira += String.fromCodePoint(cp - 0x60);
      } else {
        hira += ch;
      }
    }
    return hira;
  }

  static stripDiacritics(s: string): string {
    const nfd = s.normalize("NFD");
    let result = "";
    for (const ch of nfd) {
      const cp = ch.codePointAt(0)!;
      // 跳过组合用发音符 (Combining Diacritical Marks, U+0300–U+036F)
      if (cp >= 0x0300 && cp <= 0x036F) continue;
      result += ch;
    }
    result = result.normalize("NFC");
    result = result.replace(/đ/g, "d"); // đ
    result = result.replace(/Đ/g, "D"); // Đ
    return result;
  }

  // ── query ──

  query(prefix: string): RowResult[] {
    if (!prefix) return [];
    const t0 = performance.now();

    // 懒加载: 首次查询时自动触发数据加载
    if (!this.ready && !this._loading) {
      this._loading = true;
      console.log("[CandEngine] query 触发自动加载");
      this.loadData().then(() => {
        console.log("[CandEngine] 自动加载完成, 通知", this.readyCallbacks.length, "个回调");
        for (const cb of this.readyCallbacks) cb();
      });
    }
    if (!this.ready) return [];

    const cached = this.cache.get(prefix);
    if (cached) { console.log("[CandEngine] query cache hit,", (performance.now() - t0).toFixed(0), "ms"); return cached; }

    try {
    const rows: RowResult[] = [];
    const MAX_GROUPS = 12;
    const MAX_CANDIDATES = 120;

    // 最长前缀匹配辅助: 在 sortedKeys 中找最长匹配长度 (预留工具, 暂未使用)
    // const findLongestPrefix = (
    //   sortedKeys: string[],
    //   filter: (key: string) => boolean,
    //   maxLen: number,
    // ): { len: number; sub: string } | null => {
    //   for (let len = Math.min(prefix.length, maxLen); len > 0; len--) {
    //     const sub = prefix.slice(0, len);
    //     const lb = lowerBound(sortedKeys, sub);
    //     for (let i = lb; i < sortedKeys.length && sortedKeys[i].startsWith(sub); i++) {
    //       if (filter(sortedKeys[i])) return { len, sub };
    //     }
    //   }
    //   return null;
    // };

    // 1) 日语 on + kun (单次遍历, 限制输出)
    if (this.enabled.ja)
    {
      let onMatch: { len: number; sub: string } | null = null;
      let kunMatch: { len: number; sub: string } | null = null;
      // 同时找 on/kun 的最长前缀
      for (let len = Math.min(prefix.length, 17); len > 0; len--) {
        const sub = prefix.slice(0, len);
        const lb = lowerBound(this.jaKeys, sub);
        for (let i = lb; i < this.jaKeys.length && this.jaKeys[i].startsWith(sub); i++) {
          const e = this.jaMap.get(this.jaKeys[i])!;
          if (!onMatch && e.on.length > 0) onMatch = { len, sub };
          if (!kunMatch && e.kun.length > 0) kunMatch = { len, sub };
          if (onMatch && kunMatch) break;
        }
        if (onMatch && kunMatch) break;
      }

      const onGroups = new Map<string, string[]>();
      const kunGroups = new Map<string, string[]>();

      if (onMatch || kunMatch) {
        const sub = (onMatch || kunMatch)!.sub;
        const lb = lowerBound(this.jaKeys, sub);
        let onTotal = 0, kunTotal = 0, groupCount = 0;
        for (let i = lb; i < this.jaKeys.length && this.jaKeys[i].startsWith(sub) && groupCount < MAX_GROUPS; i++) {
          const syllable = this.jaKeys[i];
          const e = this.jaMap.get(syllable)!;
          if (onMatch && e.on.length > 0 && onTotal < MAX_CANDIDATES) {
            const existing = onGroups.get(syllable);
            if (existing) { existing.push(...e.on); }
            else { onGroups.set(syllable, [...e.on]); groupCount++; }
            onTotal += e.on.length;
          }
          if (kunMatch && e.kun.length > 0 && kunTotal < MAX_CANDIDATES) {
            const existing = kunGroups.get(syllable);
            if (existing) { existing.push(...e.kun); }
            else { kunGroups.set(syllable, [...e.kun]); }
            kunTotal += e.kun.length;
          }
        }

        if (onMatch && onGroups.size > 0) {
          const row: RowResult = { label: this.toKatakana(onMatch.sub), subLabel: "音", color: COLORS.on, candidates: [], consumeLen: onMatch.len };
          const syllables = [...onGroups.keys()].sort((a, b) => similarityCompare(a, b, prefix));
          for (const syl of syllables) {
            row.candidates.push(`\x00${this.toKatakana(syl)}`);
            row.candidates.push(...onGroups.get(syl)!);
          }
          rows.push(row);
        }

        if (kunMatch && kunGroups.size > 0) {
          const row: RowResult = { label: this.toHiragana(kunMatch.sub), subLabel: "訓", color: COLORS.kun, candidates: [], consumeLen: kunMatch.len };
          const syllables = [...kunGroups.keys()].sort((a, b) => similarityCompare(a, b, prefix));
          for (const syl of syllables) {
            row.candidates.push(`\x00${this.toHiragana(syl)}`);
            row.candidates.push(...kunGroups.get(syl)!);
          }
          rows.push(row);
        }
      }
    }

    // 2) 韩文 (谚文, 绿)
    if (this.enabled.ko)
    {
      let koMatch: { len: number; sub: string } | null = null;
      for (let len = Math.min(prefix.length, 10); len > 0; len--) {
        const sub = prefix.slice(0, len);
        const lb = lowerBound(this.koKeys, sub);
        for (let i = lb; i < this.koKeys.length && this.koKeys[i].startsWith(sub); i++) {
          if (this.koMap.get(this.koKeys[i])!.cjk.length > 0) { koMatch = { len, sub }; break; }
        }
        if (koMatch) break;
      }
      if (koMatch) {
        const row: RowResult = { label: this.romajiToHangul(koMatch.sub), subLabel: "韓", color: COLORS.ko, candidates: [], consumeLen: koMatch.len };
        const groups = new Map<string, string[]>();
        const lb = lowerBound(this.koKeys, koMatch.sub);
        let total = 0, groupCount = 0;
        for (let i = lb; i < this.koKeys.length && this.koKeys[i].startsWith(koMatch.sub) && groupCount < MAX_GROUPS && total < MAX_CANDIDATES; i++) {
          const romaji = this.koKeys[i];
          const e = this.koMap.get(romaji)!;
          if (e.cjk.length > 0) {
            groups.set(romaji, [...e.cjk]);
            total += e.cjk.length;
            groupCount++;
          }
        }
        const readings = [...groups.keys()].sort((a, b) => similarityCompare(a, b, prefix));
        for (const r of readings) {
          const e = this.koMap.get(r);
          const hangul = e?.hangul || this.romajiToHangul(r);
          if (hangul) row.candidates.push(`\x00${hangul}`);
          row.candidates.push(...groups.get(r)!);
        }
        if (row.candidates.length > 0) rows.push(row);
      }
    }

    // 4) 古谚文 (Jamo, 青)
    if (this.enabled.jamo && this.jamoInitKeys.length > 0 && this.jamoMedKeys.length > 0) {
      let pos = 0;
      let initRomaji = "";
      let initCh = "";
      let medRomaji = "";
      let medCh = "";
      let finRomaji = "";
      let finCh = "";

      for (const key of this.jamoInitKeys) {
        if (prefix.slice(pos).startsWith(key)) {
          initRomaji = key;
          initCh = this.jamoInit.get(key)!;
          pos += key.length;
          break;
        }
      }

      // 元音开头: 零辅音占位
      if (!initCh) {
        for (const key of this.jamoMedKeys) {
          if (prefix.slice(pos).startsWith(key)) {
            initCh = this.jamoInit.get("'")!;
            initRomaji = "'";
            break;
          }
        }
      }

      if (initCh) {
        for (const key of this.jamoMedKeys) {
          if (prefix.slice(pos).startsWith(key)) {
            medRomaji = key;
            medCh = this.jamoMed.get(key)!;
            pos += key.length;
            break;
          }
        }
      }

      if (initCh && medCh) {
        for (const key of this.jamoFinKeys) {
          if (prefix.slice(pos).startsWith(key)) {
            finRomaji = key;
            finCh = this.jamoFinal.get(key)!;
            pos += key.length;
            break;
          }
        }
      }

      if (initCh && medCh) {
        const jamoIndex = (ch: string, baseCp: number): number => {
          const idx = ch.codePointAt(0)! - baseCp;
          return idx >= 0 ? idx : -1;
        };

        const initIdx = jamoIndex(initCh, 0x1100);
        const medIdx = jamoIndex(medCh, 0x1161);
        const finIdx = finCh ? jamoIndex(finCh, 0x11A8) + 1 : 0;

        const isModern = initIdx >= 0 && medIdx >= 0 && finIdx >= 0
          && initIdx < 19 && medIdx < 21 && finIdx < 28;

        let composedCp = "";
        if (isModern) {
          composedCp = String.fromCodePoint(0xAC00 + initIdx * 588 + medIdx * 28 + finIdx);
        }

        // 检查是否与韩文行重复
        let duplicateWithKo = false;
        if (isModern) {
          for (const r of rows) {
            if (r.subLabel === "韓" && r.label === composedCp) {
              duplicateWithKo = true;
              break;
            }
          }
        }

        const row: RowResult = {
          label: "",
          subLabel: initRomaji + medRomaji + finRomaji,
          color: COLORS.jamo,
          candidates: [],
          consumeLen: pos,
        };

        const combined = initCh + medCh + (finCh || "");
        if (isModern && !duplicateWithKo) {
          row.label = composedCp;
          row.candidates.push(composedCp);
        } else {
          row.label = "古";
          row.candidates.push(combined);
        }
        rows.push(row);
      } else if (initCh) {
        const row: RowResult = {
          label: "古",
          subLabel: initRomaji,
          color: COLORS.jamo,
          candidates: [initCh],
          consumeLen: pos,
        };
        rows.push(row);
      }
    }

    // 3) 越南文 (国语字 + 汉字/喃字, 橙)
    if (this.enabled.vi)
    {
      let matchLen = 0;
      let queryStripped = "";
      viFound:
      for (let len = prefix.length; len > 0; len--) {
        queryStripped = CandidateEngine.stripDiacritics(prefix.slice(0, len));
        const lb = lowerBound(this.viStripped, queryStripped);
        for (let i = lb; i < this.viEntries.length && this.viEntries[i].stripped.startsWith(queryStripped); i++) {
          if (this.viEntries[i].chars.length > 0) {
            matchLen = len;
            break viFound;
          }
        }
      }
      if (matchLen > 0) {
        const row: RowResult = { label: "", subLabel: "越", color: COLORS.vi, candidates: [], consumeLen: matchLen };
        const groups = new Map<string, string[]>();
        const lb = lowerBound(this.viStripped, queryStripped!);
        let total = 0, groupCount = 0;
        for (let i = lb; i < this.viEntries.length && this.viEntries[i].stripped.startsWith(queryStripped!) && groupCount < MAX_GROUPS && total < MAX_CANDIDATES; i++) {
          const e = this.viEntries[i];
          if (e.chars.length > 0) {
            groups.set(e.reading, [...e.chars]);
            total += e.chars.length;
            groupCount++;
          }
        }
        // 越南文 reading 带声调, 用去声调形式与输入比较
        const readings = [...groups.keys()].sort((a, b) => {
          const sa = CandidateEngine.stripDiacritics(a);
          const sb = CandidateEngine.stripDiacritics(b);
          return similarityCompare(sa, sb, prefix);
        });
        if (readings.length > 0) row.label = readings[0];
        for (const rd of readings) {
          row.candidates.push(`\x00${rd}`);
          row.candidates.push(...groups.get(rd)!);
        }
        if (row.candidates.length > 0) rows.push(row);
      }
    }

    // LRU 缓存 (上限 50)
    this.cache.set(prefix, rows);
    if (this.cache.size > 50) {
      const first = this.cache.keys().next().value;
      if (first) this.cache.delete(first);
    }
    console.log("[CandEngine] query(\"" + prefix + "\")", (performance.now() - t0).toFixed(0), "ms, rows:", rows.length);
    return rows;
    } catch (e) {
      console.error("[CandEngine] query 崩溃:", e);
      return [];
    }
  }

  // ── 私有 ──

  private async loadJapanese(path: string): Promise<void> {
    const resp = await fetch(path);
    const root = await resp.json();
    for (const [syllable, entry] of Object.entries(root)) {
      const obj = entry as any;
      const on = (obj.on || []) as string[];
      const kun = (obj.kun || []) as string[];
      if (on.length > 0 || kun.length > 0) {
        this.jaMap.set(syllable, { on, kun });
      }
    }
    this.jaKeys = [...this.jaMap.keys()].sort();
  }

  private async loadKorean(path: string): Promise<void> {
    const resp = await fetch(path);
    const root = await resp.json();
    for (const [romaji, entry] of Object.entries(root)) {
      const obj = entry as any;
      const hangul = (obj.hangul || "") as string;
      const cjk = (obj.cjk || []) as string[];
      if (cjk.length > 0) {
        this.koMap.set(romaji, { hangul, cjk });
      }
    }
    this.koKeys = [...this.koMap.keys()].sort();
  }

  private async loadVietnamese(path: string): Promise<void> {
    const resp = await fetch(path);
    const text = await resp.text();
    for (const line of text.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const colonPos = trimmed.indexOf(":");
      if (colonPos < 0) continue;
      const reading = trimmed.slice(0, colonPos).trim();
      const stripped = CandidateEngine.stripDiacritics(reading);
      const chars = trimmed.slice(colonPos + 1).trim().split(/\s+/).filter(Boolean);
      if (chars.length > 0) {
        this.viEntries.push({ reading, stripped, chars });
      }
    }
    // 按 stripped 排序以支持二分查找 (ASCII 纯字母, 直接比较)
    this.viEntries.sort((a, b) => a.stripped < b.stripped ? -1 : a.stripped > b.stripped ? 1 : 0);
    this.viStripped = this.viEntries.map(e => e.stripped);
  }

  private async loadJamo(path: string): Promise<void> {
    const resp = await fetch(path);
    const root = await resp.json();
    const loadSection = (obj: Record<string, string>, map: Map<string, string>) => {
      for (const [key, val] of Object.entries(obj)) {
        if (val.length > 0) map.set(key, val[0]);
      }
    };
    loadSection(root.choseong || {}, this.jamoInit);
    loadSection(root.jungseong || {}, this.jamoMed);
    loadSection(root.jongseong || {}, this.jamoFinal);

    // 按长度降序排列 (贪心最长匹配)
    const buildKeyList = (map: Map<string, string>): string[] => {
      return [...map.keys()].sort((a, b) => b.length - a.length || a.localeCompare(b));
    };
    this.jamoInitKeys = buildKeyList(this.jamoInit);
    this.jamoMedKeys = buildKeyList(this.jamoMed);
    this.jamoFinKeys = buildKeyList(this.jamoFinal);
  }

  private initRomajiKanaTables(): void {
    const pairs: [string, string][] = [
      // 拗音+外来 (3-4字母, 优先匹配)
      ["kya", "キャ"], ["kyu", "キュ"], ["kyo", "キョ"],
      ["sya", "シャ"], ["syu", "シュ"], ["syo", "シェ"],
      ["tya", "チャ"], ["tyu", "チュ"], ["tyo", "チョ"],
      ["nya", "ニャ"], ["nyu", "ニュ"], ["nyo", "ニョ"],
      ["hya", "ヒャ"], ["hyu", "ヒュ"], ["hyo", "ヒョ"],
      ["mya", "ミャ"], ["myu", "ミュ"], ["myo", "ミョ"],
      ["rya", "リャ"], ["ryu", "リュ"], ["ryo", "リョ"],
      ["gya", "ギャ"], ["gyu", "ギュ"], ["gyo", "ギョ"],
      ["zya", "ジャ"], ["zyu", "ジュ"], ["zyo", "ジョ"],
      ["dya", "ヂャ"], ["dyu", "デュ"], ["dyo", "ヂョ"],
      ["bya", "ビャ"], ["byu", "ビュ"], ["byo", "ビョ"],
      ["pya", "ピャ"], ["pyu", "ピュ"], ["pyo", "ピョ"],
      ["sye", "シェ"], ["zye", "ジェ"], ["tye", "チェ"],
      ["tsa", "ツァ"], ["tsi", "ツィ"], ["tse", "ツェ"], ["tso", "ツォ"],
      ["kwa", "クァ"], ["kwi", "クィ"], ["kwe", "クェ"], ["kwo", "クォ"],
      ["gwa", "グァ"],
      ["ttya", "ッチャ"], ["ttyu", "ッチュ"], ["ttyo", "ッチョ"],
      ["ssya", "ッシャ"], ["ssyu", "ッシュ"], ["ssyo", "ッショ"],
      ["hhya", "ッヒャ"], ["hhyu", "ッヒュ"], ["hhyo", "ッヒョ"],
      // 外来语 (2字母)
      ["fa", "ファ"], ["fi", "フィ"], ["fe", "フェ"], ["fo", "フォ"],
      ["va", "ヴァ"], ["vi", "ヴィ"], ["vu", "ヴ"], ["ve", "ヴェ"], ["vo", "ヴォ"],
      ["ye", "イェ"],
      // 促音 (3字母)
      ["kka", "ッカ"], ["kki", "ッキ"], ["kku", "ック"], ["kke", "ッケ"], ["kko", "ッコ"],
      ["ssa", "ッサ"], ["ssi", "ッシ"], ["ssu", "ッス"], ["sse", "ッセ"], ["sso", "ッソ"],
      ["tta", "ッタ"], ["tti", "ッチ"], ["ttu", "ッツ"], ["tte", "ッテ"], ["tto", "ット"],
      ["ppa", "ッパ"], ["ppi", "ッピ"], ["ppu", "ップ"], ["ppe", "ッペ"], ["ppo", "ッポ"],
      // 基本音 (2字母)
      ["ka", "カ"], ["ki", "キ"], ["ku", "ク"], ["ke", "ケ"], ["ko", "コ"],
      ["sa", "サ"], ["si", "シ"], ["su", "ス"], ["se", "セ"], ["so", "ソ"],
      ["ta", "タ"], ["ti", "チ"], ["tu", "ツ"], ["te", "テ"], ["to", "ト"],
      ["na", "ナ"], ["ni", "ニ"], ["nu", "ヌ"], ["ne", "ネ"], ["no", "ノ"],
      ["ha", "ハ"], ["hi", "ヒ"], ["hu", "フ"], ["he", "ヘ"], ["ho", "ホ"],
      ["ma", "マ"], ["mi", "ミ"], ["mu", "ム"], ["me", "メ"], ["mo", "モ"],
      ["ya", "ヤ"], ["yu", "ユ"], ["yo", "ヨ"],
      ["ra", "ラ"], ["ri", "リ"], ["ru", "ル"], ["re", "レ"], ["ro", "ロ"],
      ["wa", "ワ"], ["wo", "ヲ"], ["wi", "ヰ"], ["we", "ヱ"],
      ["ga", "ガ"], ["gi", "ギ"], ["gu", "グ"], ["ge", "ゲ"], ["go", "ゴ"],
      ["za", "ザ"], ["zi", "ジ"], ["zu", "ズ"], ["ze", "ゼ"], ["zo", "ゾ"],
      ["da", "ダ"], ["di", "ヂ"], ["du", "ヅ"], ["de", "デ"], ["do", "ド"],
      ["ba", "バ"], ["bi", "ビ"], ["bu", "ブ"], ["be", "ベ"], ["bo", "ボ"],
      ["pa", "パ"], ["pi", "ピ"], ["pu", "プ"], ["pe", "ペ"], ["po", "ポ"],
      // 単音 (1字母, 最后匹配)
      ["a", "ア"], ["i", "イ"], ["u", "ウ"], ["e", "エ"], ["o", "オ"],
      ["n", "ン"],
    ];
    this.romajiToKana = pairs;
    // 按 romaji 长度降序 (贪心最长匹配)
    this.romajiToKana.sort((a, b) => b[0].length - a[0].length);
  }

  private romajiToHangul(romaji: string): string {
    if (!romaji) return "";
    // 精确匹配
    for (const [r, e] of this.koMap) {
      if (r === romaji && e.hangul) return e.hangul[0];
    }
    // jamo 组合 fallback
    let pos = 0;
    let initCh = "";
    let medCh = "";
    let finCh = "";

    for (const key of this.jamoInitKeys) {
      if (romaji.slice(pos).startsWith(key)) {
        initCh = this.jamoInit.get(key)!;
        pos += key.length;
        break;
      }
    }
    if (!initCh) return "";

    for (const key of this.jamoMedKeys) {
      if (romaji.slice(pos).startsWith(key)) {
        medCh = this.jamoMed.get(key)!;
        pos += key.length;
        break;
      }
    }
    if (!medCh) return "";

    for (const key of this.jamoFinKeys) {
      if (romaji.slice(pos).startsWith(key)) {
        finCh = this.jamoFinal.get(key)!;
        break;
      }
    }

    const jamoIndex = (ch: string, baseCp: number): number => {
      const idx = ch.codePointAt(0)! - baseCp;
      return idx >= 0 ? idx : -1;
    };

    const initIdx = jamoIndex(initCh, 0x1100);
    const medIdx = jamoIndex(medCh, 0x1161);
    const finIdx = finCh ? jamoIndex(finCh, 0x11A8) + 1 : 0;

    if (initIdx >= 0 && medIdx >= 0 && finIdx >= 0
      && initIdx < 19 && medIdx < 21 && finIdx < 28) {
      return String.fromCodePoint(0xAC00 + initIdx * 588 + medIdx * 28 + finIdx);
    }
    return "";
  }
}

export const candidateEngine = new CandidateEngine();
