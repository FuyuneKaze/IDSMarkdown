/* web 侧真·每次敲键耗时: 走完整的 renderSvg (含 kage-bundle.js 出轮廓 + 拼 SVG)
 *
 * 做法: 把 public/kage-bundle.js 当普通脚本跑进本进程 (它全是顶层函数声明),
 * 于是 loadGlyph/renderGlyph/clearGlyphs/getGlyphBox/getGlyphData 就成了全局 ——
 * 和浏览器里一模一样。再把 core_glyphs.json 灌进 engine.glyphData 顶掉 fetch。
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const pub = path.join(__dirname, "..", "public");
vm.runInThisContext(fs.readFileSync(path.join(pub, "kage-bundle.js"), "utf8"),
  { filename: "kage-bundle.js" });

const { KageEngine } = require("./tsout/kageEngine.js");

let t0 = Date.now();
const raw = JSON.parse(fs.readFileSync(path.join(pub, "core_glyphs.json"), "utf8"));
const eng = new KageEngine();
for (const k of Object.keys(raw.glyphs)) {
  if (k.charCodeAt(0) === 117) eng.glyphData.set(k, raw.glyphs[k]);
}
eng._ready = true;
console.log(`  冷启动 (读 + parse + 建 Map)            ${String(Date.now() - t0).padStart(6)} ms` +
  `   (${Object.keys(raw.glyphs).length} 条)`);

const CASES = ["⿰氵工", "⿱宀丁", "⿲木木木", "⿳一口一", "⿰忄忽", "⿰⿱口木刂", "⿱⿰日月心"];
for (const ids of CASES) {
  eng.idsToSvg.clear();
  t0 = Date.now();
  const first = eng.renderSvg(ids);            // 冷
  const cold = Date.now() - t0;

  const t1 = Date.now();
  const cached = eng.renderSvg(ids);           // 命中 idsToSvg 缓存
  const warm = Date.now() - t1;

  const okk = first && first.includes("<svg");
  console.log(`  renderSvg(${ids})`.padEnd(30) +
    `冷 ${String(cold).padStart(4)} ms   缓存 ${String(warm).padStart(2)} ms   ` +
    `${okk ? "SVG " + first.length + " 字符" : "× 失败"}`);
}
