#大牛大巨婴
import os
import sys
import json
from PyQt6.QtWidgets import QApplication
from gui import ModbusBabyGUI

def get_resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 如果是完全打包的应用程序
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境或别名模式
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)




def load_config():
    external_config_path = os.path.join(os.path.dirname(sys.executable),'config.json')
    if os.path.exists(external_config_path):
        config_path = external_config_path

    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    app = QApplication(sys.argv)
    config = load_config()
    window = ModbusBabyGUI(config)
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())