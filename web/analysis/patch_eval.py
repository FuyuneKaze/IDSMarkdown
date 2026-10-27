# -*- coding: utf-8 -*-
"""把读路径上的 eval 换成 int/float (实测 eval 是数据库/字形解析的大头)

替换是逐条精确匹配 + 计数断言: 任何一条对不上就中止, 不会静默改错。
"""
import io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def read(p):
    return io.open(p, encoding="utf-8", newline="").read()

def write(p, s):
    io.open(p, "w", encoding="utf-8", newline="").write(s)

def rep(txt, old, new, n=1):
    got = txt.count(old)
    assert got == n, f"期望 {n} 处, 实际 {got} 处: {old!r}"
    return txt.replace(old, new)

# ---------------------------------------------------------------- glyph_extend
p = r"D:\2026harucpp\scripts\glyph_extend.py"
t = read(p)

t = t.replace("import numpy as np\n",
              "import numpy as np\n"
              "\n"
              "def _num(s):\n"
              "    \"\"\"数字字段解析: 比 eval 快一个数量级 (eval 要编译表达式)\n"
              "\n"
              "    库里的坐标有整数也有小数 (54 / 54.16), 用 '.' 判断走 int 还是 float,\n"
              "    避免 try/except 的开销 (小数占多数, 每次都抛异常反而更慢)。\n"
              "    \"\"\"\n"
              "    return float(s) if '.' in s else int(s)\n", 1)

t = rep(t, "[eval(i) for i in self.list[3:7]]", "[_num(i) for i in self.list[3:7]]")
t = rep(t, "[eval(i) for i in self.list[1:3]]", "[_num(i) for i in self.list[1:3]]")
t = rep(t, "[eval(i) for i in self.list[10:12]]", "[_num(i) for i in self.list[10:12]]")
t = rep(t, "        return eval(n)", "        return _num(n)")
t = rep(t, "if eval(Lp[0]) in [1, 2, 3, 4, 6, 7]:", "if int(Lp[0]) in (1, 2, 3, 4, 6, 7):")
t = rep(t, "elif eval(Lp[0]) == 0 and eval(Lp[1]) in [97, 98, 99]:",
        "elif int(Lp[0]) == 0 and int(Lp[1]) in (97, 98, 99):")
t = rep(t, "elif eval(Lp[0]) == 99:", "elif int(Lp[0]) == 99:")
t = rep(t, "if eval(Ep[0]) in [1, 2, 3, 4, 6, 7]:", "if int(Ep[0]) in (1, 2, 3, 4, 6, 7):", 6)
t = rep(t, "all_points.append((eval(Ep[i]),eval(Ep[i+1])))",
        "all_points.append((_num(Ep[i]),_num(Ep[i+1])))", 2)
t = rep(t, "x = eval(Ep[i])#int", "x = _num(Ep[i])", 4)
t = rep(t, "y = eval(Ep[i+1])", "y = _num(Ep[i+1])", 4)
t = rep(t, "box = [eval(i) for i in cmd[3:7]]", "box = [_num(i) for i in cmd[3:7]]", 2)
write(p, t)
print("glyph_extend.py  OK")

# ---------------------------------------------------------------- stroke_outer
p = r"D:\2026harucpp\scripts\stroke_outer.py"
t = read(p)
t = rep(t, "keys=[eval(i) for i in keys]",
        "keys=[float(i) if '.' in i else int(i) for i in keys]")
write(p, t)
print("stroke_outer.py  OK")

# ---------------------------------------------------------------- ids_anal
p = r"D:\2026harucpp\scripts\ids_anal.py"
t = read(p)
t = rep(t, "x = [eval(i) for i in li[3::2]]", "x = [float(i) for i in li[3::2]]")
t = rep(t, "y = [eval(i) for i in li[4::2]]", "y = [float(i) for i in li[4::2]]")
write(p, t)
print("ids_anal.py      OK")

# 检查还有没有漏网的 eval
for p in (r"D:\2026harucpp\scripts\glyph_extend.py",
          r"D:\2026harucpp\scripts\stroke_outer.py",
          r"D:\2026harucpp\scripts\ids_anal.py"):
    left = [i + 1 for i, ln in enumerate(read(p).split("\n")) if "eval(" in ln and "eval1(" not in ln]
    print(f"  {p.split(chr(92))[-1]:20s} 剩余 eval( 行: {left}")
