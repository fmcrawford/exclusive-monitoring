@echo off
cd /d "%~dp0"
set IMPERSONATE=chrome131
python discord_notifier.py
pause
