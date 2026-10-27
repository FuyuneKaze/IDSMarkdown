/* 查 ⿾(镜像)/⿿(旋转) 为什么会"消失"
 * 三件事分开看: ① 发出的 KAGE 数据 ② 渲染器认不认那条 0:99 命令 ③ 坐标有没有跑出画布
 */
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

function nums(s) {
  return (s.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
}

for (const expr of ["止", "⿾止", "予", "⿿予", "木", "⿾木", "⿿木", "日", "⿾日"]) {
  eng.idsToSvg.clear();
  const r = eng.buildComposite(expr, { pos: 0 });
  const svg = eng.renderSvg(expr);
  const paths = svg ? (svg.match(/<path/g) || []).length : 0;
  // 取所有 path 的 d 属性里的数字, 看范围
  let lo = Infinity, hi = -Infinity;
  if (svg) {
    for (const m of svg.matchAll(/d="([^"]*)"/g)) {
      for (const v of nums(m[1])) { if (v < lo) lo = v; if (v > hi) hi = v; }
    }
  }
  console.log(`\n=== ${expr} ===`);
  console.log(`  合成数据: ${(r.data || "(空)").slice(0, 120)}`);
  console.log(`  SVG: ${svg ? svg.length + " 字符, " + paths + " 个 path" : "× null"}` +
    (svg && paths ? `, 坐标范围 [${lo.toFixed(1)}, ${hi.toFixed(1)}]` : ""));
}
