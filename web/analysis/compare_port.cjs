/* 对照: TS 移植 strokeOutline.ts  vs  Python 原版 stroke_outer.py */
const fs = require("fs");
const path = require("path");
const { strokicBoundary } = require("./tsout/strokeOutline.js");

const ref = JSON.parse(fs.readFileSync(path.join(__dirname, "port_ref.json"), "utf8"));

const maxdiff = (got, want) => {
  if (!got && !want) return 0;
  if (!got || !want) return Infinity;
  let m = 0;
  for (let i = 0; i < 4; i++) m = Math.max(m, Math.abs(got[i] - want[i]));
  return m;
};

let bad = 0;
let worst = 0;
const byType = {};

for (const r of ref) {
  const a = strokicBoundary(r.stro, false);
  const b = strokicBoundary(r.stro, true);
  const ea = a ? [a.x1, a.y1, a.x2, a.y2] : null;
  const eb = b ? [b.x1, b.y1, b.x2, b.y2] : null;
  const da = maxdiff(ea, r.off);
  const db = maxdiff(eb, r.on);
  const d = Math.max(da, db);
  worst = Math.max(worst, d);
  byType[r.type] = Math.max(byType[r.type] || 0, d);
  if (d > 1e-9) {
    bad++;
    if (bad <= 6) {
      console.log(`  x type=${r.type}  ${r.stro}`);
      console.log(`      off ref=${JSON.stringify(r.off)}`);
      console.log(`          got=${JSON.stringify(ea)}  diff=${da}`);
      console.log(`      on  ref=${JSON.stringify(r.on)}`);
      console.log(`          got=${JSON.stringify(eb)}  diff=${db}`);
    }
  }
}

console.log(`\n样本 ${ref.length} 条`);
console.log(`不一致 ${bad} 条, 最大偏差 ${worst}`);
console.log(
  "各类型最大偏差: " +
    Object.keys(byType)
      .sort()
      .map((k) => `${k}:${byType[k]}`)
      .join("  ")
);
