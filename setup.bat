@echo off
echo Setting up environment for dataflow generator...

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not found. Please install Python 3.10 or newer.
    exit /b 1
)

REM Create Python virtual environment
echo Creating Python virtual environment...
python -m venv .venv

REM Activate the virtual environment
echo Activating virtual environment...
call .\.venv\Scripts\activate.bat

REM Install uv
echo Installing uv package manager...
pip install uv

REM Install dependencies
echo Installing dependencies using uv...
uv sync

echo Setup complete. To activate the virtual environment, run '.\.venv\Scripts\activate.bat'. To start the app, run 'data-flow-generator'. 