const fs = require("fs");
const path = require("path");
const so = require("./tsout/strokeOutline.js");
const ke = require("./tsout/kageEngine.js");
const py = JSON.parse(fs.readFileSync(path.join(__dirname, "layout_py.json"), "utf8"));
const L = JSON.parse(fs.readFileSync(path.join(__dirname, "layout_cases.json"), "utf8"));
const f = (b) => `(${b.x1.toFixed(2)}, ${b.y1.toFixed(2)}, ${b.x2.toFixed(2)}, ${b.y2.toFixed(2)})`;

// Python 用到的名字需要笔画: 本地 layout_cases.json 只有本体, 这里只验"本体 boxes 下 layoutRects 是否与 Python 同算式"
for (const rec of py) {
  const bases = rec.args.map((n) => L[n]);
  if (bases.some((b) => !b)) { console.log(`  ${rec.op}: 缺本体笔画, 跳过`); continue; }
  const boxes = bases.map((b) => so.strokesBbox(b.strokes, true, so.BBOX_OFS));
  const opCp = rec.op.codePointAt(0);
  const rects = ke.layoutRects(opCp, boxes);
  console.log(`${rec.op}${rec.args.join("")}`);
  console.log("  py(变体) :", rec.rects.map((r) => `(${r.map((v) => v.toFixed(2)).join(", ")})`).join("  "));
  console.log("  ts(本体) :", rects.map(f).join("  "));
}
console.log("\n注: py 用的是 -01/-02 变体的盒, ts 这里只能用本体盒, 所以数值不同是预期的;");
console.log("    真正要对的是「同名字 → 同盒 → 同矩形」, 需要把变体笔画也 dump 出来。");
