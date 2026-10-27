/* 忠实路径: 先 kageDataFromIds (会 clearGlyphs + buildComposite + resolveDeps),
   再逐步看 getEachStrokes / adjustStrokes / 多边形数量 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const pub = path.join(__dirname, "..", "public");
vm.runInThisContext(fs.readFileSync(path.join(pub, "kage-bundle.js"), "utf8"),
  { filename: "kage-bundle.js" });
const { KageEngine } = require("./tsout/kageEngine.js");

const raw = JSON.parse(fs.readFileSync(path.join(pub, "core_glyphs.json"), "utf8"));
const eng = new KageEngine();
for (const k of Object.keys(raw.glyphs)) {
  if (k.charCodeAt(0) === 117) eng.glyphData.set(k, raw.glyphs[k]);
}
eng._ready = true;

function box(pg) {
  let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9;
  for (const poly of pg.array) {
    for (const p of poly.array) {
      if (p.x < x1) x1 = p.x; if (p.x > x2) x2 = p.x;
      if (p.y < y1) y1 = p.y; if (p.y > y2) y2 = p.y;
    }
  }
  return [x1, y1, x2, y2].map((v) => Math.round(v)).join(",");
}

for (const expr of ["予", "⿿予", "木", "⿿木", "⿾木"]) {
  const data = eng.kageDataFromIds(expr);
  const root = kage.kBuhin.hash ? null : null;
  // 找根名: 就是刚从 buildComposite 造出来的 _cNNN
  const rootName = Object.keys(kage.kBuhin.hash).filter((k) => k.startsWith("_c")).pop();
  const dep = expr.includes("予") ? "u4e88" : "u6728";
  const s = kage.getEachStrokes(data);
  const s2 = kage.adjustStrokes(s.map((r) => r.slice()));
  const pg = new Polygons();
  kage.makeGlyph(pg, rootName);
  console.log(`\n=== ${expr} ===`);
  console.log(`  dep(${dep}) 在 kBuhin: ${!!kage.kBuhin.search(dep)}`);
  console.log(`  getEachStrokes: ${s.length} 条  →  adjustStrokes: ${s2.length} 条`);
  console.log(`  类型序列: ${s2.map((r) => r[0]).join(" ")}`);
  console.log(`  多边形 ${pg.array.length} 个, 墨迹范围 [${box(pg)}]`);
}
