@echo off
rem SKARVIS Trener (web\site\trener): opens the operator training console in your browser.
rem No server needed: the page and the demo run load straight from disk.
rem To make a new run: cd software, then
rem   python -m czapla.sim --no-store --out ..\web\site\trener\runs\podstacja.js
start "" "%~dp0site\trener\index.html"
