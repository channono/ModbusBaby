from setuptools import setup

APP = ['src/main.py']  # 替换为您的主脚本文件名
DATA_FILES = [
    ('resources', ['resources/modbuslogo.png'])
]
OPTIONS = {
    'packages': ['PyQt6'],
    'includes': ['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets'],
    'iconfile': 'resources/modbusbaby_icon.png',  # 如果您有应用图标
    'plist': {
        'CFBundleName': 'ModbusBaby',
        'CFBundleDisplayName': 'ModbusBaby',
        'CFBundleGetInfoString': "",
        'CFBundleIdentifier': "",
        'CFBundleVersion': "0.1.0",
        'CFBundleShortVersionString': "0.1.0",
        'NSHumanReadableCopyright': u"Copyright © 2024, 大牛大巨婴, All Rights Reserved"
    },
    'arch': 'universal2',
    'strip': False,
}
try:
    setup(
        name='ModbusBaby',
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app'],
    )
except Exception as e:
    print(f"构建过程中出错: {e}")
    sys.exit(1)