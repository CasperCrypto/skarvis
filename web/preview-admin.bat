@echo off
rem Local preview of the SKARVIS build console (web\admin). Double-click this.
rem Serves the whole project on this computer only, so the console can reach
rem the site assets, the CAD and the repo docs. Passphrase: casper33
rem Stop it with Ctrl+C or by closing this window. Needs Python on PATH.
cd /d "%~dp0.."
echo.
echo   SKARVIS build console: http://localhost:8010/web/admin/
echo   Passphrase: casper33   (soft gate, local only)
echo   Ctrl+C or close this window to stop.
echo.
start "" cmd /c "timeout /t 1 >nul & start http://localhost:8010/web/admin/"
python -m http.server 8010 --bind 127.0.0.1
