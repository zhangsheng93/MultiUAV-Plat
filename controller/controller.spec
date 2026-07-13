# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for UAV Controller
This file ensures all necessary modules and data files are included in the executable.

To build the executable, run from the project root:
    pyinstaller uav_controller.spec

Why this spec file is needed:
1.  The `session_editor` is loaded dynamically using `importlib`, so PyInstaller's
    static analysis cannot find it.
2.  The session editor uses `pygame`, which also becomes a hidden import.
3.  Data files used at runtime (images, docs, settings) must be explicitly included.
"""

from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path
import importlib.util
import sys

block_cipher = None
SPEC_DIR = Path(SPECPATH).resolve()


def load_version() -> str:
    version_path = SPEC_DIR / 'app_version.py'
    spec = importlib.util.spec_from_file_location('uav_controller_version', version_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load version from {version_path}')

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VERSION


VERSION = load_version()


def exe_version_name(version: str) -> str:
    parts = version.split('.')
    if len(parts) <= 1:
        return version
    return f"{parts[0]}.{''.join(parts[1:])}"

# Hidden imports are modules that are not explicitly imported in the code
# but are required at runtime. PyInstaller's analysis can sometimes miss these.
hidden_imports = [
    'session_editor',  # Dynamically imported by main.py and gui_controller.py
    'pygame',          # A dependency of session_editor
    'PIL',             # Pillow, often used with pygame and can be a hidden import
    # Add tkinter modules that might be missed
    'tkinter.filedialog',
    'tkinter.simpledialog',
    'tkinter.messagebox',
    # Common problem package with some libraries
    'pkg_resources.py2_warn'
]
hidden_imports += collect_submodules('check_ui')

# The 'datas' list tells PyInstaller what non-code files to bundle.
# It's a list of tuples, where each tuple is ('source', 'destination_in_bundle').
datas = [
    ('img', 'img'),  # Bundle the entire 'img' directory
    ('settings.json', '.'),  # Bundle the settings file into the root
    ('API_doc', 'API_doc'),  # Bundle the API documentation
    ('LICENSE', '.'),
    ('README.md', '.'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=f'MultiUAV-Plat.Controller.v{exe_version_name(VERSION)}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    # 'console=True' ensures the terminal/console window is visible when the app runs,
    # which is useful for viewing log output.
    console=True,
    disable_windowing_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='img/controller.ico',
)
