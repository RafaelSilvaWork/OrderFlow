# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Coupa Framework / OrderFlow - Automação de Suprimentos
#
# Duas variantes (ver modules/branding.py) a partir do mesmo código, escolhida
# pela env var CFW_BRANDING ("hapvida", padrão, ou "generic") - só o nome do
# executável e os assets de marca (ícone/splash) mudam entre elas; nenhum
# código de negócio é diferente.

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

BRANDING = os.environ.get("CFW_BRANDING", "hapvida").strip().lower()
IS_GENERIC = BRANDING == "generic"
APP_EXE_NAME = "OrderFlow" if IS_GENERIC else "CoupaFramework"
BRANDING_ASSETS_DIR = f"assets/branding/{'generic' if IS_GENERIC else 'hapvida'}"

datas = []
datas += collect_data_files('fitz')         # PyMuPDF
datas += collect_data_files('PIL')
datas += collect_data_files('numpy')
datas += collect_data_files('pandas')
datas += collect_data_files('openpyxl')
datas += collect_data_files('docx')
datas += collect_data_files('pptx')
datas += collect_data_files('cryptography')
datas += collect_data_files('keyring')

# Inclui arquivos do projeto
datas += [
    ('modules', 'modules'),
    # Só os assets da marca ATIVA são empacotados - empacotar as duas pastas
    # sempre vazaria a marca do Hapvida dentro do instalador genérico (e
    # vice-versa), além de inchar o pacote à toa. icon.ico também precisa
    # estar disponível como arquivo em runtime (QApplication.setWindowIcon
    # em main.py, via resolve_asset_path) - o icon= do EXE() abaixo só
    # embute o ícone no .exe em si, não deixa o arquivo disponível pro app ler.
    (f'{BRANDING_ASSETS_DIR}/logo_pecas', f'{BRANDING_ASSETS_DIR}/logo_pecas'),
    (f'{BRANDING_ASSETS_DIR}/icon.ico', BRANDING_ASSETS_DIR),
]

# Tesseract (OCR de PDF escaneado, ver modules/download_scraper.py) - o
# workflow de release baixa e monta essa pasta antes de compilar (não é
# versionada no git, é pesada demais). Em build local sem essa pasta, o
# app simplesmente roda sem o Tesseract empacotado (cai no do PATH, se
# houver um instalado manualmente) - ver resolve_tesseract_executable.
if os.path.isdir('tesseract_bundle'):
    datas += [('tesseract_bundle', 'tesseract')]

hiddenimports = []
hiddenimports += collect_submodules('PyQt6')
hiddenimports += collect_submodules('cryptography')
hiddenimports += collect_submodules('keyring')
hiddenimports += collect_submodules('PIL')
hiddenimports += collect_submodules('numpy')
hiddenimports += [
    'requests',
    'numpy',
    'pandas',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'docx',
    'pptx',
    'fitz',
    'pytesseract',
    'filelock',
    'win32com',
    'win32com.client',
    'pythoncom',
    'pywintypes',
    'pypdf',
    'asyncio',
    'playwright',
    'playwright.async_api',
    'playwright.sync_api',
    'email.mime.multipart',
    'email.mime.text',
    'email.mime.base',
    'email.encoders',
    'logging.handlers',
    'logging.config',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'wx',
        'gi',
        'gtk',
        'test',
        'unittest',
        'xmlrpc',
        'ftplib',
        'imaplib',
        'poplib',
        'telnetlib',
        'turtle',
        'curses',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    icon=f'{BRANDING_ASSETS_DIR}/icon.ico',
    # UPX pode corromper DLLs do Qt e do Playwright — excluir explicitamente
    upx_exclude=[
        'Qt6*.dll',
        'PyQt6*.dll',
        '*.pyd',
        'node.exe',          # driver do Playwright
        'msedge*.dll',
    ],
    console=False,            # Sem janela de console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'Qt6*.dll',
        'PyQt6*.dll',
        '*.pyd',
        'node.exe',
        'msedge*.dll',
    ],
    name=APP_EXE_NAME,
)