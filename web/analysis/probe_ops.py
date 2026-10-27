import io, os, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
cnt = {}
heads = {}
for f in ["ids_lv0.txt","ids_lv1.txt","ids_lv2.txt","ids_lv4.txt"]:
    p = os.path.join(r"D:\2026harucpp\web\public", f)
    if not os.path.exists(p): continue
    for line in io.open(p, encoding="utf-8", errors="replace"):
        h, _, b = line.rstrip("\n").partition("\t")
        for ch in b:
            if 0x2FF0 <= ord(ch) <= 0x2FFF or ord(ch) == 0x31EF:
                cnt[ch] = cnt.get(ch, 0) + 1
                heads.setdefault(ch, set()).add(h.strip())
print(f"{'算符':6s} {'U+':8s} {'出现':>7s} {'不同字':>7s}")
for ch, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(f"  {ch}   U+{ord(ch):04X}  {n:7d} {len(heads[ch]):7d}   {' '.join(sorted(heads[ch])[:4])}")
