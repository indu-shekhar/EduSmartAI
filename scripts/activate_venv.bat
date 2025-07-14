@echo off
REM Activate virtual environment script for Windows
REM This script activates the Python virtual environment

echo Activating EduSmartAI virtual environment...

REM Change to the project directory
cd /d "%~dp0.."

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Error: Virtual environment not found!
    echo Please create it first with: py -m venv .venv
    pause
    exit /b 1
)

REM Activate the virtual environment
call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Virtual environment activated successfully!
echo You can now run Python commands with the activated environment.
echo.
echo Useful commands:
echo   pip install -r requirements.txt  (install dependencies)
echo   python ingest.py --refresh        (refresh document index)
echo   flask run --port 8000             (start development server)
echo   waitress-serve --port=8000 "app:create_app()"  (start production server)
echo.
echo To deactivate, type: deactivate
echo.

REM Keep the command prompt open
cmd /k
