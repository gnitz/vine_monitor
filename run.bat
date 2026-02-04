@echo off
REM FIRST RUN:
REM  pip install -r requirements.txt
REM OR
REM python -m pip install -r requirements.txt

set WORKDIR=C:\Users\sowea\Documents\GitHub\vine_monitor
set LOGFILE=%WORKDIR%\vine_monitor.log
set STATEFILE=%WORKDIR%\vine_monitor_state.json

echo Working directory: %WORKDIR%
echo Log file: %LOGFILE%
echo State file: %STATEFILE%

:: If first arg is --reset (case-insensitive), truncate the log
if /I "%1"=="--reset" (
    echo Clearing %LOGFILE%
    if exist "%LOGFILE%" (
        > "%LOGFILE%" echo.
    ) else (
        type nul > "%LOGFILE%"
    )
    echo Clearing %STATEFILE%
    if exist "%STATEFILE%" (
        > "%STATEFILE%" echo.
    ) else (
        type nul > "%STATEFILE%"
    )
)

:: Tab 1 — server.py
wt -w 0 nt --startingDirectory "%WORKDIR%" powershell -NoExit -Command "python src\server.py"


:: Tab 2 — amazon-vine.py
wt -w 0 nt --startingDirectory "%WORKDIR%" powershell -NoExit -Command "python src\amazon-vine.py"
pause