@echo off
chcp 1252 >nul 2>&1
title STEG PV
color 1F

SET "BASE=%~dp0"
SET "VENV=%BASE%venv"
SET "VEXE=%VENV%\Scripts\python.exe"
SET "PEMBED=%BASE%python_embed\python.exe"
SET "PORT=5000"

echo.
echo =====================================================
echo    STEG PV - Gestion Photovoltaique
echo =====================================================
echo.

:: --- Liberer le port avant demarrage ---
FOR /F "tokens=5" %%P IN ('netstat -ano 2^>nul ^| findstr ":%PORT% " ^| findstr "LISTENING"') DO (
    IF NOT "%%P"=="0" (
        echo [!]  Port %PORT% occupe par PID %%P - Liberation...
        taskkill /F /PID %%P >nul 2>&1
        timeout /t 2 /nobreak >nul
    )
)

IF EXIST "%PEMBED%" (
    SET "PY=%PEMBED%"
    goto :check_deps
)

IF EXIST "%VEXE%" (
    SET "PY=%VEXE%"
    goto :launch
)

SET "SYSPY="
python -c "import sys" >nul 2>&1
IF %ERRORLEVEL% EQU 0 SET "SYSPY=python"
IF DEFINED SYSPY goto :create_venv

py -c "import sys" >nul 2>&1
IF %ERRORLEVEL% EQU 0 SET "SYSPY=py"
IF DEFINED SYSPY goto :create_venv

echo [!] Python introuvable. Installation automatique...
goto :install_embed

:create_venv
"%SYSPY%" -m venv "%VENV%" >nul 2>&1
IF NOT EXIST "%VEXE%" goto :install_embed
SET "PY=%VEXE%"
"%PY%" -m pip install flask werkzeug openpyxl --no-warn-script-location -q
goto :launch

:check_deps
"%PY%" -c "import flask" >nul 2>&1
IF ERRORLEVEL 1 "%PY%" -m pip install flask werkzeug openpyxl --no-warn-script-location -q
goto :launch

:install_embed
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol='Tls12';(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip','%BASE%py.zip')}catch{exit 1}"
IF ERRORLEVEL 1 exit /b 1
powershell -NoProfile -Command "Expand-Archive -Path '%BASE%py.zip' -DestinationPath '%BASE%python_embed' -Force"
del "%BASE%py.zip" >nul 2>&1
IF NOT EXIST "%PEMBED%" exit /b 1
echo import site>> "%BASE%python_embed\python311._pth"
powershell -NoProfile -Command "try{(New-Object Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py','%BASE%python_embed\get-pip.py')}catch{exit 1}"
"%PEMBED%" "%BASE%python_embed\get-pip.py" --no-warn-script-location >nul 2>&1
SET "PY=%PEMBED%"
"%PY%" -m pip install flask werkzeug openpyxl --no-warn-script-location -q

:launch
cd /d "%BASE%"
"%PY%" launcher.py
