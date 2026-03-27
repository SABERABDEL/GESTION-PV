# -*- mode: python ; coding: utf-8 -*-
# STEG_PV.spec - Fichier de configuration PyInstaller
# Usage: pyinstaller STEG_PV.spec

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collecter tous les fichiers Flask/Jinja2/Werkzeug
flask_datas, flask_binaries, flask_hiddenimports = collect_all('flask')
jinja_datas, jinja_binaries, jinja_hiddenimports = collect_all('jinja2')
werk_datas, werk_binaries, werk_hiddenimports = collect_all('werkzeug')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=flask_binaries + jinja_binaries + werk_binaries,
    datas=[
        ('templates', 'templates'),       # Templates HTML
        ('data/bibliotheque.json', 'data'), # Bibliothèque JSON
    ] + flask_datas + jinja_datas + werk_datas,
    hiddenimports=[
        'flask', 'flask.templating', 'flask.json',
        'jinja2', 'jinja2.ext',
        'werkzeug', 'werkzeug.serving', 'werkzeug.routing',
        'werkzeug.middleware.proxy_fix',
        'click', 'itsdangerous', 'markupsafe',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
        'openpyxl.styles.fonts', 'openpyxl.styles.fills',
        'sqlite3', '_sqlite3',
        'webbrowser', 'threading', 'socket',
        'email', 'email.mime', 'http', 'urllib',
    ] + flask_hiddenimports + jinja_hiddenimports + werk_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'PIL', 'cv2'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='STEG_PV',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # True = fenêtre console visible (utile pour voir erreurs)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='steg_icon.ico',  # Décommentez si vous avez une icône
)
