# wave.spec — PyInstaller onedir bundle (dev/debug friendly).
# Build with: uv run poe build
# Output: dist/Wave/Wave (plus libs beside it)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("assets/icons", "assets/icons")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Wave",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Wave",
)
