# -*- coding: utf-8 -*-
"""生成瘦身后的字形库 (core_glyphs.slim.json)

为什么可以裁掉 89%: bundle 里 79.5% 是第三方字形名 (hkcs_* / ac1-* / tangut-* …),
IDS 组字完全用不到 —— 它们只是别的项目合进来时的手滑。

做法: 从「标准名子集」出发做**引用闭包**, 把被引用到的外部名一并保留,
保证裁剪后不会因为缺子件而少笔画。

用法:
    python scripts/slim_bundle.py                 # 默认读 web/public, 写 D:/KAGE_GLYPH
    python scripts/slim_bundle.py --in X --out Y
"""
import argparse, io, json, os, re, sys, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 组字流程会用到的后缀: ⿰/-01 -02, ⿱/-03 -04, 包围/-05 -06, 拉伸/-08 -09,
# 密度外框/-10 -11 -15, 下半/-14 -24, 以及 -j (GlyphWiki 的基准部件)
KEEP_SUF = {f"{n:02d}" for n in list(range(1, 16)) + [24]} | {"j"}
STD = re.compile(r"^u([0-9a-f]+)(?:-([0-9a-z]+))?$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=r"D:\2026harucpp\web\public\core_glyphs.json")
    ap.add_argument("--out", dest="dst", default=r"D:\KAGE_GLYPH\core_glyphs.slim.json")
    a = ap.parse_args()

    t0 = time.time()
    obj = json.load(io.open(a.src, encoding="utf-8"))
    g = obj.get("glyphs", obj)
    print(f"读入 {len(g):,} 条 / {sum(len(v) for v in g.values())/1e6:.1f} MB  ({time.time()-t0:.1f}s)")

    core = {n for n in g if (m := STD.match(n)) and (m.group(2) is None or m.group(2) in KEEP_SUF)}
    print(f"标准名子集: {len(core):,} 条 / {sum(len(g[n]) for n in core)/1e6:.1f} MB")

    def refs(data: str):
        for seg in data.split("$"):
            if seg.startswith("99:"):
                p = seg.split(":")
                if len(p) >= 8:
                    yield p[7].split("@")[0]

    need, todo, missing = set(core), list(core), 0
    while todo:
        for r in refs(g.get(todo.pop(), "")):
            if r not in g:
                missing += 1          # 库里本就没有, 与裁剪无关
                continue
            if r not in need:
                need.add(r)
                todo.append(r)

    ext = need - core
    slim = {n: g[n] for n in need}
    total = sum(len(v) for v in slim.values())
    print(f"闭包后: {len(slim):,} 条 / {total/1e6:.1f} MB "
          f"(新增外部名 {len(ext):,} 条 / {sum(len(g[n]) for n in ext)/1e6:.1f} MB)")

    os.makedirs(os.path.dirname(a.dst), exist_ok=True)
    io.open(a.dst, "w", encoding="utf-8").write(
        json.dumps({"glyphs": slim}, ensure_ascii=False, separators=(",", ":")))
    print(f"写出 {a.dst}  ({os.path.getsize(a.dst)/1e6:.1f} MB, {time.time()-t0:.1f}s)")

    gz = a.dst + ".gz"
    import gzip
    with io.open(a.dst, "rb") as fi, gzip.open(gz, "wb", compresslevel=9) as fo:
        fo.write(fi.read())
    print(f"写出 {gz}  ({os.path.getsize(gz)/1e6:.1f} MB)  ← 这才是要上传的传输体积")
    print(f"缺失引用 {missing} 处 (原库残缺, 与裁剪无关)")


if __name__ == "__main__":
    main()
