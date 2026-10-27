/* 验证 dfTransform 的 inside 门: 多边形只要有一点跑出命令框, 整条就被跳过
 * 办法: 手工造数据, 同一个字分别用「紧框 0-200」和「宽框 -20..220」发旋转命令
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

function loadAll(name) {
  clearGlyphs();
  if (!has(name)) return false;
  loadGlyph(name, G[name]);
  const seen = new Set([name]);
  const stack = [G[name]];
  while (stack.length) {
    for (const seg of stack.pop().split("$")) {
      const p = seg.split(":");
      if (p[0] !== "99" || p.length < 8) continue;
      const dep = p[7].split("@")[0];
      if (seen.has(dep) || !has(dep)) continue;
      seen.add(dep); loadGlyph(dep, G[dep]); stack.push(G[dep]);
    }
  }
  return true;
}

function render(data, root) {
  loadGlyph(root, data);
  const pg = new Polygons();
  kage.makeGlyph(pg, root);
  let x1 = 1e9, y1 = 1e9, x2 = -1e9, y2 = -1e9;
  for (const poly of pg.array) {
    for (const p of poly.array) {
      if (p.x < x1) x1 = p.x; if (p.x > x2) x2 = p.x;
      if (p.y < y1) y1 = p.y; if (p.y > y2) y2 = p.y;
    }
  }
  return { n: pg.array.length, box: pg.array.length ? [x1, y1, x2, y2].map((v) => Math.round(v)) : null };
}

// 找几个墨迹跑出 0-200 的部件 (用紧框时应有一部分多边形被跳过)
const cand = [];
for (const k of Object.keys(G)) {
  if (k.charCodeAt(0) !== 117 || k.includes("-")) continue;
  if (cand.length >= 400) break;
  if (!loadAll(k)) continue;
  const r = render(G[k], k);
  if (r.box && (r.box[0] < 0 || r.box[1] < 0 || r.box[2] > 200 || r.box[3] > 200)) {
    cand.push([k, r]);
    if (cand.length >= 3) break;
  }
}
console.log("墨迹跑出 0-200 的部件样例:", cand.map((c) => `${c[0]} ${JSON.stringify(c[1].box)}`).join("  ") || "(没找到)");

for (const [k, base] of cand) {
  console.log(`\n=== ${k}  (原样: ${base.n} 个多边形, 框 ${JSON.stringify(base.box)}) ===`);
  const variants = [
    ["无命令", `99:0:0:0:0:200:200:${k}:0:0:0`],
    ["转90 紧框", `99:0:0:0:0:200:200:${k}:0:0:0$0:99:1:0:0:200:200`],
    ["转90 宽框", `99:0:0:0:0:200:200:${k}:0:0:0$0:99:1:-20:-20:220:220`],
    ["转180 紧框", `99:0:0:0:0:200:200:${k}:0:0:0$0:99:2:0:0:200:200`],
    ["镜像 紧框", `99:0:0:0:0:200:200:${k}:0:0:0$0:98:0:0:0:200:200`],
    ["镜像 宽框", `99:0:0:0:0:200:200:${k}:0:0:0$0:98:0:-20:-20:220:220`],
  ];
  for (const [label, data] of variants) {
    const r = render(data, "_t");
    console.log(`  ${label.padEnd(10)} 多边形 ${String(r.n).padStart(3)}  框 ${JSON.stringify(r.box)}`);
  }
}
