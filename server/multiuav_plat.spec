from pathlib import Path
import re
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


if "SPEC" in globals():
    PROJECT_ROOT = Path(SPEC).resolve().parent
else:
    PROJECT_ROOT = Path.cwd().resolve()

main_py = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
version_match = re.search(r'^VERSION\s*=\s*"([^"]+)"', main_py, re.MULTILINE)
if not version_match:
    raise RuntimeError("Could not infer VERSION from main.py")
version = version_match.group(1)
major, minor, patch = version.split(".")
app_version = f"{major}.{minor}{patch}"
APP_NAME = f"MultiUAV-Plat.Server.v{app_version}"

if sys.platform == "win32":
    ICON_PATH = PROJECT_ROOT / "ui" / "img" / "drone.ico"
elif sys.platform == "darwin":
    ICON_PATH = PROJECT_ROOT / "ui" / "img" / "drone.icns"
else:
    ICON_PATH = None

datas = []
for folder in ("config", "models", "controllers", "api", "ui"):
    datas.append((str(PROJECT_ROOT / folder), folder))

datas += collect_data_files("fastapi")
datas += collect_data_files("pygame")
datas += collect_data_files("uvicorn")

hiddenimports = sorted(
    set(
        collect_submodules("api")
        + collect_submodules("config")
        + collect_submodules("controllers")
        + collect_submodules("models")
        + collect_submodules("ui")
        + collect_submodules("fastapi")
        + collect_submodules("pygame")
        + collect_submodules("uvicorn")
    )
)


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=APP_NAME,
    icon=str(ICON_PATH) if ICON_PATH and ICON_PATH.exists() else None,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
