# 2026harucpp —— IDS 组字引擎与编辑器

用 **KAGE 笔画数据** 把一个 IDS（Ideographic Description Sequence，如 `⿴囗人`）
合成为一个字形，并提供 Markdown 编辑器做所见即所得的预览。

本项目的重点是**组字的几何求解**：不依赖从字体里学习放置，而是从**容器自身的墨迹**
求出「空腔」，再把内部件放进去。

## 目录

```
web/                     编辑器 (Vite + React 19 + TypeScript)
  src/editor/
    kageEngine.ts        KAGE 字形树展开 / IDS → 复合字形 / SVG 渲染
    strokeOutline.ts     笔画中心线采样 → 轮廓 → 单笔包围盒  (对应 scripts/stroke_outer.py)
    cavity.ts            容器墨迹补集的「空腔」枚举        (对应 scripts/cavity.py)
    centralBox.ts        内部件的「中宫盒」                (对应 scripts/central_box.py)
    compose.ts           包围结构的合成流程                (对应 scripts/ids_anal.surround)
    glyphSource.ts       字形数据来源: bundle → 缓存 → GlyphWiki API
  public/data/           词典表 (Unihan 派生, 见 THIRD-PARTY.md §3)
scripts/                 算法的 Python 实验实现 (与 web 端同一套语义)
web/analysis/            对拍 / 评分 / 诊断脚本, 以及 DATA_LAYER.md (数据层契约)
```

## 运行

```bash
cd web
npm install
npm run dev          # 开发服务器 (默认 http://localhost:5173)
npm run build        # tsc -b + vite build
```

### 数据从哪来

**仓库里不带字形数据**。`core_glyphs.json` 有 100+ MB，超过 GitHub 单文件上限，
也不应该进版本库。运行时的回退顺序（`web/src/editor/glyphSource.ts`）：

1. `web/public/core_glyphs.json`（有就用，零延迟）
2. 缓存（内存；可接 IndexedDB）
3. **GlyphWiki API**：`https://glyphwiki.org/api/glyph?name=u4e00`
   —— 该端点带 `Access-Control-Allow-Origin: *`，浏览器可直接取，**纯静态部署可行**

没有 bundle 也能用，只是第一次显示每个字会慢一点（按需取，且取过的会缓存）。

IDS 文本（`cjkvi-ids`，GPLv2）同样不入库；需要时自行下载，或只做字形合成（不需要 IDS 表）。

## 算法约定（改代码前请读）

- **99 引用的接缝拉伸**：`(sx,sy)` 是目标、`(sx2,sy2)` 是缝；`sx>100` 时 `sx-=200`。
  写反会让「忽/鼻」这类字反向拉伸。权威实现在 `kage-bundle.js` 的 `getEachStrokesOfBuhin`。
- **名字解析有两条语义**：第一轮叶子查找允许「后缀退化到本体」（查 `u670b-04` 可退化成 `u670b`）；
  字形内部引用的递归必须**精确优先 → 最长子串**，否则会串味（鹿-05 曾因此少 5 笔）。
- **空腔是补集的连通面**，不是最大内接空矩形；安放盒用「面内最大内接矩形」，
  用面的外接框会把容器笔画盖住。
- 数据层的完整契约见 [`web/analysis/DATA_LAYER.md`](web/analysis/DATA_LAYER.md)。

## 许可

- **源代码**：MIT，见 [`LICENSE`](LICENSE)
- **第三方数据/字体**：各自遵守原许可，见 [`THIRD-PARTY.md`](THIRD-PARTY.md)
  ⚠️ `web/public/data/` 里的词典表由 Unihan 派生，但**排序**借用了两处许可证未核实的
  语料频率；严格合规的再分发者请看 `THIRD-PARTY.md` §3 并自行重新生成。
