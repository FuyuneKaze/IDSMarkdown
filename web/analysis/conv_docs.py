import re, html, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
src = r"D:\2026harucpp\cpp-desktop"
files = {
  "spec": "GlyphWiki_KAGEデータ仕様 - GlyphWiki.html",
  "reg":  "GlyphWiki_登记字形 - GlyphWiki.html",
  "adv":  "GlyphWiki_高度な活用方法 - GlyphWiki.html",
}
for key, fn in files.items():
    p = os.path.join(src, fn)
    t = open(p, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S|re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S|re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|tr|li|h[1-6])>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    out = os.path.join(r"D:\2026harucpp\web\analysis", f"doc_{key}.txt")
    open(out, "w", encoding="utf-8").write(t)
    print(f"{key}: {len(t)} chars -> {out}")
