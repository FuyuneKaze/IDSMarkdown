# -*- coding: utf-8 -*-
"""
IDS 批量预览工具
================

用途: 改完 ids_anal.py 的算法后, 一次性查看它在多个部件组合上的合成效果。

链路 (与你的脚本完全一致):
    IDS 字符串  →  ids_anal.IDS(op, [部件名])  →  kage_contour.extract_one()
                →  contours  →  前端画 SVG

性能处理:
    glyph_extend 在 import 时会 readlines 整个 dump, 且 get_data 是线性扫描
    (每次查询 O(250万行))。本工具在启动时把 dump 建成 name→data 索引,
    并替换 glyph_extend.get_data 为 O(1) 查表, 之后每次合成都是毫秒级。

算法热更新:
    每次请求都会 importlib.reload(ids_anal), 所以改完 ids_anal.py
    只需在页面上点"重新渲染"(或刷新), 不用重启本服务。

用法:
    python preview.py            # 启动, 浏览器打开 http://127.0.0.1:8765
    python preview.py --port 9000
"""
'''
⿰亻惑    
⿰氵工
⿰木衣
⿰口口
⿰亻尔
⿱艹朋
⿱勿心
⿱喵灬
⿰田鼻
⿰田自
⿰岁月
⿰田刂
⿰麦将
⿰口鷄
⿲忄束负
⿳艹一灬
⿸厂口
⿸疒粤
⿴囗口
⿸𠂆氐
⿸鹿丶
⿹土口
⿺鬼口
⿺老口
⿽土口
⿶门㐅
'''
import sys
import os
import io
import json
import time
import types
import importlib
import contextlib
import traceback
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# Windows 控制台默认 GBK, 显式用 UTF-8 输出, 否则中文日志乱码
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPTS = r"D:\2026harucpp\scripts"
DUMP = r"D:/KAGE_GLYPH/dump_newest_only.txt"
HOST = "127.0.0.1"
PORT = 8765

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

_T0 = time.time()


def log(msg):
    print(f"[{time.time()-_T0:7.2f}s] {msg}", flush=True)


# ============================================================
# 1. 启动: 建索引 + 加速 glyph_extend
# ============================================================
log("导入 glyph_extend (会读一次 dump, 约 10s) ...")
import glyph_extend  # noqa: E402  这个 import 本身会 readlines 整个 dump

log(f"  读入 {len(glyph_extend.dbs):,} 行, 开始建索引 ...")
# name -> (行号, data)。必须全量建索引: 字形名首字母不只是 u,
# 还有 h/l/s/j/k/d/z/e/t... (约 198 万条), 只留 " u" 会漏掉大半。
_INDEX = {}
for _ln, _line in enumerate(glyph_extend.dbs):
    _cols = _line.split(" | ")
    if len(_cols) < 3:
        continue
    _INDEX[_cols[0].strip()] = (_ln, _cols[2].strip())
log(f"  索引 {len(_INDEX):,} 个字形")

# 释放原始行列表 (省几百 MB)。必须用原地 clear():
# unfold/return_bone 的默认参数绑定的是同一个 list 对象, 只有原地清空
# 才真正释放内存。这样安全是因为下面已把 get_data 换成索引查表。
glyph_extend.dbs.clear()


_HEAD_INDEX = None


def _head_names(head):
    """同一"字头"(name.split('-')[0]) 的全部字形名, 按文件行序。

    mode="candidate" 通路要用。只存名字引用(不复制数据), 按需懒构建。
    """
    global _HEAD_INDEX
    if _HEAD_INDEX is None:
        m = {}
        for nm in _INDEX:
            m.setdefault(nm.split("-")[0], []).append(nm)
        _HEAD_INDEX = m
        log(f"  字头索引 {len(_HEAD_INDEX):,} 个")
    lst = _HEAD_INDEX.get(head)
    if not lst:
        return []
    return sorted(lst, key=lambda n: _INDEX[n][0])


