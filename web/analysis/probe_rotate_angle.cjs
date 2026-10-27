/* 用库里的真字形反推 ⿿ 到底是转 90/180/270 度
 * 办法: 找一个 ⿿X 的字, 把它的真字形墨迹框 和 X 的真字形墨迹框比
 *   框交换 → 90/270 度;  框不变 → 180 度
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const pub = path.join(__dirname, "..", "public");
vm.runInThisContext(fs.readFileSync(path.join(pub, "kage-bundle.js"), "utf8"),
  { filename: "kage-bundle.js" });

const raw = JSON.parse(fs.readFileSync(path.join(pub, "core_glyphs.json"), "utf8"));
const G = raw.glyphs;
const has = (n) => Object.prototype.hasOwnProperty.call(G, n);

function inkBox(name) {
  clearGlyphs();
  if (!has(name)) return null;
  loadGlyph(name, G[name]);
  // 递归把 99 依赖也装进去
  const seen = new Set([name]);
  const stack = [G[name]];
  while (stack.length) {
    for (const seg of stack.pop().split("$")) {
      const p = seg.split(":");
      if (p[0] !== "99" || p.length < 8) continue;
      const dep = p[7].split("@")[0];
      if (seen.has(dep) || !has(dep)) continue;
      seen.add(dep);
      loadGlyph(dep, G[dep]);
      stack.push(G[dep]);
    }
  }
  const pg = new Polygons();
  kage.makeGlyph(pg, name);
  if (!pg.array.length) return null;
  let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9;
  for (const poly of pg.array) {
    for (const p of poly.array) {
      if (p.x < x1) x1 = p.x; if (p.x > x2) x2 = p.x;
      if (p.y < y1) y1 = p.y; if (p.y > y2) y2 = p.y;
    }
  }
  return { w: +(x2 - x1).toFixed(1), h: +(y2 - y1).toFixed(1) };
}

// 文档/库里的 ⿿ 例子: 结果字 → 操作数
const PAIRS = [
  ["u2010f", "𠄏", ["u4e86", "u4e86-01", "u4e86-02"], "了"],
  ["u20114", "𠄔", ["u4e88", "u4e88-01", "u4e88-02"], "予"],
  ["u20544", "𠕄", ["u51f9", "u51f9-01", "u51f9-02"], "凹"],
  ["u22a0b", "𢨋", ["u6216", "u6216-01", "u6216-02"], "或"],
];

for (const [rn, rc, ops, oc] of PAIRS) {
  const rb = has(rn) ? inkBox(rn) : null;
  let ob = null, used = "";
  for (const o of ops) { if (has(o)) { ob = inkBox(o); used = o; break; } }
  console.log(`${rc} (${rn}) ${rb ? `${rb.w} x ${rb.h}` : "库里没有"}   ` +
    `vs ${oc} (${used}) ${ob ? `${ob.w} x ${ob.h}` : "库里没有"}`);
  if (rb && ob) {
    const swap = Math.abs(rb.w - ob.h) + Math.abs(rb.h - ob.w);
    const same = Math.abs(rb.w - ob.w) + Math.abs(rb.h - ob.h);
    console.log(`     框交换差 ${swap.toFixed(1)}  框不变差 ${same.toFixed(1)}  → ` +
      `${swap < same ? "更像 90/270 度" : "更像 180 度"}`);
  }
}
