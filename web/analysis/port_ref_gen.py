# -*- coding: utf-8 -*-
"""
生成"轮廓/包围盒"移植的参考数据 (用 Python 原版 stroke_outer.py)

输出 port_ref.json: [{ "stro": ..., "types": t, "off": [x1,y1,x2,y2],
                        "on": [x1,y1,x2,y2] }, ...]
  off = strokic_boundary(stro, ifshrink=False)
  on  = strokic_boundary(stro, ifshrink=True)
"""
import sys, io, json, contextlib
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, r"D:\2026harucpp\scripts")

import glyph_extend
from stroke_outer import strokic_boundary

NAMES = [
    "u4e00", "u5fc3-04", "u8279-03", "u864d-10", "u52f9-05", "u5382-05",
    "u8fb6-10", "u6c35-01", "u5de5-02", "u624c-01", "u6728-01", "u53e3-01",
    "u65e5-04", "u7592-10", "u5e7f-05", "u9e7f-11", "u8863-05", "u884c-05",
    "u56d7-j", "u9580-05", "u4eba-06", "u6c14-05", "u9ebb-05-var-003",
]

by_type = defaultdict(list)
for nm in NAMES:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        data = glyph_extend.return_bone(nm)
    if not data:
        print(f"  {nm}: 空")
        continue
    for s in data.split("$"):
        s = s.strip()
        if not s:
            continue
        p = s.split(":")
        if p[0] not in ("1", "2", "3", "4", "6", "7"):
            continue
        t = int(p[0])
        if len(by_type[t]) < 8:          # 每种类型最多取 8 条
            by_type[t].append(s)

print("各笔画类型收集数:", {k: len(v) for k, v in sorted(by_type.items())})

# 真实字库里 type 4 (乙線) / 6 (複曲線) 罕见, 补合成样本把分支都覆盖到
SYNTH = {
    3: ["3:0:0:30:40:30:150:150:150"],
    4: ["4:0:0:20:180:40:60:180:40",
        "4:0:0:150:30:150:150:40:170",
        "4:5:0:10:10:10:190:190:190"],       # 尾形 5 (竖钩)
    6: ["6:0:0:100:10:100:80:100:150:10:190",
        "6:0:0:20:20:60:180:140:20:180:180"],
    7: ["7:0:7:20:20:60:40:100:40:180:180"],
    1: ["1:0:4:20:100:180:100"],             # 尾形 4 (横钩)
}
for t, lst in SYNTH.items():
    by_type[t].extend(lst)
print("补合成样本后:", {k: len(v) for k, v in sorted(by_type.items())})

recs = []
for t in sorted(by_type):
    for s in by_type[t]:
        b0 = strokic_boundary(s, ifshrink=False)
        b1 = strokic_boundary(s, ifshrink=True)
        recs.append({
            "type": t,
            "stro": s,
            "off": [b0.x1, b0.y1, b0.x2, b0.y2],
            "on": [b1.x1, b1.y1, b1.x2, b1.y2],
        })

out = r"D:\2026harucpp\web\analysis\port_ref.json"
json.dump(recs, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"写出 {len(recs)} 条 → {out}")
print()
for r in recs[:6]:
    print(f"  type={r['type']}  off={[round(v,3) for v in r['off']]}  "
          f"on={[round(v,3) for v in r['on']]}")
