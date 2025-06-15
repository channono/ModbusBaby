#大牛大巨婴
import os
import sys
import json
from PyQt6.QtWidgets import QApplication
from gui import ModbusBabyGUI
from utils import resource_path as get_resource_path # Use centralized resource_path

def load_config():
    try:
        config_path = get_resource_path('config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError: 
        return {}


def main():
    app = QApplication(sys.argv)
    config = load_config()
    window = ModbusBabyGUI(config)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()