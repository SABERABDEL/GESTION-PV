@echo off
chcp 1252 >nul 2>&1
title STEG PV - Preparation hors ligne
color 2F

SET "BASE=%~dp0"
SET "WHEELS=%BASE%wheels"

echo.
echo =====================================================
echo    STEG PV - Preparation pour PC sans Internet
echo    Executez ce script sur un PC AVEC Internet
echo =====================================================
echo.

IF NOT EXIST "%WHEELS%" mkdir "%WHEELS%"

pip --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERREUR] pip introuvable. Installez Python d abord.
    pause
    exit /b 1
)

echo Telechargement des paquets...
pip download flask werkzeug openpyxl -d "%WHEELS%" --platform win_amd64 --python-version 311 --only-binary=:all: -q 2>nul
IF ERRORLEVEL 1 (
    echo Tentative sans contrainte plateforme...
    pip download flask werkzeug openpyxl -d "%WHEELS%" -q
)

echo.
echo [OK] Paquets dans: %WHEELS%
echo.
echo Copiez maintenant tout le dossier STEG PV sur
echo les autres PC et lancez INSTALLER_OFFLINE.bat
echo.
pause
