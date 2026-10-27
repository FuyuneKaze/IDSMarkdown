const fs = require("fs");
const path = require("path");
const cav = require("./tsout/cavity.js");
const cb  = require("./tsout/centralBox.js");
const cmp = require("./tsout/compose.js");

const S = JSON.parse(fs.readFileSync(path.join(__dirname, "smoke_strokes.json"), "utf8"));
const f = (b) => b ? "(" + b.map((v) => v.toFixed(1)).join(",") + ")" : "null";

console.log("=== 空腔枚举 (对拍 Python 已知值) ===");
for (const [name, op] of [["u65e5", "⿴"], ["u7530", "⿴"], ["u65e5", "⿸"], ["u7530", "⿺"]]) {
  const r = cav.pickCavity(S[name], op);
  console.log(`  ${op}${name}  候选 ${r.candidates.length}  腔 ${f(r.cavity)}  外框 ${f(r.outer)}`);
  r.candidates.forEach((b, i) => console.log(`      [${i}] ${f(b)}`));
}

console.log("\n=== 中宫盒 (内部件 人) ===");
const c = cb.centralBox(S["u4eba"], 1, true);
console.log("  box", f(c.box), " center", c.center.map((v) => v.toFixed(1)));

console.log("\n=== 包围合成计划 ⿴日+人 ===");
const plan = cmp.surroundPlan("⿴", S["u65e5"], S["u4eba"]);
for (const k of ["cavity", "ibb1", "ibb2", "basis"]) console.log(`  ${k.padEnd(7)} ${f(plan[k])}`);
console.log("  target ", plan.target ? f([plan.target.x1, plan.target.y1, plan.target.x2, plan.target.y2]) : "null");
const done = cmp.composeSurround("⿴", S["u65e5"], S["u4eba"]);
console.log("  合成段数", done ? done.data.split("$").length : 0, done ? "(容器 5 + 内部件 2)" : "");
if (done) console.log("  内部件映射后:", done.data.split("$").slice(5).join(" | "));


