@echo off
cd /d "%~dp0"
echo Starting Expense Tracker...
start python app.py
timeout /t 3 /nobreak >nul
start "" "http://localhost:8080"
echo Done! Your browser should open now.
