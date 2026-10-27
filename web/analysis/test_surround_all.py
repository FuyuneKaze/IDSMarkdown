# -*- coding: utf-8 -*-
"""把 9 个包围算符全跑一遍, 打印腔/候选/落位 —— 给人工验证用"""
import sys, io, contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")
sys.path.insert(0, r"D:\2026harucpp\web\preview")
import preview                                     # noqa: E402
import ids_anal                                    # noqa: E402

CASES = [
    ("⿴", ["u56d7", "u4eba"]),   # 囚 = 囗 人
    ("⿵", ["u5182", "u4e42"]),   # 冈 = 冂 乂
    ("⿶", ["u51f5", "u4e42"]),   # 凶 = 凵 乂
    ("⿷", ["u531a", "u4e42"]),   # 区 = 匚 乂
    ("⿸", ["u5382", "u4eba"]),   # 仄 = 厂 人
    ("⿹", ["u2cea0", "u4e36"]),  # 寸 = 𬺰 丶
    ("⿺", ["u200ca", "u4eba"]),  # 亾 = 𠃊 人
    ("⿼", ["u53c9", "u4e36"]),   # 㕚 = 叉 丶
    ("⿽", ["u5341", "u2e80"]),   # 斗 = 十 ⺀
    ("⿴", ["u884c", "u4eba"]),   # 行 + 人  (左右分立: 无 pocket, 应退回老算法)
    ("⿴", ["u8863", "u4eba"]),   # 衣 + 人  (上下分立: 同上)
    ("⿺", ["u8fb6", "u5bf8"]),   # 辶 + 寸  (开口钩子: 应退回老算法)
    ("⿺", ["u9b3c", "u6597"]),   # 鬼 + 斗  (梳形面: 应退回老算法)
    ("⿴", ["u65e5", "u4e00"]),   # 日 + 一  (两格容器: 应该有 2 个候选)
    ("⿴", ["u7530", "u4e00"]),   # 田 + 一  (四格容器: 应该有 4 个候选)
]

buf = io.StringIO()
for op, args in CASES:
    with contextlib.redirect_stdout(buf):
        out = ids_anal.IDS(op, list(args))
    b = ids_anal.LAST_BOXES
    fmt = lambda t: "None" if not t else "[%6.1f,%6.1f,%6.1f,%6.1f]" % tuple(t)
    print(f"{op}{args[0]}+{args[1]}   笔画 {len((out or '').split('$'))} 段")
    print(f"    外框      {fmt(b['outer'])}")
    print(f"    候选({len(b['candidates'])})   " +
          "  ".join(f"[{i}]{fmt(c)}" for i, c in enumerate(b["candidates"])))
    print(f"    选中腔    {fmt(b['cavity'])}")
    print(f"    内部件盒  {fmt(b['components'][1]) if len(b['components'])>1 else 'None'}")
    print()
