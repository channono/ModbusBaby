#大牛大巨婴
import os
import sys
import json
import platform
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui import ModbusBabyGUI
from utils import resource_path as get_resource_path # Use centralized resource_path

# --- Start of Critical Change ---
# Configure logging at the very beginning of the application.
# This ensures that all loggers, including from libraries like pymodbus,
# will adhere to this configuration.
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# --- End of Critical Change ---

def check_permissions():
    if platform.system() == 'Darwin':
        try:
            # 检查是否有串口访问权限
            import serial.tools.list_ports
            serial.tools.list_ports.comports()
            
            # 检查是否有网络权限
            import socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.close()
            
            return True
        except Exception as e:
            logging.error(f"Permission error: {str(e)}")
            return False
    return True

def load_config():
    try:
        config_path = get_resource_path('config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError: 
        return {}


def main():
    app = QApplication(sys.argv)
    
    # 检查权限
    if not check_permissions():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("权限错误")
        msg.setInformativeText("应用程序需要串口和网络权限才能正常运行.\n请在系统偏好设置中允许这些权限。")
        msg.setWindowTitle("权限错误")
        msg.exec()
        return
    
    config = load_config()
    window = ModbusBabyGUI(config)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()