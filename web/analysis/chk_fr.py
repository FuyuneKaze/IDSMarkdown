import re, sys, io, urllib.request
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
html = urllib.request.urlopen("http://127.0.0.1:18080/", timeout=30).read().decode("utf-8")
print("页面中的 fill-rule 属性值:", re.findall(r'fill-rule="([a-z]+)"', html))
print("是否残留 fill-rule=evenodd :", 'fill-rule="evenodd"' in html)
