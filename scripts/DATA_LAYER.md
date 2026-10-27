# 笔画库 数据层 (契约 + 现状性能)

> 这份文件的用途：**数据结构可以被重写，但这些语义不能被悄悄改掉**。
> 任何改动数据存储/读取通路的会话，请先读完本文，再把「结论 / 数字 / 死胡同」填到最后一节。
> 最后更新：索引实验（`exp_datalayer/`，结论填在第 5 节）；第 1~4 节仍是空腔算法 + 中宫盒阶段的内容。

---

## 1. 现状：数据从哪来

```
DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"        # glyph_extend.py:3
dbs  = open(DUMP, encoding="utf-8").readlines()    # 模块级, import 时就执行 (L4-6)
```

- 每行格式：` name | ? | data`（`line.split(' | ')`，只用 `cols[0]`=名字、`cols[2]`=数据）
- 规模：**2,485,799 行 / 2,485,797 个字形**（实测，两次一致）
- `data` 是 `$` 分隔的字形串：`1|2|3|4|6|7` 开头是笔画，`99:...` 是引用，`0:9x` 是变换命令
- Web 端另有一份：`web/public/` 下 bundle 出来的 `glyphData: Map<name, data>`（`kageEngine.ts`），
  `renderSvg` 走这个 Map。**两端是两套独立的读取实现，必须语义对齐。**

## 2. 契约（不能改的语义）

### 2.1 `get_data(targets, datas=dbs, mode="single", order=None, exact=False)`

| 参数 | 语义 |
| --- | --- |
| `exact=False`（默认） | 名字是目标**子串**即命中，**后面的覆盖前面的 → 文件中最后一个命中胜出** |
| `exact=True` | ① 名字**完全相等**优先（同名取最后一个）；② 无精确名时取**名字最长**的子串命中 |

**为什么必须有两条**（这是被 bug 逼出来的，别再合并成一条）：

- `exact=False` 是**第一轮叶子查找**用的：`ids_anal` 传进来的是加过后缀的名字（`u670b-04`），
  该变体不存在时要**退化成本体** `u670b`。这条退化是特性，不是缺陷。
- `exact=True` 是**拆笔画递归**（`unfold` 里对 `99:` 引用的递归）用的：引用名是库里的真实名字，
  走子串会**串味**。实测：鹿-05 引用 `u2ff1-cdp-88b4-u6bd4`（库里有 10 笔），
  按"行号最大"拿到的是 `u6bd4-j`（比，5 笔）→ 展平后少 5 笔，`⿸鹿` 的容器丢中间。
  改成精确优先后 13 笔，与 web 编辑器一致。

### 2.2 `mode="candidate"`

收集同一字头（`name.split("-")[0]`）的全部变体，交给 `fallback_candidate(entries, order)` 排序。
**不要在数据层重新实现这套排序**，直接调那个函数。

### 2.3 `unfold(name, glyph, datas, mode, order, exact=False)`

顶层调用 `exact=False`；**递归那一行固定 `exact=True`**（当前实现里是硬编码的）。
改数据层时如果引入了自己的查找函数，这两条都得跟着区分。

### 2.4 `preview` 会**接管并破坏**模块状态

```python
# web/preview/preview.py
_INDEX = {name: (行号, data)}        # 启动时自己扫一遍 dump 建索引
glyph_extend.get_data = _fast_get_data   # 覆盖原函数
glyph_extend.dbs.clear()                 # 清空原列表省内存
```

所以：

- 任何**在 preview 之后**还去读 `glyph_extend.dbs` 的代码会读到空列表（我踩过一次）；
- 任何给 `get_data` **加新参数**的改动，必须同步 `_fast_get_data`（它用 `**kw` 接住未知参数并打印警告，
  不会报错，只会静默忽略 —— 等于悄悄走旧逻辑）；
- `_fast_get_data` 还要复刻 `exact=True` 的那条路径（当前已实现）。

### 2.5 其他读取入口

