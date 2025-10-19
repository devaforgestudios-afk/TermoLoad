# -*- mode: python ; coding: utf-8 -*-
# Optimized PyInstaller spec for TermoLoad - Fast startup and performance

block_cipher = None

# Exclude unnecessary modules to reduce size and improve startup
excludes = [
    'matplotlib',  # Heavy, only used if installed
    'numpy',       # Heavy, only used if installed
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    'pytest',
    'unittest',
    'doctest',
    'pdb',
    'pydoc',
    'xml.etree',
    'xmlrpc',
    'email',
    'ftplib',
    'http.server',
    'socketserver',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'textual',
        'textual.app',
        'textual.widgets',
        'textual.containers',
        'textual.screen',
        'aiohttp',
        'aiohttp.connector',
        'aiofiles',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'pystray',
        'tkinter',
        'tkinter.filedialog',
        'queue',
        'concurrent.futures',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=2,  # Python optimization level (-OO flag)
)

# Remove duplicate entries
a.datas = list({tuple(d) for d in a.datas})

pyz = PYZ(
    a.pure, 
    a.zipped_data, 
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TermoLoad',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Console mode for better performance and stability
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: icon='icon.ico'
    # Performance optimizations
    onefile=True,  # Single file for easier distribution
)
