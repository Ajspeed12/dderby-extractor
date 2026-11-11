@echo off
setlocal DisableDelayedExpansion
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>&1
if errorlevel 1 (
  echo Python 3.11 or newer is required. Install Python and enable Add to PATH.
  pause
  exit /b 1
)
python -c "import numpy, PIL, unicorn" >nul 2>&1
if errorlevel 1 (
  echo Installing required Python packages...
  python -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo Installation failed. Check your connection and Python installation.
    pause
    exit /b 1
  )
)
if "%~1"=="" goto ask_folder
python "%~dp0dd1_extract.py" %*
goto finished

:ask_folder
set "dd1_game_folder="
set /p "dd1_game_folder=Paste the extracted game folder path: "
set "dd1_game_folder=%dd1_game_folder:"=%"
if not defined dd1_game_folder (
  echo No folder supplied.
  pause
  exit /b 1
)
python "%~dp0dd1_extract.py" "%dd1_game_folder%\."

:finished
set "dd1_result=%errorlevel%"
echo.
if not "%dd1_result%"=="0" echo Extraction did not finish successfully. Read the error above.
pause
exit /b %dd1_result%
