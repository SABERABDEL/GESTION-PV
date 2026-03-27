@echo off
chcp 1252 >nul 2>&1
title STEG PV - Pare-feu
net session >nul 2>&1
IF %ERRORLEVEL% EQU 0 goto :has_admin
powershell -NoProfile -Command "Start-Process '%~f0' -Verb RunAs"
exit /b
:has_admin
echo.
echo STEG PV - Ouverture du port 5000 dans le pare-feu
echo.
netsh advfirewall firewall delete rule name="STEG_PV_HTTP" >nul 2>&1
netsh advfirewall firewall add rule name="STEG_PV_HTTP" dir=in action=allow protocol=TCP localport=5000 profile=any
IF %ERRORLEVEL% EQU 0 (echo [OK] Port 5000 ouvert - Acces Android/reseau actif) ELSE (echo [ERREUR] Echec)
echo.
pause