| 入口 | 位置 | 说明 |
| --- | --- | --- |
| `name_lines()` | `ids_anal.py` | 字形名 → 行号的**精确**索引，首次调用构建一次（惰性） |
| `_INDEX` / `_head_names` | `web/preview/preview.py` | 同上 + 按字头分组（candidate 模式用） |
| `resolveRef(refName)` | `web/src/editor/kageEngine.ts` | web 端内部引用解析：精确 → **最长子串**（必须与 2.1 的 `exact=True` 一致） |
| 后缀退化 | `web/src/editor/kageEngine.ts` | web 端第一轮叶子查找的退化（对应 2.1 的 `exact=False`） |

**单一真相来源**：内部引用解析以 `glyph_extend.get_data(exact=True)` 为准，web 必须复刻；
叶子后缀退化以 `get_data(exact=False)` 为准。两边已经因为不一致踩过三次（缝合拉伸、exact 优先、迷你库模拟）。

## 3. 性能现状（实测，同机不同负载会有 ±2 倍波动）

| 操作 | 耗时 | 备注 |
| --- | --- | --- |
| `import glyph_extend`：readlines 2.48M 行 | **1.1 ~ 1.6 s** | 一次性 |
| 紧跟的建索引（preview / name_lines） | **2.1 ~ 4.5 s** | 2.48M 次 dict 写入 |
| 就绪总时间（preview，含导入腔体等模块） | **4.4 ~ 7.5 s** | 冷启动 |
| `_fast_get_data` 单次查询（索引后） | **0.065 ms** | docstring 里记录的实测值 |
| 裸 `get_data` 单次查询（线性扫 dbs） | **0.5 ~ 38 s** | 名字在文件越靠后越慢 |
| `ids_anal.IDS(...)` 单次（裸函数，无索引） | **8 ~ 21 s** | 一次展平要做几次 `get_data` |
| `preview` 一次渲染 | **≈ 12 ms** | 索引已建好时 |
| `web renderSvg` | **0 ~ 4 ms** | Map 命中；冷启动 1.1 s（解析 bundle） |
| `layout_ref_gen.py` 81 个用例（借 preview 索引） | **≈ 11.5 s** | 改造前单个 IDS 就要 8~21 s |
| `return_bone(u9e7f-05)` 一次展平（eval 已换掉后） | **0.52 ms** | 13 笔 |
| `return_bone(u56fd)` / `return_bone(u7ca4)` | **0.89 / 1.63 ms** | 复杂度随笔画数上升 |
| `ids_anal.IDS(...)` 单次（索引 + eval 已换掉后） | **≈ 19.6 ms** | 腔体枚举占大头 |

内存：`_INDEX` 存 `name → (行号, data 字符串)`，data 是原文本切片；`dbs` 被 `clear()` 后
只剩索引里的字符串。**改造时请一并记录内存峰值**（现在没有量过，这是空白）。

> ✅ 已落地（2026，本次）：把 `glyph_extend` / `stroke_outer.stroke_point` / `ids_anal` 里
> 读路径上的 `eval()` 全换成 `float(s) if '.' in s else int(s)`（`glyph_extend._num`）。
> A/B 实测（同进程把 `_num` 临时换回 `eval`）：
>
> ```
> return_bone(u9e7f-05)  0.52 ms  vs  eval 8.71 ms   16.8x
> return_bone(u56fd)     0.89 ms  vs  eval 11.50 ms  12.9x
> return_bone(u7ca4)     1.63 ms  vs  eval 20.64 ms  12.7x
> 纯字段解析 160k 次:     118 ms  vs  eval 4955 ms    42x
> 端到端单次 IDS:        19.6 ms vs  eval 26.0 ms     1.3x  ← 腔体枚举已成大头
> ```
>
> 注意：整数串要用 `int()`（保留 int 语义，否则 `"54"` 会输出成 `"54.0"`，改变笔画串文本）；
> 类型码用 `int(tok)`。`stroke_outer.stroke_point` 里是内联的同款表达式，没有走 `_num`。