def _fast_get_data(targets, datas=None, mode="single", order=None, exact=False, **kw):
    """精确复刻 glyph_extend.get_data 的三条通路, 但用索引加速。

    mode="single" (原语义):
        for line in datas:
            cols = line.split(' | ')
            if len(cols) < 3: continue
            name = cols[0].strip()
            if name in targets:          # ← 子串包含! 不是相等
                data = cols[2].strip()   # 反复覆盖 → 最后一个匹配胜出

        "name in targets" 是子串判断, 所以查询 "u670b-04" 在该变体不存在时,
        会自动退化成命中本体 "u670b" 等更短子串 —— 相当于内建 fallback。
        本实现等价地枚举 targets 的所有子串取"行号最大"的匹配, 逐字一致
        (14 个含缺失变体的用例对照, 0 处不一致), 每次查询 0.065 毫秒
        (原版 0.5~38 秒)。

    mode="candidate" (新增通路):
        收集同一字头的全部变体 (按文件行序) 交给 glyph_extend.fallback_candidate
        按 order 挑 —— 直接调你自己的函数, 不做二次实现以免语义漂移。
        返回值与 get_data 一致 (可能是 (data, fix) 或 (name, data) 元组,
        unfold 那边取 [0], 保持原样)。
    """
    if kw:
        print(f"[preview] get_data 收到未知参数 {sorted(kw)}, 已忽略 —— "
              f"请在 preview._fast_get_data 里同步 glyph_extend 的新签名",
              flush=True)

    if mode == "candidate":
        head = targets.split("-")[0]
        ents = [(nm, _INDEX[nm][1]) for nm in _head_names(head)]
        return glyph_extend.fallback_candidate(ents, order)

    if mode != "single":
        return None

    # exact=True (拆笔画递归): 精确名优先; 否则取"名字最长"的子串命中 (同长取行号大)
    if exact and targets in _INDEX:
        return _INDEX[targets][1]

    best = -1          # 老语义: 行号最大
    best_len = -1      # 精确语义: 先比子串长度, 再比行号
    bd = ""
    n = len(targets)
    for i in range(n):
        for j in range(i + 1, n + 1):
            hit = _INDEX.get(targets[i:j])
            if hit is None:
                continue
            if exact:
                if (j - i, hit[0]) > (best_len, best):
                    best_len, best, bd = j - i, hit[0], hit[1]
            elif hit[0] > best:
                best = hit[0]
                bd = hit[1]
    return bd


glyph_extend.get_data = _fast_get_data

log("导入 ids_anal / kage_contour / stroke_outer / cavity / central_box ...")
import kage_contour    # noqa: E402
import stroke_outer    # noqa: E402
import cavity          # noqa: E402  空腔枚举 (§6.6), ids_anal 依赖它
import central_box_old     # noqa: E402  内部件"内容基准框", fit_into 用它缩放
import ids_anal        # noqa: E402
from kage_contour import extract_contours, ch_uni  # noqa: E402
log("就绪。")


# ============================================================
# 热重载: 改完用户模块不用重启服务
# ============================================================
_MTIME = {}


def _reload_changed():
    """按文件 mtime 重载被改过的模块 (依赖在前, ids_anal 在后)。

    以前只 reload(ids_anal), 于是改 stroke_outer.py / kage_contour.py
    不会生效 —— 它们已在 sys.modules 里, reload 不会带上。

    glyph_extend 特殊: 重载它会重新 readlines 整个 dump, 并覆盖掉本工具
    安装的 get_data 补丁, 所以重载后必须立刻重装补丁并再次清空 dbs。
    """
    for mod in (stroke_outer, cavity, central_box_old, kage_contour, ids_anal, glyph_extend):
        p = getattr(mod, "__file__", None)
        if not p:
            continue
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        prev = _MTIME.get(p)
        _MTIME[p] = mt
        if prev is None or prev == mt:
            continue                      # 首次记录 / 未改动
        try:
            importlib.reload(mod)
        except Exception as e:
            print(f"[preview] 重载 {mod.__name__} 失败: {e}", flush=True)
            continue
        if mod is glyph_extend:
            glyph_extend.dbs.clear()
            glyph_extend.get_data = _fast_get_data
        print(f"[preview] 已重载 {mod.__name__}", flush=True)


