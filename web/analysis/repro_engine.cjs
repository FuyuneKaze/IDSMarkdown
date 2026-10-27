// 模拟引擎: 只用 glyphData 里的名字 → composeStrokes → surroundPlan
const fs = require("fs");
const path = require("path");
const cmp = require("./tsout/compose.js");
const cav = require("./tsout/cavity.js");
const bundle = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "public/core_glyphs.json"), "utf8"));
const G = bundle.glyphs || bundle;
const f = (b) => b ? `(${[...b].map((v) => (+v).toFixed(1)).join(", ")})` : "null";

// 与 kageEngine.composeStrokes 等价: 只取直绘笔画 (不做 99 展开, 这里数据已是展平的)
function strokesOfName(nm) {
  const d = G[nm];
  return d ? cav.strokesOf(d) : [];
}

for (const [op, c, i] of [["⿺", "u8fb6", "u9f3b"], ["⿰", "u9ea6", "u5c06"], ["⿲", "u5fc4", "u675f"]]) {
  const cs = strokesOfName(c), is_ = strokesOfName(i);
  console.log(`${op}${c}+${i}: 容器 ${cs.length} 笔, 内部件 ${is_.length} 笔`);
  if (!cs.length || !is_.length) { console.log("   → 笔画为空, 会退回 legacy"); continue; }
  const p = cmp.surroundPlan(op, cs, is_);
  const faces = cav.faces(cs);
  console.log(`   候选 ${p.candidates.length} (面 ${faces.faces.length}), 空腔 ${f(p.cavity)}, basis ${f(p.basis)}`);
  console.log(`   target ${p.target ? f([p.target.x1, p.target.y1, p.target.x2, p.target.y2]) : "null → 退回 legacy"}`);
}
