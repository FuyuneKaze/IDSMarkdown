# 第三方数据与许可（THIRD-PARTY）

本仓库的**源代码**按 [MIT](LICENSE) 授权。
下列**数据/字体**不属于本项目，各有自己的来源与授权，请在使用前阅读本节。

> 一句话给 MIT 使用者：**代码随便用；`web/public/data/` 里那几张表是从 Unihan 派生的，
> 但它们的「排序」借用了两处许可证未核实的语料频率，见 §3。严格合规的再分发者
> 应当自行从原站获取语料、用 `scripts/` 里的脚本重新生成。**

---

## 1. 字形数据（运行时获取，不入库）

| 数据 | 来源 | 许可 | 说明 |
| --- | --- | --- | --- |
| GlyphWiki 字形（KAGE 笔画） | [glyphwiki.org](https://glyphwiki.org/) / [dump 下载](https://zhs.glyphwiki.org/wiki/GlyphWiki) | GlyphWiki 字形数据可自由使用（社区惯例；具体以其站点声明为准） | **不入库**。本项目通过 `https://glyphwiki.org/api/glyph?name=…` 运行时按需获取（`web/src/editor/glyphSource.ts`） |
| IDS 表意文字序列 | [cjkvi-ids](https://github.com/cjkvi/cjkvi-ids)（源自 [CHISE](http://www.chise.org/)） | **GPLv2** | **不入库**。需要者自行下载；本仓库不含该数据，故不影响本仓库的 MIT 授权 |
| Unicode Han 数据库（Unihan） | [Unicode UCD](https://www.unicode.org/Public/UCD/latest/ucd/) | [Unicode License v3](https://www.unicode.org/license.txt) | 允许衍生与再分发，须保留版权声明 |

## 2. 字体（不入库，用户自备）

| 字体 | 用途 | 状态 |
| --- | --- | --- |
| MetaHan Myungjo (`mthmyung.ttf`) | 古谚文显示 | ⚠️ 来源 <http://ko.cheonhyeong.com/fonts/mthmyung.ttf>，许可未核实 → **不入库** |
| Noto Serif Tangut | 西夏文 | OFL 1.1 → 可分发（需附 `OFL.txt`，不得改字体名） |
| 說文小篆（Unicode 字表字形） | 小篆显示 | 属 Unicode 数据/字形，体积大 → **不入库** |

## 3. ⚠️ `web/public/data/` 里那几张表的排序问题（重要）

| 文件 | 内容 | 怎么来的 |
| --- | --- | --- |
| `jap_cjk.json` | 日语音读/训读 → 汉字 | `scripts/unihan.py` 从 **Unihan** `kJapaneseOn`/`kJapaneseKun` 抽取并**按频率重排**（`data/dictionary/freq/resorted.py`） |
| `hangul_cjk.json`、`extend_hangul_map.json` | 韩语音 → 汉字 | `scripts/hangul.py` 从 Unihan 派生 + 频率重排 |
| `viet_cjk.txt` | 越南语词 → 喃字 | 从 Unihan 派生 + 频率重排 |
| `ipa_keymap.json` | IPA 键位映射 | `scripts/extract_ipa.py`（与上表无关，无此问题） |

**衍生关系**：这些表的内容主体是 **Unihan 数据**（属 Unicode License，允许再分发），
本项目只是**按频率给字表排了序**。排序信息来自：

1. **大地数据库**（日韩越字频，原站 <http://www.xn--cesp9b.net/>）—— 原站声明
   「本语料库语料文本数据全面公开」「毫无保留地提供了我们语料库中的全部语料的文本数据」，
   但**未见明确的开放许可证标识**；
2. **morphoboid / labri 的 Nôm 训练集**（<https://morphoboid.labri.fr/ihr-nom.html>）——
   许可证状态**未核实**（原链接目前无法访问）。

因此：

- 这些表里**不包含语料的原文文本**，只包含「字 → 读音」的映射与顺序；
- 但**顺序本身来源于上述语料**。若你在欧盟等承认「数据库权利」的司法辖区再分发，
  可能需要注意；本项目的立场是**如实记录来源、不宣称拥有该排序**。
- **严格合规的替代做法**：删掉 `web/public/data/*` 中除 `ipa_keymap.json` 外的文件，
  按 `scripts/unihan.py` / `scripts/hangul.py` / `data/dictionary/freq/resorted.py`
  用你自己合法获得的语料重新生成。

## 4. 引擎代码

| 组件 | 来源 | 许可 |
| --- | --- | --- |
| KAGE 渲染引擎（`kage-bundle.js`） | [kurgm/kage-engine](https://github.com/kurgm/kage-engine)、[kamichikoichi/kage-engine](https://github.com/kamichikoichi/kage-engine) | MIT（原作者的许可；再分发时请保留其版权头） |
| 本仓库其余代码 | 本项目作者 | MIT（见 `LICENSE`） |

## 5. 如何重新生成 §3 的数据

```powershell
# 需要: Unihan 的解压文件 (Unihan_Readings.txt 等), 以及你自己合法获得的频率语料
python scripts/unihan.py        # → jap_cjk.json
python scripts/hangul.py        # → hangul_cjk.json / extend_hangul_map.json
python data/dictionary/freq/resorted.py   # 按频率重排
```
