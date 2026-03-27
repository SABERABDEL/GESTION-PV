@echo off
chcp 1252 >nul 2>&1
title STEG PV - Installation bibliotheques
color 1F

SET "BASE=%~dp0"
SET "STATIC=%BASE%static"
SET "PEMBED=%BASE%python_embed\python.exe"
SET "VEXE=%BASE%venv\Scripts\python.exe"

echo.
echo =====================================================
echo    STEG PV - Telechargement librairies locales
echo =====================================================
echo.
echo Cette operation necessite une connexion Internet.
echo.

IF EXIST "%PEMBED%" (SET "PY=%PEMBED%") ELSE IF EXIST "%VEXE%" (SET "PY=%VEXE%") ELSE (SET "PY=python")

"%PY%" -c "
import os, urllib.request

BASE = r'%BASE%'
STATIC = os.path.join(BASE, 'static')

libs = {
    'css/bootstrap.min.css':       'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'js/bootstrap.bundle.min.js':  'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'fa/css/all.min.css':          'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
    'js/xlsx.full.min.js':         'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js',
    'js/qrcode.min.js':            'https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js',
    'js/chart.min.js':             'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js',
}
webfonts = ['fa-solid-900.woff2','fa-solid-900.woff','fa-solid-900.ttf','fa-regular-400.woff2','fa-regular-400.woff','fa-brands-400.woff2','fa-brands-400.ttf']
for wf in webfonts:
    libs[f'fa/webfonts/{wf}'] = f'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/{wf}'

ok = 0
fail = 0
for rel, url in libs.items():
    dest = os.path.join(STATIC, rel.replace('/', os.sep))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 100:
        print(f'  [DEJA OK] {rel}')
        ok += 1
        continue
    try:
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f'  [OK] {rel} ({size//1024} KB)')
        ok += 1
    except Exception as e:
        print(f'  [ECHEC] {rel}: {e}')
        fail += 1

print(f'\nResultat: {ok} OK, {fail} echec(s)')
if fail == 0:
    print('Toutes les librairies sont installes!')
"

echo.
pause
