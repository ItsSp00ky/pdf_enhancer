# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all

datas = [('scanner.ico', '.'), ('scanner.png', '.')]
binaries = []
hiddenimports = []

for pkg in ['customtkinter', 'tkinterdnd2', 'pypdfium2', 'pypdfium2_raw']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

excludes = [
    'unittest',
    'email',
    'http',
    'xmlrpc',
    'pydoc',
    'test',
    'sqlite3',
    'distutils',
    'setuptools',
    'pip',
    'PIL.AvifImagePlugin',
    'PIL.WebPImagePlugin',
    'PIL.FpxImagePlugin',
    'PIL.MicImagePlugin',
    'PIL.SunImagePlugin',
    'PIL.XpmImagePlugin',
    'numpy.f2py',
    'numpy.testing',
    'numpy.tests',
    'numpy.distutils',
    'asyncio',
    'curses',
    'zoneinfo',
    'lib2to3',
    'doctest',
    'pdb',
    'idlelib',
    'multiprocessing',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

# Platform-specific foreign binary pruning to reduce executable size
if sys.platform == 'win32':
    strip_keywords = ['ffmpeg', '_avif', 'avif', 'linux-', 'osx-', 'win-arm64', 'win-x86', '.so', '.dylib']
    a.binaries = [b for b in a.binaries if not any(k in b[0].lower() for k in strip_keywords)]
elif sys.platform.startswith('linux'):
    strip_keywords = ['ffmpeg', '_avif', 'avif', 'win-', 'osx-', 'linux-arm', '.dll', '.dylib']
    a.binaries = [b for b in a.binaries if not any(k in b[0].lower() for k in strip_keywords)]
elif sys.platform == 'darwin':
    strip_keywords = ['ffmpeg', '_avif', 'avif', 'win-', 'linux-', '.dll', '.so']
    a.binaries = [b for b in a.binaries if not any(k in b[0].lower() for k in strip_keywords)]

# Strip redundant Tcl encoding files & tests from GUI data to reduce bundle size
a.datas = [
    d for d in a.datas
    if not (
        '_tcl_data' in d[0] and (
            ('encoding' in d[0] and not any(enc in d[0].lower() for enc in ['ascii', 'utf-8', 'cp1252', 'iso8859-1']))
            or 'tcltest' in d[0].lower()
            or 'demos' in d[0].lower()
        )
    )
]

pyz = PYZ(a.pure, optimize=2)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='PDF_Enhancer_v1.1',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['scanner.ico'],
)
