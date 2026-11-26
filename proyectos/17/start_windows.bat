@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto launch
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 -c "import sys;sys.exit(sys.version_info < (3,10))"
if errorlevel 1 goto missing
py -3 -m venv .venv
if errorlevel 1 goto failed
goto launch
:usepython
where python >nul 2>nul
if errorlevel 1 goto missing
python -c "import sys;sys.exit(sys.version_info < (3,10))"
if errorlevel 1 goto missing
python -m venv .venv
if errorlevel 1 goto failed
:launch
".venv\Scripts\python.exe" app.py %*
if errorlevel 1 goto failed
exit /b 0
:missing
echo Instala Python 3.10 o posterior desde python.org y vuelve a ejecutar este archivo.
:failed
pause
exit /b 1