> ⚠ 补一条与数据层无关、但比数据层大得多的账（2026 索引实验实测，详见第 5 节 ③）：
> **`unfold` 里约 67% 的时间花在 `eval()` 上**（一次单字 unfold 4.16 ms 里约 2.8 ms），
> 换成 `int()/float()` 快路径可快 5.6~6.9 倍且输出逐字不变。也就是说：
> 数据层再怎么优化，unfold 的天花板由几何代码里的 `eval` 决定。

## 4. 已知的坑（改造时容易踩）

1. **`dbs` 被 clear** —— 见 2.4。
2. **`_fast_get_data` 的 `**kw` 静默忽略** —— 新增参数必须显式实现。
3. **`line.split(' | ')`** —— 分隔符是**空格竖线空格**，不是单纯的 `|`。
4. **同名多条**：库里存在同名字形（`readlines` 比索引少 2 条，说明有重复/空行），
   "最后一个胜出"依赖**文件顺序**。若新结构丢掉了行序，这条语义会变。
5. **`data` 里可能有多余空白**（`cols[2].strip()` 是必要的）。
6. **`.blend`/`.pyc` 之外不要引入需要联网或编译的依赖** —— 实验脚本要能直接 `python xxx.py` 跑。

## 5. 结论 / 数字 / 必须保留 / 死胡同 / 回滚（已填：索引实验）

> 本次填写依据：`D:\2026harucpp\exp_datalayer\`（索引实验，未改动任何读取通路）。
> 取证文件：`RESULTS.md`（数字总表）、`verify_result.json`（对拍）、`bench_result.json`、
> `ab_unfold.json`、`fastpath_result.json`、`depth.json`、`scan_numeric.json`。

```
结论:
  「字头索引表」和「引用直指列」两条都成立，都可以做 —— 但**它们不是 unfold 的瓶颈**：
  做完之后一个字形的 unfold 只快 0.85% ~ 1.4%。真正值钱的收益在别处（冷启动/内存/全库批处理）。
  · ① 字头索引表：成立，而且比预想的更省 —— dump 里名字按码位**全局有序**（实测），
    同一字头的行天然是**连续区间**，所以这张表只要 491,785 个 (字头, 首行) 对，
    二分定位即可，不需要哈希字典。收益是替掉 preview 里那张 49 万条、冷建 1.9~2.2 s、
    约 40 MB 的 _HEAD_INDEX；**单次 candidate 查询速度打平**（耗时被 fallback_candidate 吃掉）。
  · ② 引用直指列：成立。把 3.26M 条 99 引用的目标行号在建表时算好（int32，
    ref_targets 13.0 MB + ref_off 9.9 MB），递归里不再碰名字空间。
    收益：全库引用校验 43.7 s → 0.82 s；全库递归深度分布 1.64 s 算完（以前算不动）。
    对单个 unfold 的收益：0.85%（单字）~ 1.4%（最深层 60 个）。
  · ③ 顺带发现（比①②都重要）：unfold 里 **67% 的时间是 eval()**。
    把 eval 换成 int()/float() 快路径（全库 37,808,709 个数值字段 100% 匹配
    `-?\d+(\.\d+)?`，兜底仍是 eval，所以 85 个非数值字段的行为不变），
    输出逐字不变（435 个字形对拍 0 处不同），端到端快 **5.6 ~ 6.9 倍**。
    下一步该动的是这里，不是数据层。

