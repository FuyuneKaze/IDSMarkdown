# -*- coding: utf-8 -*-
"""量化 Python 侧「一次组字」到底花多久: 裸 get_data 路径 vs preview 的索引路径"""
import sys, io, time, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")

_buf = io.StringIO()


def t(label, fn, n=3):
    with contextlib.redirect_stdout(_buf):
        fn()                                   # 预热
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        dt = (time.perf_counter() - t0) / n
    print(f"  {label:38s} {dt * 1000:9.1f} ms")
    return dt


def clock(label, fn):
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(_buf):
        fn()
    print(f"  {label:38s} {(time.perf_counter() - t0) * 1000:9.1f} ms")


print("① 载入字形库 (import glyph_extend)")
t0 = time.perf_counter()
import glyph_extend                      # noqa: E402
import ids_anal                          # noqa: E402
print(f"  {'import (读 248 万行)':38s} {(time.perf_counter() - t0) * 1000:9.1f} ms")
print(f"  dbs 行数 = {len(glyph_extend.dbs):,}")

print("\n② 裸路径 (脚本里直接调 ids_anal 时走的就是这条)")
t("IDS('⿰', [氵, 工])", lambda: ids_anal.IDS("⿰", ["u6c35", "u5de5"]))
t("IDS('⿱', [宀, 丁])", lambda: ids_anal.IDS("⿱", ["u5b80", "u4e01"]))
t("IDS('⿲', 木木木)", lambda: ids_anal.IDS("⿲", ["u6728", "u6728", "u6728"]))
t("return_bone('u5ffd-02')", lambda: glyph_extend.return_bone("u5ffd-02"))

print("\n③ 挂上 preview 的索引后 (web/preview/preview.py 启动时做的事)")
t0 = time.perf_counter()
import preview                            # noqa: E402  (module 级: 建索引 + 清 dbs)
print(f"  {'preview 启动 (建索引 + 清 dbs)':38s} {(time.perf_counter() - t0) * 1000:9.1f} ms")
print(f"  当前 get_data = {glyph_extend.get_data.__name__}")
t("IDS('⿰', [氵, 工])", lambda: ids_anal.IDS("⿰", ["u6c35", "u5de5"]))
t("IDS('⿱', [宀, 丁])", lambda: ids_anal.IDS("⿱", ["u5b80", "u4e01"]))
t("IDS('⿲', 木木木)", lambda: ids_anal.IDS("⿲", ["u6728", "u6728", "u6728"]))
t("return_bone('u5ffd-02')", lambda: glyph_extend.return_bone("u5ffd-02"))
