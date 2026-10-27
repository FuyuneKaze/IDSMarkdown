/* 端到端冒烟: 真字形库 + buildComposite, 查合成树里的 99 矩形与叶子取名
 *
 * 不走 renderSvg (那要 kage-bundle.js 真渲染), 只查「组字决策」这一段,
 * 也就是这次移植改动的全部范围: 叶子变体选择 + 包围盒 + 矩形分配。
 *
 * 用法: node analysis/smoke_compose.cjs
 */
const fs = require("fs");
const path = require("path");

const loaded = new Map();          // 假装是 kage-bundle.js 的字形表
globalThis.clearGlyphs = () => loaded.clear();
globalThis.loadGlyph = (name, data) => loaded.set(name, data);
globalThis.renderGlyph = () => '<path d="M0 0L1 1"/>';
globalThis.getGlyphBox = () => ({ x1: 0, y1: 0, x2: 200, y2: 200 });
globalThis.getGlyphData = (name) => loaded.get(name) || "";

const { KageEngine } = require("./tsout/kageEngine.js");

const t0 = Date.now();
const raw = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "public", "core_glyphs.json"), "utf8"));
const all = raw.glyphs;
let n = 0;
const eng = new KageEngine();
for (const k of Object.keys(all)) {
  if (k.charCodeAt(0) !== 117 /* u */) continue;   // 只要 uXXXX 系部件
  eng.glyphData.set(k, all[k]);
  n++;
}
console.log(`字形库: ${Object.keys(all).length} 条, 取 u* 部件 ${n} 条, ` +
  `载入 ${((Date.now() - t0) / 1000).toFixed(1)}s`);

const CASES = [
  "⿰氵工", "⿰木木", "⿱宀丁", "⿲木木木", "⿳一口一",
  "⿰⿱口木刂", "⿱⿰日月心", "⿰亻匕", "⿸广木",
];

let fail = 0;
for (const ids of CASES) {
  try {
    loaded.clear();
    const pos = { pos: 0 };
    const r = eng.buildComposite(ids, pos);
    const lines = (r.data || "").split("$").filter((s) => s.startsWith("99:"));
    const parsed = pos.pos === ids.length;
    const rects = lines.map((s) => {
      const p = s.split(":");
      return `${p[7]}@[${p[3]},${p[4]},${p[5]},${p[6]}]`;
    });
    const bad = lines.length === 0 && !eng.glyphData.has(r.rootName);
    if (bad) fail++;
    console.log(`${bad ? "x" : "v"} ${ids}  解析完整=${parsed} 根=${r.rootName} ` +
      `子件=${lines.length}`);
    console.log(`    ${rects.join("  ")}`);
  } catch (e) {
    fail++;
    console.log(`x ${ids}  抛异常: ${e && e.message}`);
  }
}
console.log(fail ? `\n失败 ${fail} / ${CASES.length}` : `\n全部 ${CASES.length} 例通过`);
process.exit(fail ? 1 : 0);
