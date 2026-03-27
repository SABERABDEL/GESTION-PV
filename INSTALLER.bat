@echo off
chcp 1252 >nul 2>&1
title STEG PV - Installation
color 1F

SET "BASE=%~dp0"
SET "PYDIR=%BASE%python_embed"
SET "PYEXE=%PYDIR%\python.exe"

echo.
echo =====================================================
echo    STEG PV - Installation Automatique
echo =====================================================
echo.

IF EXIST "%PYEXE%" goto :install_deps

echo [1/4] Telechargement Python 3.11 embarque...
powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol='Tls12';(New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip','%BASE%py.zip')}catch{exit 1}"
IF ERRORLEVEL 1 (
    echo [ERREUR] Telechargement echoue. Verifiez Internet.
    pause
    exit /b 1
)

echo [2/4] Extraction...
powershell -NoProfile -Command "Expand-Archive -Path '%BASE%py.zip' -DestinationPath '%PYDIR%' -Force"
del "%BASE%py.zip" >nul 2>&1

IF NOT EXIST "%PYEXE%" (
    echo [ERREUR] Extraction echouee.
    pause
    exit /b 1
)

echo import site>> "%PYDIR%\python311._pth"

echo [3/4] Installation pip...
powershell -NoProfile -Command "try{(New-Object Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py','%PYDIR%\get-pip.py')}catch{exit 1}"
"%PYEXE%" "%PYDIR%\get-pip.py" --no-warn-script-location >nul 2>&1

:install_deps
echo [4/4] Installation Flask et dependances...
"%PYEXE%" -m pip install flask werkzeug openpyxl --no-warn-script-location -q
IF ERRORLEVEL 1 (
    echo [ERREUR] Installation des dependances echouee.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo    Installation terminee! Lancement...
echo =====================================================
echo.
call "%BASE%LANCER_STEG.bat"
