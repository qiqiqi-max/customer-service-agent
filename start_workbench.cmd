@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%start_workbench.ps1"

if not exist "%PS_SCRIPT%" (
  echo Missing PowerShell launcher: "%PS_SCRIPT%"
  pause
  exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
if errorlevel 1 (
  echo.
  echo Start failed. Please review the error above.
  pause
  exit /b 1
)

exit /b 0
