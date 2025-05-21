@echo off
echo Setting up environment for dataflow generator...

REM Check for fd and recommend installation if missing
where fd >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Optional: For much faster file search, install 'fd' (https://github.com/sharkdp/fd):
    echo   winget install sharkdp.fd
    echo   or choco install fd
    echo   or scoop install fd
    echo.
)

REM Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python is not found. Please install Python 3.10 or newer.
    exit /b 1
)

REM Remove existing virtual environment if it exists
if exist .venv (
    echo Removing existing virtual environment...
    rmdir /s /q .venv
    if exist .venv (
        echo Failed to remove existing virtual environment. Please remove it manually and try again.
        exit /b 1
    )
)

REM Create Python virtual environment
echo Creating Python virtual environment...
python -m venv .venv
if %ERRORLEVEL% NEQ 0 (
    echo Failed to create Python virtual environment.
    exit /b 1
)

REM Check if activation script exists
if not exist .\.venv\Scripts\activate.bat (
    echo Activation script not found. Virtual environment creation may have failed.
    exit /b 1
)

REM Activate the virtual environment
echo Activating virtual environment...
call .\.venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate the virtual environment.
    exit /b 1
)

REM Install uv
echo Installing uv package manager...
pip install uv
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install uv.
    exit /b 1
)

REM Check if uv is installed
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 'uv' is not available after installation.
    exit /b 1
)

REM Install dependencies
echo Installing dependencies using uv...
uv sync --dev
if %ERRORLEVEL% NEQ 0 (
    echo Failed to install dependencies using uv.
    exit /b 1
)

echo Setup complete. To activate the virtual environment, run ".\.venv\Scripts\activate.bat"
echo To start the app (once activated), run "data-flow-generator"