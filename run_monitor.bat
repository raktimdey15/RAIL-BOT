@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Bangladesh Railway Ticket Availability Alert

echo ============================================================
echo     BANGLADESH RAILWAY - TICKET AVAILABILITY ALERT
echo ============================================================
echo.
set /p "FROM_STATION=From station: "
if not defined FROM_STATION goto missing
set /p "TO_STATION=Destination station: "
if not defined TO_STATION goto missing
set /p "JOURNEY_DATE=Journey date (e.g. 25-Oct-2026): "
if not defined JOURNEY_DATE goto missing
set /p "TRAIN_NAME=Train name (ALL for any train): "
if not defined TRAIN_NAME goto missing
echo Seat types: SNIGDHA, S_CHAIR, SHOVAN, AC_B, AC_S, F_BERTH, F_SEAT, F_CHAIR, SULOV, ALL
set /p "SEAT_CLASS=Seat type: "
if not defined SEAT_CLASS goto missing

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (
  where python >nul 2>nul
  if errorlevel 1 (echo Install Python 3 from https://www.python.org/downloads/ & pause & exit /b 1)
  set "PY=python"
)
echo.
echo Installing/updating Playwright...
%PY% -m pip install --user --upgrade "playwright>=1.48"
if errorlevel 1 (echo Could not install Playwright. Check internet connection. & pause & exit /b 1)

set "CHROME="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined CHROME if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "CHROME=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined CHROME if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "CHROME=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined CHROME (echo Could not find Chrome or Edge. Install one and retry. & pause & exit /b 1)

%PY% -c "import json,os; c={'from_station':os.environ['FROM_STATION'].strip(),'to_station':os.environ['TO_STATION'].strip(),'journey_date':os.environ['JOURNEY_DATE'].strip(),'train_name':os.environ['TRAIN_NAME'].strip(),'seat_class':os.environ['SEAT_CLASS'].strip().upper(),'poll_interval_seconds':10,'open_railway_site_on_alert':True}; json.dump(c,open('config.json','w',encoding='utf-8'),indent=2,ensure_ascii=False)"
if errorlevel 1 (echo Could not save settings. & pause & exit /b 1)
if exist "%~dp0chrome-profile\DevToolsActivePort" (echo Monitor browser may already be running. Close it and retry. & pause & exit /b 1)
echo.
echo Opening dedicated browser. Log in normally on the official site.
echo First run only; profile is saved in chrome-profile.
start "Railway monitor browser" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%~dp0chrome-profile" "https://eticket.railway.gov.bd/"
echo.
echo After you are logged in in the browser, return here and press any key.
pause >nul
%PY% monitor.py
pause
exit /b 0
:missing
echo All fields are required. Restart the BAT file and enter each value.
pause
exit /b 1
