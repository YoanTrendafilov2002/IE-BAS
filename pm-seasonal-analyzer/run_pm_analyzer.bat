@echo off
cd /d "%~dp0"
python pm_seasonal_analyzer.py --gui
if errorlevel 1 (
  echo.
  echo The program could not start. Install its packages with:
  echo python -m pip install -r requirements.txt
  pause
)
