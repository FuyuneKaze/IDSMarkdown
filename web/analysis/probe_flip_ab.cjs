/* 干净 A/B: 同一个测量方法 (多边形墨迹范围) 比 原字 vs ⿾镜像 vs ⿿旋转 */
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

function measure(expr) {
  clearGlyphs();
  const pos = { pos: 0 };
  const r = eng.buildComposite(expr, pos);
  if (!r.rootName) return { err: "无根" };
  const data = r.data || eng.glyphData.get(r.rootName);
  loadGlyph(r.rootName, data);
  if (!r.data) eng.resolveDeps(data, new Set([r.rootName]));
  else eng.resolveDeps(data, new Set([r.rootName]));
  // 依赖
  for (const nm of Object.keys(eng.glyphData)) {
    if (nm !== r.rootName) { /* 按需 */ }
  }
  const strokes = kage.getEachStrokes(data);
  const pg = new Polygons();
  kage.makeGlyph(pg, r.rootName);
  let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9;
  for (const poly of pg.array) {
    for (const p of poly.array) {
      if (p.x < x1) x1 = p.x; if (p.x > x2) x2 = p.x;
      if (p.y < y1) y1 = p.y; if (p.y > y2) y2 = p.y;
    }
  }
  return {
    strokes: strokes.length,
    types: strokes.map((s) => s[0]).join(","),
    polys: pg.array.length,
    ink: pg.array.length
      ? `${Math.round(x1)},${Math.round(y1)} → ${Math.round(x2)},${Math.round(y2)}` +
        `  (${Math.round(x2 - x1)} x ${Math.round(y2 - y1)})`
      : "(空)",
  };
}

// 依赖要先全灌进 kBuhin, 否则 99 引用展不开
function preload(names) {
  for (const n of names) {
    const d = eng.glyphData.get(n);
    if (d) loadGlyph(n, d);
  }
}

for (const expr of ["予", "⿾予", "⿿予", "木", "⿾木", "⿿木", "日", "⿾日"]) {
  // 把该表达式可能用到的叶子都灌进去
  preload(["u4e88", "u6728", "u65e5", "u6b62",
    "u4e88-01", "u4e88-02", "u6728-01", "u6728-02",
    "u65e5-01", "u65e5-02", "u6b62-01", "u6b62-02"]);
  const m = measure(expr);
  console.log(`${expr.padEnd(5)} 笔画 ${m.strokes}  类型[${m.types}]  多边形 ${m.polys}  墨迹 ${m.ink}`);
}
