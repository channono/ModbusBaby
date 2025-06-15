# -*- mode: python ; coding: utf-8 -*-

# This is the Analysis block. It analyzes your main script and its dependencies.
a = Analysis(
    ['src/main.py'],  # Main script of your application. Path is relative to this .spec file.
    pathex=['src'],   # List of paths where PyInstaller will look for modules. 'src' for your source layout.
    binaries=[
        ('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation', '.'),
        ('/System/Library/Frameworks/IOKit.framework/IOKit', '.'),
        ('/System/Library/Frameworks/Security.framework/Security', '.')
    ],      # List of non-Python binaries to include (e.g., .dll, .so).
    datas=[           # List of data files or directories to include.
        ('resources', 'resources'),  # Copies 'resources' folder (source) to 'resources' (destination in app).
        ('config.json', '.'),        # Copies 'config.json' (source) to the root ('.') (destination in app).
        ('rthook.py', '.')          # Include the runtime hook in the package
    ],
    hiddenimports=[
        'serial',
        'serial.tools.list_ports',
        'serial.tools.list_ports_osx',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui'
    ], # Add all required modules
    hookspath=[],     # Paths to custom PyInstaller hooks.
    hooksconfig={},   # Configuration for hooks.
    runtime_hooks=['rthook.py'], # Scripts to run at runtime before your main script.
    excludes=[],      # Modules to exclude from the bundle.
    noarchive=False,  # If True, Python scripts are not put into a PYZ archive.
    optimize=0        # Python bytecode optimization level (0, 1, or 2).
)

# This creates a PYZ archive from the pure Python modules found by Analysis.
pyz = PYZ(a.pure)

# This creates the executable file.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ModbusBaby',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None  # We'll handle code signing separately
)

# This collects all necessary files into a directory structure for the application.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ModbusBaby'
)

# This creates the macOS .app bundle.
app = BUNDLE(
    coll,
    name='ModbusBaby.app',
    icon='MyIcon.icns',
    bundle_identifier='com.biggiantbaby.modbusbaby',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'LSApplicationCategoryType': 'public.app-category.developer-tools',
    }
)
