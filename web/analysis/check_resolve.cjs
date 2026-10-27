const fs = require("fs"), path = require("path");
global.loadGlyph=()=>{}; global.clearGlyphs=()=>{}; global.renderGlyph=()=>""; global.getGlyphBox=()=>null; global.getGlyphData=()=>null;
const { KageEngine } = require("./tsout/kageEngine.js");
const e = new KageEngine();
const G = (JSON.parse(fs.readFileSync(path.join(__dirname,"..","public","core_glyphs.json"),"utf8")).glyphs) || {};
for (const k of Object.keys(G)) e.glyphData.set(k, G[k]);
console.log("  has u9ea6-j =", e.glyphData.has("u9ea6-j"));
console.log("  resolveRef('u9ea6-j') =", e.resolveRef("u9ea6-j"));
console.log("  collectStrokes(G['u9ea6']) =", e.collectStrokes(G["u9ea6"], new Set(["u9ea6"])).length);
console.log("  G['u9ea6'] =", G["u9ea6"]);
console.log("  G['u9ea6-j'] =", (G["u9ea6-j"]||"").slice(0,80));

