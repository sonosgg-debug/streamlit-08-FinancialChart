@echo off
chcp 65001 > nul
title Financial Chart Dashboard
echo ========================================================
echo   Starting Financial Chart Web Dashboard...
echo   Address: http://localhost:8501
echo ========================================================
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

python -m streamlit run app.py

pause
