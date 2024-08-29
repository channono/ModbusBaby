import sys
import os
import logging
import argparse
import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from gui import ModbusBabyGUI

if __name__ == "__main__":
    print("Starting application...")
    main()
    print("Application finished.")
# 添加当前目录到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from gui import ModbusBabyGUI
from PyQt6.QtWidgets import QApplication

def setup_logging(level, log_file):
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_dir = os.path.expanduser('~/ModbusBaby_logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_path = os.path.join(log_dir, log_file)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def get_resource_path(filename):
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "resources", filename)

def parse_arguments():
    parser = argparse.ArgumentParser(description="ModbusBaby - Modbus调试器")
    parser.add_argument("--log-level", default="INFO", help="设置日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument("--log-file", default="modbusbaby.log", help="指定日志文件路径")
    parser.add_argument("--config", default=get_resource_path("config.json"), help="指定配置文件路径")
    return parser.parse_args()

def load_config(config_path):
    if not config_path or not os.path.exists(config_path):
        logging.warning(f"配置文件不存在: {config_path}")
        return {}
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return {}

def save_window_state(window):
    settings = QSettings("ModbusBaby", "WindowState")
    settings.setValue("geometry", window.saveGeometry())
    settings.setValue("windowState", window.saveState())

def restore_window_state(window):
    settings = QSettings("ModbusBaby", "WindowState")
    geometry = settings.value("geometry")
    if geometry:
        window.restoreGeometry(geometry)
    state = settings.value("windowState")
    if state:
        window.restoreState(state)

def main():
    # 解析命令行参数
    args = parse_arguments()

    # 设置日志
    setup_logging(args.log_level, "modbusbaby.log")
    logger = logging.getLogger(__name__)
    logger.info("启动 ModbusBaby 应用程序")

    # 加载配置
    logger.debug(f"尝试加载配置文件: {args.config}")
    config = load_config(args.config)
    logger.info(f"加载配置: {config}")

    # 创建 QApplication 实例
    app = QApplication(sys.argv)

    try:
        # 创建并显示主窗口
        window = ModbusBabyGUI(config)
        restore_window_state(window)
        window.show()

        # 设置应用程序图标
        icon_path = get_resource_path("modbusbaby_icon.png")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(icon_path))

        # 运行应用程序的主循环
        exit_code = app.exec()
        # 保存窗口状态
        save_window_state(window)
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"应用程序运行时发生错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("应用程序已关闭")

if __name__ == "__main__":
    main()