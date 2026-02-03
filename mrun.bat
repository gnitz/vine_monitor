REM FIRST RUN:
REM  pip install -r requirements.txt
REM OR
REM python -m pip install -r requirements.txt
@echo off

set WORKDIR=C:\Users\sowea\Documents\GitHub\vine_monitor
set LOGFILE=%WORKDIR%\vine_monitor.log

echo Working directory: %WORKDIR%
echo Log file: %LOGFILE%
python %WORKDIR%\src\amazon-vine.py