def _snap_boxes():
    """快照 ids_anal.LAST_BOXES —— 转成纯 float, 否则 numpy 值无法 JSON 序列化"""
    b = getattr(ids_anal, "LAST_BOXES", None) or {}
    def cv(x):
        return [float(v) for v in x] if x else None
    return {"components": [cv(x) for x in (b.get("components") or [])],
            "cavity": cv(b.get("cavity")),
            "candidates": [cv(x) for x in (b.get("candidates") or [])],
            "basis": cv(b.get("basis")),
            "outer": cv(b.get("outer"))}

# ============================================================
# 2. IDS 解析
# ============================================================
OPS = {chr(c) for c in range(0x2FF0, 0x3000)} | {chr(0x31EF)}
ARITY3 = {"⿲", "⿳"}
ARITY1 = {"⿾", "⿿"}


def _subtree_len(s, i):
    """返回从 i 开始的 IDS 子树占用的字符数; 非法返回 0"""
    if i >= len(s):
        return 0
    if s[i] not in OPS:
        return 1
    arity = 3 if s[i] in ARITY3 else 2
    p = i + 1
    for _ in range(arity):
        n = _subtree_len(s, p)
        if n == 0:
            return 0
        p += n
    return p - i


def parse_ids(s):
    """把 "⿰忄忽" 解析成 ("⿰", ["忄","忽"])"""
    s = s.strip()
    if not s:
        return None, None, "空字符串"
    if s[0] not in OPS:
        return None, None, f"必须以 IDS 操作符开头 (当前首字符 {s[0]!r})"
    op = s[0]
    arity = 3 if op in ARITY3 else 2
    if op in ARITY1:
        arity =1
    rest = s[1:]
    parts, i = [], 0
    while i < len(rest) and len(parts) < arity:
        n = _subtree_len(rest, i)
        if n == 0:
            return None, None, f"部件不完整 (位置 {i})"
        parts.append(rest[i:i + n])
        i += n
    if len(parts) != arity:
        return None, None, f"{op} 需要 {arity} 个部件, 只得到 {len(parts)} 个"
    if i < len(rest):
        return None, None, f"尾部有多余字符: {rest[i:]!r}"
    return op, parts, None


_SUFFIXES = [f"-{i:02d}" for i in range(1, 21)]


def variant_hint(names):
    """列出每个部件实际有哪些位置变体。

    用途: 当 IDS() 抛异常时, 帮你立刻区分是"数据缺失"还是"算法问题"。
    典型情况: 部件缺少所需后缀 (如 ⿱ 的下部件需要 -04 但库里没有),
    glyph_extend.return_bone 会返回空串, 随后 unfold 里 eval("") 抛 SyntaxError。
    """
    lines = []
    for n in names:
        have = [s for s in _SUFFIXES if _INDEX.get(n + s)]
        base = "有" if _INDEX.get(n) else "无"
        lines.append(f"      {n}: 本体={base}  变体="
                     + (" ".join(have) if have else "无"))
    return "  该部件在库中的可用变体:\n" + "\n".join(lines)


