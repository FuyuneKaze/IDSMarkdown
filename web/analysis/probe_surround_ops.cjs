/* 验证 ⿽ (U+2FFD) 当前是怎么渲染的: SURROUND_OPS 里没有它 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const pub = path.join(__dirname, "..", "public");
vm.runInThisContext(fs.readFileSync(path.join(pub, "kage-bundle.js"), "utf8"),
  { filename: "kage-bundle.js" });
const { KageEngine } = require("./tsout/kageEngine.js");
const { isSurroundOp, idsOperatorArity } = require("./tsout/charUtils.js");

const raw = JSON.parse(fs.readFileSync(path.join(pub, "core_glyphs.json"), "utf8"));
const eng = new KageEngine();
for (const k of Object.keys(raw.glyphs)) {
  if (k.charCodeAt(0) === 117) eng.glyphData.set(k, raw.glyphs[k]);
}
eng._ready = true;

const OPS = { "⿴": 0x2ff4, "⿵": 0x2ff5, "⿽": 0x2ffd, "⿼": 0x2ffc, "⿻": 0x2ffb };
console.log("SURROUND_OPS 判定:");
for (const [ch, cp] of Object.entries(OPS)) {
  console.log(`  ${ch} U+${cp.toString(16).toUpperCase()}  isSurroundOp=${isSurroundOp(cp)}  arity=${idsOperatorArity(cp)}`);
}
console.log("\n实际合成 (斗 = ⿽十⺀):");
for (const expr of ["⿽十⺀", "⿻十⺀", "⿸十⺀"]) {
  const r = eng.buildComposite(expr, { pos: 0 });
  const rects = (r.data || "").split("$").filter((s) => s.startsWith("99:"))
    .map((s) => { const p = s.split(":"); return `${p[7]}[${p[3]},${p[4]},${p[5]},${p[6]}]`; });
  console.log(`  ${expr} → ${rects.join("  ") || "(空)"}`);
}
