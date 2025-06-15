#!/bin/bash

# 设置变量
APP_NAME="ModbusBaby"
DMG_NAME="${APP_NAME}_Installer"
DMG_FINAL="${DMG_NAME}.dmg"
VOLUME_NAME="${APP_NAME} Installer"

# 确保 dist 目录存在
if [ ! -d "dist" ]; then
    echo "Error: dist directory not found! Please build the app first."
    exit 1
fi

# 清理旧的 DMG 文件
rm -f "dist/${DMG_FINAL}"

# 设置变量
APP_NAME="ModbusBaby"
DMG_NAME="${APP_NAME}_Installer"
APP_PATH="dist/${APP_NAME}.app"
DMG_PATH="dist/${DMG_NAME}.dmg"

# 检查 .app 文件是否存在
if [ ! -d "${APP_PATH}" ]; then
    echo "错误：${APP_PATH} 不存在。请确保您已经构建了应用程序。"
    exit 1
fi

# 创建 DMG
create-dmg \
  --volname "${APP_NAME} Installer" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "${APP_NAME}.app" 175 120 \
  --hide-extension "${APP_NAME}.app" \
  --app-drop-link 425 120 \
  "${DMG_PATH}" \
  "${APP_PATH}"

# 检查是否成功
if [ $? -eq 0 ]; then
    echo "DMG 创建成功：${DMG_PATH}"
else
    echo "DMG 创建失败"
    exit 1
fi