@echo off
cd /d "C:\AI\놀이터"

set LOG_DIR=C:\AI\놀이터\logs
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "tokens=1-4 delims=/ " %%a in ('date /t') do (set mydate=%%a%%b%%c)
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
set LOG_FILE=%LOG_DIR%\sync_%mydate%_%mytime%.log

echo ================================================== > "%LOG_FILE%"
echo Google Sheets Auto Sync >> "%LOG_FILE%"
echo Start Time: %date% %time% >> "%LOG_FILE%"
echo ================================================== >> "%LOG_FILE%"

python sync_google_sheet_incremental.py >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo. >> "%LOG_FILE%"
    echo [SUCCESS] Sync completed >> "%LOG_FILE%"
) else (
    echo. >> "%LOG_FILE%"
    echo [ERROR] Sync failed: %ERRORLEVEL% >> "%LOG_FILE%"
)

echo ================================================== >> "%LOG_FILE%"
echo End Time: %date% %time% >> "%LOG_FILE%"
echo ================================================== >> "%LOG_FILE%"
