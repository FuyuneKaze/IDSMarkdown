/* 直接读 KAGE 库里 ⿾/⿿ 例子字的原始数据 —— 库里怎么写, 就是权威语义 */
const fs = require("fs");
const path = require("path");
const raw = JSON.parse(fs.readFileSync(
  path.join(__dirname, "..", "public", "core_glyphs.json"), "utf8"));
const G = raw.glyphs;
const has = (n) => Object.prototype.hasOwnProperty.call(G, n);

const NAMES = [
  ["u2010f", "𠄏 (文档: ⿿了)"],
  ["u20114", "𠄔 (文档: ⿿予)"],
  ["u20544", "𠕄 (文档: ⿿凹)"],
  ["u22a0b", "𢨋 (文档: ⿱或⿿或)"],
  ["u4e86", "了 (操作数)"],
  ["u4e88", "予 (操作数)"],
  ["u51f9", "凹 (操作数)"],
  ["u6216", "或 (操作数)"],
  // ⿾ 的例子
  ["u3193b", "𱤻 (文档: ⿾止)"],
  ["u6b62", "止 (操作数)"],
];

for (const [n, label] of NAMES) {
  console.log(`${label.padEnd(22)} ${n.padEnd(9)} ${has(n) ? (G[n] || "(空数据)") : "× 库里没有"}`);
}

// 顺带: 库里所有含 0:9x 命令的字形有多少, 用的是什么 a3
let cnt = {};
let shown = 0;
for (const k of Object.keys(G)) {
  const d = G[k];
  if (!d || d.indexOf(":9") < 0) continue;
  for (const seg of d.split("$")) {
    const p = seg.split(":");
    if (p[0] === "0" && (p[1] === "97" || p[1] === "98" || p[1] === "99")) {
      const key = `0:${p[1]}:${p[2]}`;
      cnt[key] = (cnt[key] || 0) + 1;
      if (shown < 6) { console.log(`  例: ${k} → ${seg}`); shown++; }
    }
  }
}
console.log("\n库里 0:9x 命令的分布:", JSON.stringify(cnt, null, 0));
