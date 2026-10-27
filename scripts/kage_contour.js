/**
 * KAGE 轮廓提取 — Node.js 桥接脚本
 *
 * 用法:
 *   node kage_contour.js
 *   从 stdin 读取 JSON, 输出 JSON 到 stdout
 *
 * 输入格式:
 *   { "glyphs": [{"name": "test", "data": "1:0:0:24:10:..."}, ...] }
 *
 * 输出格式:
 *   { "glyphs": [{"name": "test", "contours": [[[x,y,off],...], ...]}, ...] }
 *
 * 每个 contour 是一个封闭多边形: [[x, y, off], [x, y, off], ...]
 * off: 0=顶点, 1=贝塞尔控制点
 */

var fs = require('fs');
var path = require('path');

// 加载 KAGE 引擎 (所有类挂全局)
var bundlePath = path.join(__dirname, 'kage-bundle.js');
var bundleSrc = fs.readFileSync(bundlePath, 'utf8');
eval(bundleSrc);

// --- 从 stdin 累积输入 (跨平台) ---
var chunks = [];
process.stdin.on('data', function(chunk) { chunks.push(chunk); });
process.stdin.on('end', function() {
    var inputJson = Buffer.concat(chunks).toString('utf8');
    var input = JSON.parse(inputJson);
    var glyphs = input.glyphs || [];

    var results = [];

    for (var gi = 0; gi < glyphs.length; gi++) {
        var g = glyphs[gi];
        var result = { name: g.name, contours: [] };

        try {
            var k = new Kage();
            k.kBuhin.push(g.name, g.data);

            var polygons = new Polygons();
            k.makeGlyph(polygons, g.name);

            for (var pi = 0; pi < polygons.array.length; pi++) {
                var poly = polygons.array[pi];
                var pts = [];
                for (var pj = 0; pj < poly.array.length; pj++) {
                    var pt = poly.array[pj];
                    pts.push([pt.x, pt.y, pt.off]);
                }
                if (pts.length > 0) {
                    result.contours.push(pts);
                }
            }
        } catch (e) {
            result.error = e.message || String(e);
        }

        results.push(result);
    }

    process.stdout.write(JSON.stringify({ glyphs: results }));
});
