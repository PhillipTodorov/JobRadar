@echo off
title JobRadar - Application Assistant
cls
echo ================================================
echo           JobRadar - Application Assistant
echo ================================================
echo.
echo Starting services...
echo.

REM Change to script directory
cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start Flask backend
echo [1/2] Starting Flask Backend (http://localhost:5000)...
start /B python tools/answer_questions_api.py >nul 2>&1

REM Wait a moment for Flask to start
timeout /t 2 >nul

REM Start Streamlit dashboard
echo [2/2] Starting Dashboard (http://localhost:8501)...
set STREAMLIT_CLI_TELEMETRY=0
python -m streamlit run app.py

REM When Streamlit closes, kill Flask too
taskkill /F /IM python.exe >nul 2>&1
