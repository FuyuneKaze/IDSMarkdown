/**
 * parity_ts.cjs —— 用 parity_cases.json 里的**同一份笔画**跑 TS 侧, 逐值对拍
 *
 * 只比算法, 不比名字解析: 输入笔画串由 Python 侧写好, TS 侧原样使用。
 */
const fs = require("fs");
const path = require("path");
const cav = require("./tsout/cavity.js");
const cb = require("./tsout/centralBox.js");
const cmp = require("./tsout/compose.js");

const cases = JSON.parse(fs.readFileSync(path.join(__dirname, "parity_cases.json"), "utf8"));

const near = (a, b, tol = 1e-6) =>
  a === null && b === null ? true : a !== null && b !== null && Math.abs(a - b) <= tol;
const eqBox = (a, b, tol = 1e-6) => {
  if (!a && !b) return true;
  if (!a || !b) return false;
  for (let i = 0; i < 4; i++) if (!near(a[i], b[i], tol)) return false;
  return true;
};
const fmt = (b) => (b ? "(" + b.map((v) => v.toFixed(2)).join(", ") + ")" : "null");

let pass = 0;
const fails = [];
for (const c of cases) {
  const plan = cmp.surroundPlan(c.op, c.cstrokes, c.istrokes);
  const cbx = cb.centralBox(c.istrokes, 1, true);
  // 注意: Python 的 box_map 用的是**盒中心**, 不是骨架重心
  const ibb2 = cbx
    ? cb.boxMap(cbx.box, [(cbx.box[0] + cbx.box[2]) / 2, (cbx.box[1] + cbx.box[3]) / 2], 2)
    : null;

  const checks = {
    outer: eqBox(plan.outer ? [plan.outer[0], plan.outer[1], plan.outer[2], plan.outer[3]] : null, c.outer, 1e-6),
    candidates: plan.candidates.length === c.candidates.length &&
      plan.candidates.every((b, i) => eqBox(b, c.candidates[i], 1e-6)),
    cavity: eqBox(plan.cavity, c.cavity, 1e-6),
    ibb1: eqBox(plan.ibb1, c.ibb1, 1e-6),
    cbRaw: eqBox(cbx ? cbx.box : null, c.cb_raw, 1e-6),
    ibb2: eqBox(ibb2, c.ibb2, 1e-6),
    basis: eqBox(plan.basis, c.basis, 1e-6),
    target: plan.target
      ? eqBox([plan.target.x1, plan.target.y1, plan.target.x2, plan.target.y2], c.target, 1e-6)
      : eqBox(null, c.target, 1e-6),
  };

  const bad = Object.entries(checks).filter(([, ok]) => !ok).map(([k]) => k);
  if (bad.length === 0) { pass++; continue; }
  fails.push({ c, plan, cbx, ibb2, bad, checks });
}

console.log(`=== 对拍: ${pass}/${cases.length} 完全一致 ===`);
for (const f of fails) {
  const { c, plan, cbx, ibb2, bad } = f;
  console.log(`\n✗ ${c.op}${c.cname}+${c.iname}  不一致字段: ${bad.join(", ")}`);
  console.log(`   outer  py ${fmt(c.outer)}`);
  console.log(`          ts ${fmt(plan.outer)}`);
  if (bad.includes("candidates")) {
    console.log(`   候选   py ${c.candidates.length} 个: ${c.candidates.map(fmt).join(" ")}`);
    console.log(`          ts ${plan.candidates.length} 个: ${plan.candidates.map(fmt).join(" ")}`);
  }
  if (bad.includes("cavity")) {
    console.log(`   空腔   py ${fmt(c.cavity)}`);
    console.log(`          ts ${fmt(plan.cavity)}`);
  }
  if (bad.includes("ibb1")) {
    console.log(`   ibb1   py ${fmt(c.ibb1)}`);
    console.log(`          ts ${fmt(plan.ibb1)}`);
  }
  if (bad.includes("cbRaw")) {
    console.log(`   中宫   py ${fmt(c.cb_raw)}  center ${c.cb_center}`);
    console.log(`          ts ${fmt(cbx ? cbx.box : null)}  center ${cbx ? cbx.center : null}`);
  }
  if (bad.includes("ibb2")) {
    console.log(`   ibb2   py ${fmt(c.ibb2)}`);
    console.log(`          ts ${fmt(ibb2)}`);
  }
  if (bad.includes("basis")) {
    console.log(`   basis  py ${fmt(c.basis)}`);
    console.log(`          ts ${fmt(plan.basis)}`);
  }
  if (bad.includes("target")) {
    console.log(`   target py ${fmt(c.target)}`);
    console.log(`          ts ${plan.target ? fmt([plan.target.x1, plan.target.y1, plan.target.x2, plan.target.y2]) : "null"}`);
  }
}
