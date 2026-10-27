import time, csv, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
t00 = time.time()
from kage import Kage
from kage.font.serif import Serif
print(f"import: {time.time()-t00:.2f}s")

t0 = time.time()
k = Kage(ignore_component_version=True)
k.font = Serif()
print(f"Kage init: {time.time()-t0:.2f}s")

DUMP = "D:/KAGE_GLYPH/dump_newest_only.txt"
t0 = time.time()
lines = open(DUMP, encoding="utf-8").readlines()
print(f"readlines: {time.time()-t0:.2f}s  ({len(lines):,} lines)")

t0 = time.time()
n = 0
for row in csv.reader(lines, delimiter="|"):
    if len(row) < 3:
        continue
    r = [s.strip() for s in row]
    if not r[0] or r[0].startswith("-"):
        continue
    k.components.push(r[0], r[2])
    n += 1
print(f"push {n:,}: {time.time()-t0:.2f}s")
print(f"TOTAL: {time.time()-t00:.2f}s")
print("components type:", type(k.components))
