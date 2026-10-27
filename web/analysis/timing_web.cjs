/* web 侧: 冷启动一次 + 每次组字多久 (真字形库, 只量组字决策那一段) */
const fs = require("fs");
const path = require("path");

globalThis.clearGlyphs = () => {};
globalThis.loadGlyph = () => {};
globalThis.renderGlyph = () => '<path d="M0 0L1 1"/>';
globalThis.getGlyphBox = () => ({ x1: 0, y1: 0, x2: 200, y2: 200 });
globalThis.getGlyphData = () => "";

const { KageEngine } = require("./tsout/kageEngine.js");

let t0 = Date.now();
const raw = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "public", "core_glyphs.json"), "utf8"));
const eng = new KageEngine();
for (const k of Object.keys(raw.glyphs)) {
  if (k.charCodeAt(0) === 117) eng.glyphData.set(k, raw.glyphs[k]);
}
console.log(`  冷启动 (读 + JSON.parse + 建 Map)      ` +
  `${String(Date.now() - t0).padStart(6)} ms   (${Object.keys(raw.glyphs).length} 条)`);

const CASES = ["⿰氵工", "⿱宀丁", "⿲木木木", "⿳一口一", "⿰⿱口木刂", "⿱⿰日月心"];
for (const ids of CASES) {
  // 真编辑器每敲一次都会 renderSvg → clearGlyphs + bboxCache.clear(),
  // 所以这里也每次清缓存, 量的才是「第一次见这个 IDS」的冷路径
  eng.bboxCache.clear();
  eng.buildComposite(ids, { pos: 0 });          // 预热 (JIT)
  const n = 20;
  let cold = 0;
  for (let i = 0; i < n; i++) {
    eng.bboxCache.clear();
    const t = process.hrtime.bigint();
    eng.buildComposite(ids, { pos: 0 });
    cold += Number(process.hrtime.bigint() - t) / 1e6;
  }
  const warm0 = process.hrtime.bigint();
  eng.buildComposite(ids, { pos: 0 });
  const warm = Number(process.hrtime.bigint() - warm0) / 1e6;
  console.log(`  buildComposite(${ids})`.padEnd(34) +
    `冷 ${(cold / n).toFixed(3).padStart(7)} ms   缓存命中 ${warm.toFixed(3).padStart(6)} ms`);
}
