import sys
import os

def resource_path(relative_path):
    """ 获取资源的绝对路径，兼容开发模式和 PyInstaller 打包后的模式 """
    try:
        # PyInstaller 创建一个临时文件夹，并把路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        # 在开发模式下，我们假设脚本从项目根目录运行
        base_path = os.path.abspath(".")
    
    # 对于 src 布局，开发模式下的资源路径可能需要调整
    # 但由于我们把所有东西都打包到根目录，这个简单的实现通常就够了
    return os.path.join(base_path, relative_path)