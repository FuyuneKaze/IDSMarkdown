const fs = require("fs");
const path = require("path");
const so = require("./tsout/strokeOutline.js");
const ke = require("./tsout/kageEngine.js");
const L = JSON.parse(fs.readFileSync(path.join(__dirname, "layout_cases.json"), "utf8"));

const f = (b) => b ? `(${b.x1.toFixed(1)}, ${b.y1.toFixed(1)}, ${b.x2.toFixed(1)}, ${b.y2.toFixed(1)})` : "null";
const order = ["u9ea6", "u5c06", "u5fc4", "u675f", "u8d1f", "u8fb6", "u9f3b"];
console.log("=== 每笔 shrink 盒并集 (strokesBbox, BBOX_OFS) vs Python bbox ===");
const boxes = {};
for (const nm of order) {
  const b = so.strokesBbox(L[nm].strokes, true, so.BBOX_OFS);
  boxes[nm] = b;
  const py = L[nm].bbox;
  const d = Math.max(Math.abs(b.x1-py[0]), Math.abs(b.y1-py[1]), Math.abs(b.x2-py[2]), Math.abs(b.y2-py[3]));
  console.log(`  ${nm}  ts ${f(b)}  py (${py.join(", ")})  最大差 ${d.toFixed(3)}`);
}
const mk = (nm) => boxes[nm];
console.log("\n=== layoutRects ===");
console.log("  ⿰麦将 :", ke.layoutRects(0x2FF0, [mk("u9ea6"), mk("u5c06")]).map(f).join("  "));
console.log("  ⿲忄束负:", ke.layoutRects(0x2FF2, [mk("u5fc4"), mk("u675f"), mk("u8d1f")]).map(f).join("  "));


