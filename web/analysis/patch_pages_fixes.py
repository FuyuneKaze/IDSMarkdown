# -*- coding: utf-8 -*-
"""修复线上(GitHub Pages)两个问题:

1) kage 编辑器 404 —— KageEditorPanel 里 iframe 用的 URL 是硬编码 "/kage-editor/...",
   子路径部署下会指到域名根。改用 assetUrl()。
2) 字形一直停在"等待数据"—— 生成 prefetch 完成后只调用一次 __recomposeIds,
   而那时 idsCompose 的插件可能还没注册该函数 / 数据库还没 loaded, 于是重排被吞掉。
   改成"等它出现 + 更长重试预算"。
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ED = os.path.join(ROOT, "src", "editor")
CP = os.path.join(ROOT, "src", "components")


def patch(path, pairs, need_import=None, imp_line=None):
    s = io.open(path, encoding="utf-8").read()
    n = 0
    for old, new in pairs:
        if old not in s:
            print(f"  !! {os.path.basename(path)}: 未找到 {old[:60]!r}")
            continue
        s = s.replace(old, new)
        n += 1
    if need_import and imp_line and need_import not in s:
        s = imp_line + s
    io.open(path, "w", encoding="utf-8", newline="").write(s)
    print(f"  {os.path.basename(path)}: 替换 {n} 处")


# ---------- 1. kage 编辑器 URL ----------
patch(
    os.path.join(CP, "KageEditorPanel.tsx"),
    [('return `/kage-editor/index.html#${params.join("&")}`;',
      'return assetUrl(`/kage-editor/index.html#${params.join("&")}`);')],
    need_import="assetUrl",
    imp_line='import { assetUrl } from "../editor/assetUrl";\n',
)

# ---------- 2. prefetch 后等 __recomposeIds 出现 ----------
patch(
    os.path.join(ED, "kageEngine.ts"),
    [(
        "            (window as any).__recomposeIds?.();",
        "            this.afterPrefetch();",
    )],
)

# 追加 afterPrefetch 方法
kage = os.path.join(ED, "kageEngine.ts")
s = io.open(kage, encoding="utf-8").read()
if "private afterPrefetch(" not in s:
    anchor = "  /** 将 IDS 字符串渲染为 SVG，未就绪或失败返回 null */"
    method = '''  /**
   * 远程取到字形之后的重排触发
   *
   * 为什么不是直接 `__recomposeIds?.()`: 线上(无 bundle)首次渲染发生得很早,
   * 那一刻 idsCompose 的插件可能**还没注册** __recomposeIds, 或者它的 IDS 数据库
   * 还没 loaded —— 直接调用会被静默吞掉, 于是字一直停在"等待数据"的黄色状态。
   * 这里改成轮询等待函数出现, 再交给它自己的重试预算去等数据库。
   */
  private afterPrefetch(attempt = 0): void {
    const fn = (window as any).__recomposeIds;
    if (typeof fn === "function") {
      fn();
      return;
    }
    if (attempt >= 20) {
      console.warn("[KageEngine] __recomposeIds 一直未注册, 放弃自动重排");
      return;
    }
    setTimeout(() => this.afterPrefetch(attempt + 1), 250);
  }

'''
    if anchor in s:
        s = s.replace(anchor, method + anchor, 1)
        io.open(kage, "w", encoding="utf-8", newline="").write(s)
        print("  kageEngine.ts: 已加 afterPrefetch()")
    else:
        print("  !! kageEngine.ts: 找不到插入锚点")

# ---------- 3. idsCompose 的重试预算加大 ----------
patch(
    os.path.join(ED, "idsCompose.ts"),
    [("if (recomposeRetries < 10) {", "if (recomposeRetries < 40) {"),
     ('console.log("[idsCompose] __recomposeIds: database not loaded, retrying in 300ms (attempt " + (recomposeRetries + 1) + ")");',
      'console.log("[idsCompose] __recomposeIds: database not loaded, retrying in 500ms (attempt " + (recomposeRetries + 1) + ")");'),
     ("setTimeout(() => (window as any).__recomposeIds?.(optView), 300);",
      "setTimeout(() => (window as any).__recomposeIds?.(optView), 500);"),
     ('console.warn("[idsCompose] __recomposeIds: gave up after 10 retries");',
      'console.warn("[idsCompose] __recomposeIds: gave up after 40 retries");')],
)