# ============================================================
# 3. 合成 + 轮廓提取
# ============================================================
def synth_batch(ids_list):
    """批量合成。

    先把每个 IDS 都过一遍 ids_anal.IDS() 得到 KAGE 数据, 收集齐之后
    只调用一次 node 提取轮廓 (extract_contours 支持批量), 避免 N 次 subprocess。

    返回 [{ids, contours, info, error, names, log}, ...]
    """
    out = [{"ids": s, "contours": None, "info": None, "error": None} for s in ids_list]

    # 按 mtime 重载被改过的用户模块 → 改完 ids_anal / stroke_outer /
    # kage_contour 都立即生效, 不用重启服务
    _reload_changed()

    pending = []  # 已成功合成、待提取轮廓的项
    for o, s in zip(out, ids_list):
        op, parts, err = parse_ids(s)
        if err:
            o["error"] = err
            continue
        o["op"] = op

        nested = [p for p in parts if p in OPS]
        if nested:
            o["error"] = f"暂不支持嵌套部件 ({nested[0]}) — ids_anal.IDS 只接受单字符部件"
            continue

        names = [ch_uni(p) for p in parts]
        o["names"] = names
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                glyph = ids_anal.IDS(op, names)
            o["boxes"] = _snap_boxes()      # 本次实际用到的包围盒
        except Exception as e:
            o["boxes"] = _snap_boxes()      # 出错时也快照, 方便看算到哪一步
            o["error"] = (f"IDS() 异常: {type(e).__name__}: {e}\n"
                          + variant_hint(names) + "\n"
                          + traceback.format_exc(limit=3))
            o["log"] = buf.getvalue()
            continue

        if not glyph:
            o["error"] = ("IDS() 没有返回结果。常见原因:\n"
                          f"  ① ids_anal.IDS 未实现操作符 {op}\n"
                          "  ② 部件缺少所需后缀的变体 (见下)\n"
                          + variant_hint(names))
            o["log"] = buf.getvalue()
            continue

        o["_glyph"] = glyph
        pending.append(o)

    # ---- 一次 node 调用提取全部轮廓 ----
    if pending:
        try:
            rs = extract_contours(
                [{"name": f"_s{k}", "data": o["_glyph"]} for k, o in enumerate(pending)]
            )
        except Exception:
            err = "轮廓提取失败:\n" + traceback.format_exc(limit=3)
            for o in pending:
                o["error"] = err
            rs = []
        for o, r in zip(pending, rs):
            if r.get("error"):
                o["error"] = r["error"]
                continue
            cs = r.get("contours", [])
            if not cs:
                o["error"] = "轮廓为空"
                continue
            o["contours"] = cs
            o["info"] = {
                "names": o.get("names"),
                "op": o.get("op"),
                "n_contours": len(cs),
                "n_points": sum(len(c) for c in cs),
            }

    for o in out:
        o.pop("_glyph", None)
    return out


# ============================================================
# 4. HTTP 服务
# ============================================================
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静音

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, HTML_PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/render":
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            items = payload.get("ids", [])
        except Exception as e:
            self._send(400, json.dumps({"error": str(e)}), "application/json")
            return

        clean = [(raw or "").strip() for raw in items]
        clean = [s for s in clean if s]

        t0 = time.time()
        try:
            out = synth_batch(clean)
        except Exception:
            err = traceback.format_exc(limit=5)
            out = [{"ids": s, "contours": None, "info": None, "error": err}
                   for s in clean]
        total = round((time.time() - t0) * 1000)
        body = json.dumps({"results": out, "total_ms": total},
                          ensure_ascii=False)
        self._send(200, body, "application/json; charset=utf-8")


