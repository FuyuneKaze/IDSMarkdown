/**
 * engine_test.cjs —— 不开浏览器, 直接实例化 KageEngine 跑真实 bundle
 *
 * 把 kage-bundle.js 的全局函数打桩, 手动灌 glyphData, 然后调内部方法
 * (TS 的 private 只在编译期, 运行时可直接访问)。用来定位"布局塌/空盒"这一环。
 */
const fs = require("fs");
const path = require("path");

// ---- kage-bundle.js 的全局依赖: 打桩 ----
global.loadGlyph = () => {};
global.clearGlyphs = () => {};
global.renderGlyph = () => "";
global.getGlyphBox = () => null;
global.getGlyphData = () => null;

const { KageEngine } = require("./tsout/kageEngine.js");
const so = require("./tsout/strokeOutline.js");

const engine = new KageEngine();
const bundle = JSON.parse(
  fs.readFileSync(path.join(__dirname, "..", "public", "core_glyphs.json"), "utf8"),
);
const G = bundle.glyphs || bundle;
for (const k of Object.keys(G)) engine.glyphData.set(k, G[k]);
engine._ready = true;
console.log(`灌入字形 ${engine.glyphData.size} 条`);

const f = (b) => (b ? `(${b.x1.toFixed(1)}, ${b.y1.toFixed(1)}, ${b.x2.toFixed(1)}, ${b.y2.toFixed(1)})` : "null");

console.log("\n=== collectStrokes / strokicBboxOf ===");
for (const nm of ["u9ea6", "u9ea6-j", "u5c06", "u5c06-j", "u8fb6", "u9f3b"]) {
  const d = engine.glyphData.get(nm);
  const st = d ? engine.collectStrokes(d, new Set([nm])) : [];
  const bb = engine.strokicBboxOf(nm);
  console.log(`  ${nm.padEnd(9)} 展开 ${String(st.length).padStart(3)} 笔, strokicBbox ${f(bb)}`);
}

console.log("\n=== ⿰麦将 / ⿲忄束负 的分配 ===");
for (const [op, names] of [
  [0x2ff0, ["u9ea6", "u5c06"]],
  [0x2ff2, ["u5fc4", "u675f", "u8d1f"]],
]) {
  const boxes = names.map((n) => engine.strokicBboxOf(n));
  const rects = require("./tsout/kageEngine.js").layoutRects(op, boxes);
  console.log(`  ${String.fromCodePoint(op)}: ${rects.map(f).join("  ")}`);
}

console.log("\n=== planSurround ⿺辶鼻 ===");
const plan = engine.planSurround("⿺", "u8fb6", "u9f3b");
if (!plan) console.log("  null (composeStrokes 取不到笔画)");
else {
  console.log(`  候选 ${plan.candidates.length}  空腔 ${f(plan.cavity)}`);
  console.log(`  ibb1 ${f(plan.ibb1)}  ibb2 ${f(plan.ibb2)}  basis ${f(plan.basis)}`);
  console.log(`  target ${plan.target ? f(plan.target) : "null → 会退回 legacy"}`);
  console.log(`  容器笔画 ${engine.composeStrokes("u8fb6").length}, 内部件笔画 ${engine.composeStrokes("u9f3b").length}`);
}
