@echo off
cd /d "%~dp0"
python tools\maverick_gui.py
if errorlevel 1 pause
