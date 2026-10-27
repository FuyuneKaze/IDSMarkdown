@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   IDS 批量预览工具
echo   ----------------------------------------
echo   启动后浏览器会自动打开预览页面
echo   关闭本窗口即停止服务
echo.
python preview.py
echo.
echo   服务已退出。按任意键关闭窗口。
pause >nul
