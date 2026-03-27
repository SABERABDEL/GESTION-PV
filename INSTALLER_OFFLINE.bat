@echo off
chcp 1252 >nul 2>&1
title STEG PV - Installation Hors Ligne
color 1F

SET "BASE=%~dp0"
SET "PYDIR=%BASE%python_embed"
SET "PYEXE=%PYDIR%\python.exe"
SET "WHEELS=%BASE%wheels"

echo.
echo =====================================================
echo    STEG PV - Installation HORS LIGNE
echo =====================================================
echo.

IF NOT EXIST "%WHEELS%" (
    echo [ERREUR] Dossier 'wheels' manquant.
    echo.
    echo Sur un PC avec Internet, lancez d abord:
    echo   PREPARER_WHEELS.bat
    echo.
    pause
    exit /b 1
)

IF NOT EXIST "%PYEXE%" (
    echo [ERREUR] Dossier 'python_embed' manquant.
    echo.
    echo Copiez le dossier python_embed depuis un autre PC
    echo ou utilisez INSTALLER.bat sur un PC avec Internet.
    echo.
    pause
    exit /b 1
)

findstr "import site" "%PYDIR%\python311._pth" >nul 2>&1
IF ERRORLEVEL 1 echo import site>> "%PYDIR%\python311._pth"

echo Installation des paquets locaux...
"%PYEXE%" -m pip install --no-index --find-links="%WHEELS%" flask werkzeug openpyxl --no-warn-script-location -q

IF ERRORLEVEL 1 (
    echo [ERREUR] Installation echouee.
    pause
    exit /b 1
)

echo.
echo [OK] Installation terminee!
echo Utilisez LANCER_STEG.bat pour demarrer.
echo.
pause