数字: (本机实测; 口径见下方「计时口径」)
  加载:  裸 import glyph_extend 1.09~1.16 s / peak 487 MB
         preview 补丁    +2.58 s 建 _INDEX / peak 1179 MB（dbs.clear() 后 714 MB）
         新结构 RamDB    33~41 s 建表（3/4 花在预解析引用）/ peak 704 MB / rss 665 MB
         新结构 DiskDB   0.023 s 打开索引（mmap）/ peak 69 MB / rss 62 MB / 索引文件 223 MB
  单次查询(µs):  精确命中   610000(裸线性) | 1.3(preview) | 0.9(哈希) | 3.2(mmap二分)
                 最长子串   ——           | 13.3         | 15.7       | 69.1
                 叶子退化   ——           | 17.9         | 18.1       | 72.3
  candidate:    字头表一次性 1.9~2.2 s(preview 字典) vs 0(区间表)
                u4eba(42变体) 0.04~0.13 ms vs 0.06~0.20 ms —— 打平
                u2ff0(38221变体) 329~355 ms vs 328~382 ms —— 都被 fallback_candidate 吃掉
  全库遍历:     3.26M 条引用 按名字解析 43.7 s(抽样外推) | 读引用列 0.82 s | 裸线性 ~23 天(外推)
                全库递归深度分布 1.64 s(只有靠引用列才可能) | 37.8M 字段体检 61 s
  unfold 一个字: 裸线性 u4e2d 1.16 s / u9e7f 1.15 s / ub2aa(39笔) 5.05 s
                索引后同三个字形 0.70 / 1.68 / 5.28 ms —— **约 680~1660 倍**
                索引后均值: 单字 4.16 ms(4.79 节点) / 全库最深 100 的均值 10.40 ms(13.4 节点)
  内存峰值:     487 MB(裸) | 1179 MB(preview) | 704 MB(RamDB) | 69 MB(DiskDB)
  计时口径:     ① 每个测点一个独立进程;
                ② 本机持续负载约 1 秒后 CPU 会降频到 1/8 左右(见 exp_datalayer/diag_timing.py,
                   那里 cpu/alloc/unfold 三项一起变慢), 所以绝对耗时只有在"进程第一件事"
                   测才有效 —— 上面的数都是这么取的;
                ③ 比值一律来自**同一降频状态下的交错 A/B**, 不受降频影响。
                跨时段仍有 ±倍数波动, 只看量级与数量级。

  附: 对第 3、4 节的两处事实修正(实测, 与改造无关)
    · 第 4 节第 4 条「库里存在同名字形」——**没有**。2,485,797 个名字全部唯一;
      readlines 比索引少的那 2 条是 `len(cols) < 3` 的坏行, 不是重复。
    · 第 3 节「裸 get_data 单次查询 0.5~38 s」——本机实测 **≈0.61 s**
      (5 次独立进程 598~617 ms; 降频状态下约 1.2 s),
      而且与名字位置**无关**(那个循环没有 break, 每次都扫完 248 万行)。
    · 附: 全库有 53 条引用的部件名解析不出来(32 个不同名字, 如 lp_lpy-00001460)。

必须保留: (逐条勾对第 2 节; 实测对拍见 exp_datalayer/verify.py, 期望 ALL_PASS = True)
  · 2.1 两条查找语义 —— 保留, 并逐条对拍:
        子集(4010 行保序小库)上直接拿**原版线性 get_data 当 oracle**, 19,306 个目标
        × exact∈{False,True} 全部一致; 全库上 4 个实现(哈希/二分/preview/mmap)互校
        12,156 个目标也全部一致。
        ★ 一条容易被忽略的等价性: 名字全局有序时「文件里最后一个命中」==
          「字典序最大的命中」。二分实现全靠它, 已实测成立(248 万行 0 逆序)。
  · 2.2 candidate —— 保留, 直接调 glyph_extend.fallback_candidate, 没有二次实现;
        60 个字头 × 3 种 order 的返回元组逐个相等。
  · 2.3 unfold 顶层 exact=False / 递归 exact=True —— 保留。free_unfold 顶层走 find(name, exact),
        递归直接读引用列(等价于 exact=True 的结果, 3.26M 条已对拍)。
  · 2.4 preview 会接管并破坏模块状态 —— 未触碰。实验只在 verify/bench 自己的进程里
        临时 monkeypatch get_data, 跑完不改 glyph_extend 的任何模块状态。
  · 2.5 其他入口(name_lines / _INDEX / _head_names / resolveRef / web 后缀退化) —— 未触碰。
  · 4.1 dbs 被 clear —— 实验里不依赖 dbs, 不受影响。
  · 4.2 _fast_get_data 的 **kw 静默忽略 —— 未改签名, 不受影响。
  · 4.3 ' | ' 分隔符 —— 保留。
  · 4.5 data 可能有多余空白 —— 保留 cols[2].strip() / data.strip("$")。
  · 4.6 不引入联网或编译依赖 —— 全部纯 stdlib(array / mmap / bisect / json)。
  变更项(仅限实验层, 未进主通路):
    · 引用列把 exact=True 的解析结果**冻结**在索引里 —— 只对**同一份 dump** 有效,
      换 dump 必须重建; 这一条写进回滚说明。

