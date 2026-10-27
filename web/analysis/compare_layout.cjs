/* 对照: TS 移植的分配算式 与 Python ids_anal.IDS 实际用的矩形 */
const fs = require("fs");
const path = require("path");

const { layoutRects, KageEngine } = require("./tsout/kageEngine.js");

const ref = JSON.parse(fs.readFileSync(path.join(__dirname, "layout_ref.json"), "utf8"));
const OPCP = { "⿰": 0x2ff0, "⿱": 0x2ff1, "⿲": 0x2ff2, "⿳": 0x2ff3 };

/* ---------- ① layoutRects: 喂 Python 算好的 box, 看算出的矩形 ---------- */
let bad1 = 0;
let worst1 = 0;
for (const c of ref.cases) {
  const boxes = c.boxes.map(([x1, y1, x2, y2]) => ({ x1, y1, x2, y2 }));
  const got = layoutRects(OPCP[c.op], boxes);
  if (got.length !== c.rects.length) {
    console.log(`  x ${c.op} 数量不符 ref=${c.rects.length} got=${got.length}`);
    bad1++;
    continue;
  }
  for (let i = 0; i < c.rects.length; i++) {
    const w = c.rects[i];
    const g = got[i];
    const d = Math.max(
      Math.abs(g.x1 - w[0]), Math.abs(g.y1 - w[1]),
      Math.abs(g.x2 - w[2]), Math.abs(g.y2 - w[3]),
    );
    worst1 = Math.max(worst1, d);
    if (d > 1e-4) {
      bad1++;
      if (bad1 <= 6) {
        console.log(`  x ${c.op}${c.args.join("")} rect${i}`);
        console.log(`      ref=[${w.join(", ")}]`);
        console.log(`      got=[${g.x1}, ${g.y1}, ${g.x2}, ${g.y2}]  d=${d}`);
      }
    }
  }
}
console.log(`① layoutRects: ${ref.cases.length} 用例, 不一致 ${bad1}, 最大偏差 ${worst1}`);

/* ---------- ② strokicBboxOf: 注入迷你库, 与 Python ids_anal.bbox 对照 ---------- */
const eng = new KageEngine();
for (const [nm, data] of Object.entries(ref.db)) eng.glyphData.set(nm, data);

let bad2 = 0;
let worst2 = 0;
let checked = 0;
for (const c of ref.cases) {
  for (let i = 0; i < c.leafNames.length; i++) {
    const nm = c.leafNames[i];
    const w = c.boxes[i];
    const g = eng.strokicBboxOf(nm);
    if (!isFinite(g.x1) || g.x1 > g.x2) {
      console.log(`  x ${nm}: 空盒`);
      bad2++;
      continue;
    }
    const d = Math.max(
      Math.abs(g.x1 - w[0]), Math.abs(g.y1 - w[1]),
      Math.abs(g.x2 - w[2]), Math.abs(g.y2 - w[3]),
    );
    worst2 = Math.max(worst2, d);
    checked++;
    if (d > 1e-4) {
      bad2++;
      if (bad2 <= 40) {
        console.log(`  x ${nm}`);
        console.log(`      ref=[${w.join(", ")}]`);
        console.log(`      got=[${g.x1}, ${g.y1}, ${g.x2}, ${g.y2}]  d=${d}`);
      }
    }
  }
}
console.log(`② strokicBboxOf: 检查 ${checked} 个部件盒, 不一致 ${bad2}, 最大偏差 ${worst2}`);

/* ---------- ③ 纯算式 × 3600 随机盒 (空/倒置/越界/极扁) ---------- */
let fref = null;
try {
  fref = JSON.parse(fs.readFileSync(path.join(__dirname, "formula_ref.json"), "utf8"));
} catch {
  fref = null;
}
if (fref) {
  let bad3 = 0;
  let worst3 = 0;
  let checked3 = 0;
  let div = 0;
  let deg = 0;
  const fin = (r) => r && Number.isFinite(r.x1) && Number.isFinite(r.y1)
    && Number.isFinite(r.x2) && Number.isFinite(r.y2);
  for (const c of fref.cases) {
    const boxes = c.boxes.map(([x1, y1, x2, y2]) => ({ x1, y1, x2, y2 }));
    const got = layoutRects(OPCP[c.op], boxes);
    const mid = boxes[1];
    // 中件的"被拉伸跨度": 只有 ⿲⿳ 有这个量
    const midSpan = c.op === "⿲" ? mid.x2 - mid.x1
      : c.op === "⿳" ? mid.y2 - mid.y1 : 1;
    // Python 端在这些输入上会崩 (除零) 或算出 x1>x2 的倒置矩形:
    //   rects===null        → ZeroDivisionError (后件外沿=200 / 中件零宽)
    //   midSpan <= 0        → 中件倒置或空, k_c 变号, 中件矩形被算反
    // 约定: 一律退化成"分界带本身", 这里只查兜底结果有限且非退化。
    if (c.rects === null || (midSpan <= 1e-9 && c.op !== "⿰" && c.op !== "⿱")) {
      if (c.rects === null) div++; else deg++;
      const cc = got[1];
      // 只查"有限 + 中件带非退化"。矩形越出 0-200 是正常结果
      // (真字形 ⿰氵工 的左件就是 233.04), 不是缺陷。
      const ok = got.every(fin)
        && (midSpan <= 1e-9 ? (c.op === "⿲" ? cc.x2 > cc.x1 : cc.y2 > cc.y1) : true);
      if (!ok) {
        bad3++;
        if (bad3 <= 5) {
          console.log(`  x ${c.op} 退化兜底非有限/中件退化: ${JSON.stringify(got)}`);
          console.log(`      boxes=${JSON.stringify(c.boxes)}`);
        }
      }
      continue;
    }
    checked3++;
    for (let i = 0; i < c.rects.length; i++) {
      const w = c.rects[i];
      const g = got[i];
      const d = Math.max(
        Math.abs(g.x1 - w[0]), Math.abs(g.y1 - w[1]),
        Math.abs(g.x2 - w[2]), Math.abs(g.y2 - w[3]),
      );
      worst3 = Math.max(worst3, d);
      if (!(d <= 1e-9)) {
        bad3++;
        if (bad3 <= 5) {
          console.log(`  x ${c.op} boxes=${JSON.stringify(c.boxes)} rect${i}`);
          console.log(`      ref=[${w.join(", ")}]`);
          console.log(`      got=[${g.x1}, ${g.y1}, ${g.x2}, ${g.y2}]`);
        }
      }
    }
  }
  console.log(`③ layoutRects 随机盒: 核对 ${checked3} 例, 不一致 ${bad3}, ` +
    `最大偏差 ${worst3} (另有 ${div} 例 Python 除零 + ${deg} 例中件倒置盒, ` +
    `按约定只查兜底)`);
}
