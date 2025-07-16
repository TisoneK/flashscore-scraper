@echo off
REM Change to the directory where this script is located
cd /d "%~dp0"

REM Activate the virtual environment
call .venv\Scripts\activate.bat

REM Run the scraper in CLI mode
python main.py --cli

REM Pause to allow user to review output
pause 