# ============================================================
# 5. 前端页面
# ============================================================
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>IDS 批量预览</title>
<style>
  :root{
    --bg:#1b1b1f; --panel:#232329; --line:#37373f; --fg:#e6e6ea;
    --dim:#9a9aa6; --accent:#7cb3ff; --err:#ff7b72; --ok:#7ee787;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);
       font:14px/1.6 "Segoe UI","Microsoft YaHei",system-ui,sans-serif}
  header{padding:14px 18px;border-bottom:1px solid var(--line);
         display:flex;gap:14px;align-items:center;flex-wrap:wrap}
  h1{margin:0;font-size:15px;font-weight:600;letter-spacing:.3px}
  .spacer{flex:1}
  .hint{color:var(--dim);font-size:12px}
  main{display:flex;gap:16px;padding:16px;align-items:flex-start;
       flex-wrap:wrap}
  .left{flex:0 0 330px;position:sticky;top:16px}
  .right{flex:1;min-width:420px}
  textarea{width:100%;height:260px;resize:vertical;background:var(--panel);
    color:var(--fg);border:1px solid var(--line);border-radius:8px;
    padding:10px 12px;font:13px/1.7 ui-monospace,Consolas,monospace;
    outline:none}
  textarea:focus{border-color:var(--accent)}
  .row{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
  button{background:var(--accent);color:#10131a;border:0;border-radius:7px;
    padding:8px 14px;font-weight:600;cursor:pointer;font-size:13px}
  button.ghost{background:transparent;color:var(--fg);border:1px solid var(--line);
    font-weight:500}
  button:disabled{opacity:.5;cursor:default}
  label.chk{color:var(--dim);font-size:12px;display:flex;gap:5px;align-items:center;
    cursor:pointer}
  .status{margin-top:10px;color:var(--dim);font-size:12px;min-height:18px}
  .grid{display:grid;gap:14px;
    grid-template-columns:repeat(auto-fill,minmax(215px,1fr))}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
    padding:10px;display:flex;flex-direction:column;gap:8px}
  .card .head{display:flex;justify-content:space-between;align-items:baseline;
    gap:8px}
  .card .ids{font:600 16px/1.3 ui-monospace,Consolas,monospace;color:var(--fg);
    word-break:break-all}
  .card .meta{color:var(--dim);font-size:11px;white-space:nowrap}
  .card svg{background:#fff;border-radius:6px;display:block;width:100%;
    height:auto;aspect-ratio:1/1}
  .card .foot{color:var(--dim);font-size:11px;
    font-family:ui-monospace,Consolas,monospace;word-break:break-all}
  .card.err{border-color:#5d2b2b}
  .card .err{color:var(--err);font-size:12px;white-space:pre-wrap;
    word-break:break-word;max-height:150px;overflow:auto}
  details{font-size:11px;color:var(--dim)}
  details pre{white-space:pre-wrap;word-break:break-all;max-height:130px;
    overflow:auto;background:#1a1a1e;padding:6px;border-radius:5px;margin:6px 0 0}
  .empty{color:var(--dim);padding:34px;text-align:center;
    border:1px dashed var(--line);border-radius:10px}
</style>
</head>
<body>
<header>
  <h1>IDS 批量预览</h1>
  <span class="hint">走 ids_anal.IDS → kage_contour.extract_one → SVG</span>
  <span class="spacer"></span>
  <span class="hint" id="engine">引擎就绪</span>
</header>

<main>
  <div class="left">
    <textarea id="input" spellcheck="false"></textarea>
    <div class="row">
      <button id="go">渲染</button>
      <button class="ghost" id="auto">自动</button>
      <label class="chk"><input type="checkbox" id="fill" checked> 实心</label>
      <label class="chk"><input type="checkbox" id="boxes" checked> 包围盒</label>
      <label class="chk"><input type="checkbox" id="grid200" checked> 网格</label>
    </div>
    <div class="status" id="status">每行一个 IDS。改完 ids_anal.py 直接点"渲染"即可生效。</div>
  </div>
  <div class="right">
    <div class="grid" id="grid"></div>
  </div>
</main>

<script>
const $ = s => document.querySelector(s);
const inputEl = $('#input'), gridEl = $('#grid'), statusEl = $('#status');

const DEFAULT_IDS = [
  "⿰忄忽",
  "⿰氵工",
  "⿰木木",
  "⿰口木",
  "⿰亻尔",
  "⿱艹朋",
].join("\n");

try {
  const saved = localStorage.getItem("ids_preview_list");
  inputEl.value = saved || DEFAULT_IDS;
} catch (e) { inputEl.value = DEFAULT_IDS; }

inputEl.addEventListener("input", () => {
  try { localStorage.setItem("ids_preview_list", inputEl.value); } catch (e) {}
});

/* ---------- contours → SVG path (移植 draw_glyph.create_bezier_svg 逻辑) ---------- */
function contourToPath(contour) {
  const nums = v => (Math.round(v * 100) / 100);
  let d = "";
  let i = 0;
  while (i < contour.length) {
    const p = contour[i];
    if (!p || p[2] !== 0) { i++; continue; }
    const x = nums(p[0]), y = nums(p[1]);
    d += (d === "" ? "M" : "L") + x + " " + y;

    /* 收集紧随其后的控制点 (off=1) */
    let j = i + 1;
    const ctrls = [];
    while (j < contour.length && contour[j] && contour[j][2] === 1) {
      ctrls.push(contour[j]); j++;
    }
    if (ctrls.length && j < contour.length && contour[j] && contour[j][2] === 0) {
      const e = contour[j];
      if (ctrls.length === 1) {
        d += "Q" + nums(ctrls[0][0]) + " " + nums(ctrls[0][1]) +
             " " + nums(e[0]) + " " + nums(e[1]);
      } else {
        d += "C" + nums(ctrls[0][0]) + " " + nums(ctrls[0][1]) + " " +
                    nums(ctrls[1][0]) + " " + nums(ctrls[1][1]) + " " +
                    nums(e[0]) + " " + nums(e[1]);
      }
      i = j;
      continue;
    }
    i++;
  }
  return d ? d + "Z" : "";
}

/* 包围盒配色: components 按顺序循环取色; 空腔/外框各自专用色。
   盒由后端 ids_anal.LAST_BOXES 提供 —— 是各算符那次实际用到的盒,
   不是重新猜的(不同用途的盒故意不同: bbox 用 ifshrink=True,
   包围空腔用 ifshrink=False)。 */
const BOX_COLORS = ["#ff7b72", "#ffa657", "#d2a8ff", "#79c0ff"];
const CAVITY_COLOR = "#3fb950";
const CAND_COLOR = "#6e7681";
const CAND_ALT_COLOR = "#d29922";
const BASIS_COLOR = "#58a6ff";
const OUTER_COLOR = "#8b949e";

function sameBox(a, b) {
  return a && b && Math.abs(a[0]-b[0]) < 0.01 && Math.abs(a[1]-b[1]) < 0.01 &&
         Math.abs(a[2]-b[2]) < 0.01 && Math.abs(a[3]-b[3]) < 0.01;
}

function boxRect(b, color, dash, label) {
  if (!b) return "";
  const w = b[2] - b[0], h = b[3] - b[1];
  let s = '<rect x="' + b[0] + '" y="' + b[1] + '" width="' + w +
          '" height="' + h + '" fill="none" stroke="' + color +
          '" stroke-width="1.1"' +
          (dash ? ' stroke-dasharray="' + dash + '"' : '') + '/>';
  if (label) {
    s += '<text x="' + (b[0] + 1.5) + '" y="' + (b[1] + 7) + '" font-size="7" ' +
         'fill="' + color + '" font-family="monospace">' + label + '</text>';
  }
  return s;
}

function makeSvg(r) {
  const solid = $('#fill').checked;
  const showGrid = $('#grid200').checked;
  const showBox = $('#boxes').checked;
  const contours = r.contours || [];
  const paths = contours.map(contourToPath).filter(Boolean).join(" ");

  let g = "";
  if (showGrid) {
    g += '<rect x="0" y="0" width="200" height="200" fill="none" ' +
         'stroke="#e3e6ee" stroke-width="0.6"/>';
    /* 十字中线, 便于看比例 */
    g += '<line x1="100" y1="0" x2="100" y2="200" stroke="#eceff5" stroke-width="0.5"/>';
    g += '<line x1="0" y1="100" x2="200" y2="100" stroke="#eceff5" stroke-width="0.5"/>';
  }
  if (paths) {
    /* 必须用 nonzero, 不能用 evenodd。
       kage_contour.js 输出的是"每个笔画各自独立的轮廓多边形"(Polygons.array),
       笔画之间会重叠。evenodd 规则下, 被偶数个轮廓覆盖的点不填充
       → 笔画重叠处被挖空变白, 笔画越多越破碎
       (朋 10 笔、勿 5 笔这种尤其明显, 单笔画部件反而看不出来)。
       nonzero 则: 多个正向轮廓叠加仍然填充(并集), 反向的内孔轮廓正确挖空。 */
    g += solid
      ? '<path d="' + paths + '" fill="#111" fill-rule="nonzero"/>'
      : '<path d="' + paths + '" fill="rgba(0,123,255,0.10)" ' +
        'stroke="#007bff" stroke-width="1.1" fill-rule="nonzero"/>';
  }
  /* 盒画在字形之上, 免得被实心填充盖住 */
  if (showBox && r.boxes) {
    const bx = r.boxes;
    (bx.components || []).forEach(function (b, i) {
      if (sameBox(b, bx.outer)) return;          // 与外框重复就不重画
      g += boxRect(b, BOX_COLORS[i % BOX_COLORS.length], "3 2", "c" + (i + 1));
    });
    /* 候选腔: 未选中的橙色虚线 + [i] 编号, 选中的绿色粗线画在最上面 */
    (bx.candidates || []).forEach(function (b, i) {
      if (sameBox(b, bx.cavity)) return;         // 选中的那个下面单独画
      g += boxRect(b, CAND_ALT_COLOR, "2 4", "[" + i + "]");
    });
    g += boxRect(bx.cavity, CAVITY_COLOR, "5 3", "cavity ✓");
    /* 内部件的内容基准框 (central_box): 它被映射到 cavity 上, 所以它的大小
       直接决定内部件被放大/缩小多少 —— 口/日 这类会很大, 乂/木 会很小 */
    g += boxRect(bx.basis, BASIS_COLOR, "4 2 1 2", "basis");
    g += boxRect(bx.outer, OUTER_COLOR, "1.5 2.5", "outer");
  }
  return '<svg viewBox="-4 -4 208 208" xmlns="http://www.w3.org/2000/svg">' +
         g + '</svg>';
}

/* ---------- 渲染 ---------- */
let timer = null, autoOn = false;

async function render() {
  const lines = inputEl.value.split("\n").map(s => s.trim()).filter(Boolean);
  if (!lines.length) { gridEl.innerHTML = '<div class="empty">输入 IDS 后点"渲染"</div>'; return; }

  const btn = $('#go');
  btn.disabled = true;
  statusEl.textContent = "渲染中 ... " + lines.length + " 个";

  try {
    const resp = await fetch("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: lines }),
    });
    const data = await resp.json();
    const results = data.results || [];

    gridEl.innerHTML = "";
    let ok = 0, bad = 0;
    for (const r of results) {
      const card = document.createElement("div");
      card.className = "card" + (r.error ? " err" : "");
      const meta = r.error ? "失败"
        : (r.info.n_contours + " 轮廓 · " + r.info.n_points + " 点");
      let html = '<div class="head"><span class="ids">' + esc(r.ids) +
                 '</span><span class="meta">' + meta + '</span></div>';
      if (r.error) {
        bad++;
        html += '<div class="err">' + esc(r.error) + '</div>';
        if (r.info && r.info.log) {
          html += '<details><summary>IDS() 输出</summary><pre>' +
                  esc(r.info.log.slice(-1200)) + '</pre></details>';
        }
      } else {
        ok++;
        html += makeSvg(r);
        const names = (r.info.names || []).join(" + ");
        html += '<div class="foot">' + esc(names) + ' · ' + r.info.n_points + ' 点</div>';
      }
      card.innerHTML = html;
      gridEl.appendChild(card);
    }
    statusEl.textContent = "完成: " + ok + " 成功" +
      (bad ? " / " + bad + " 失败" : "") + " · 共 " + data.total_ms + "ms";
  } catch (e) {
    statusEl.textContent = "请求失败: " + e;
  } finally {
    btn.disabled = false;
  }
}

function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

$('#go').onclick = render;
$('#fill').onchange = render;
$('#boxes').onchange = render;
$('#grid200').onchange = render;

$('#auto').onclick = () => {
  autoOn = !autoOn;
  $('#auto').textContent = autoOn ? "自动 ●" : "自动";
  $('#auto').classList.toggle("ghost", !autoOn);
  if (autoOn) render();
};

inputEl.addEventListener("input", () => {
  if (!autoOn) return;
  clearTimeout(timer);
  timer = setTimeout(render, 700);
});

render();
</script>
</body>
</html>
"""


def main():
    port = PORT
    argv = sys.argv[1:]
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except Exception:
            pass

    # Windows 上端口常被占用或被 Hyper-V 保留 (WinError 10013), 自动往后找
    srv = None
    for p in range(port, port + 25):
        try:
            srv = HTTPServer((HOST, p), Handler)
            port = p
            break
        except OSError as e:
            log(f"端口 {p} 不可用 ({e.__class__.__name__}), 试下一个 ...")
    if srv is None:
        log(f"在 {PORT}~{PORT + 24} 范围内找不到可用端口, 请用 --port 指定")
        return

    url = f"http://{HOST}:{port}"
    if "--no-browser" not in argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    log(f"服务已启动 → {url}   (Ctrl+C 退出)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("bye")


if __name__ == "__main__":
    main()