死胡同:
  · 「只要把查找做成 O(1)，unfold 就会快很多」——**不成立**。实测一次 unfold 只有
    4.8(单字)~13.4(最深层) 个节点, 查找总共 36~241 µs, 占 4.16/10.40 ms 的
    0.85%~1.4%(中位数甚至跨零, 单个字形量不出差别)。索引在「从无到有」那一层是决定性的
    (610 ms → 0.9~20 µs, 约 5~6 个数量级; unfold 一个单字 1.16 s → 0.70 ms),
    再往下优化没有空间。
  · 「二分表可以完全替代哈希表」——能跑通且省 200~300 MB, 但每次查询慢 3.5~4.5 倍
    (叶子退化 18.1 µs → 72.3 µs), 全库批处理会被放大。只在「零解析启动 + 62 MB 常驻」
    这个场景下划算(DiskDB 就是这么用的: 启动 0.023 s)。
  · 「给 candidate 建字头字典能加速 candidate」——不成立。candidate 的耗时在
    fallback_candidate 自己: 38,221 个变体的 u2ff0 一律 330~380 ms, 两种结构一模一样。
    真想快, 要在建表时把变体标识符(名字第二段)也预先切好。
  · 踩过的坑(不是想法本身, 是实现的坑): 第一版前缀游走把「走到的前缀长度」当成
    「命中名的长度」, 于是 `u2ff0-u866b-u95`(本身是更长名字的前缀)在 exact=True 下
    选中 5 字符的 u2ff0 而不是同样 5 字符但行号更大的 u866b —— 小库对拍没覆盖到,
    **是全库互校抓到的**。以后加任何索引, 全库互校那一层不能省。
  · 现状 bug(非本次引入, 只记录): 全库 85 个非数值字段里 ——
    46 个在 `0:` 注释行(如 `0:irgn2267`), unfold 走到 `_eval(Lp[1])` 会 NameError;
    28 个只是空栏(unfold 先归一成 "0", 无害); 4 个在 `999:` 畸形笔种行(整条被忽略);
    7 个(`s` / `-` / `0p` / `116p`)会让 unfold 当场崩。
    实测 hkcs_m21565 / hkcs_m215dc / hkcs_m21c81 / hkcs_m2282c / hkcs_m24662 这 5 个字形
    现在就是崩的。要修的话, 在 `elif _eval(Lp[0]) == 0 and _eval(Lp[1]) in [97,98,99]`
    那一行先把非数值栏挡掉即可。
    另有 19 个前导零字段(`08`/`00`/`-08`): eval 会 SyntaxError, int() 不会,
    所以换 eval 快路径时这 19 个字段是唯一的行为差异点。

回滚:
  · 不需要回滚 —— 什么都没动。全部代码在 `D:\2026harucpp\exp_datalayer\`,
    `scripts/glyph_extend.py` / `web/preview/preview.py` / `web/src/**` 一行未改;
    verify.py / bench.py 里的 monkeypatch 只作用于它们自己的进程。
  · 若要把实验结构接进主通路, 入口是 `exp_datalayer/fastdb.py`:
      RamDB.get_data / RamDB.find / DiskDB.get_data 与 glyph_extend.get_data **同签名**,
      所以切回旧路径 = `glyph_extend.get_data = 原来的函数`(等价于不装 preview 补丁)。
    RamDB 用 `fastdb.build()`; DiskDB 用 `fastdb.DiskDB()`(读 ./index/)。
    unfold 侧对应 `exp_datalayer/free_unfold.unfold_rows(db, name)`,
    它和 glyph_extend.unfold 输出逐字一致(720 个字形对拍 0 差异)。
  · 索引文件随时可以删掉重建: `python fastdb.py --build`(33~41 s, 223 MB)。
    **换 dump 必须重建**, 否则引用列指向旧行号(这是这个结构唯一新增的失效模式)。
```

