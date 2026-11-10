# 把 IPA 字体的源文件同步进 web/public/fonts（每次在 FontCreator 里改完字体后跑一次）
$src = 'C:\Users\DZF\Desktop\IPA官网翻译\common_files\webfonts'
$dst = Join-Path $PSScriptRoot '..\web\public\fonts' | Resolve-Path
foreach ($n in @('IPASans-Regular.woff2','IPASans-Regular.woff','IPASerif-Regular.woff2','IPASerif-Regular.woff')) {
  Copy-Item (Join-Path $src $n) $dst -Force
  $h = (Get-FileHash (Join-Path $dst $n) -Algorithm SHA256).Hash.Substring(0,12)
  "  synced $n  ($h)"
}
