@echo off
rem Local preview of the SKARVIS site (web\site). Double-click this file.
rem It serves the site on this computer only and opens it in your browser.
rem Stop it with Ctrl+C or by closing this window. Needs Python on PATH.
cd /d "%~dp0site"
echo.
echo   SKARVIS preview: http://localhost:8000
echo   Ctrl+C or close this window to stop.
echo.
start "" cmd /c "timeout /t 1 >nul & start http://localhost:8000"
python -m http.server 8000 --bind 127.0.0.1
