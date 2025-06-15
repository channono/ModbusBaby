import os
import sys
import ctypes
import logging
import platform

# 设置日志记录
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.StreamHandler(sys.stderr)])

def load_framework(name):
    if platform.system() != 'Darwin':
        return None
        
    # 首先尝试从应用程序包中加载
    app_framework_path = os.path.join(
        os.path.dirname(sys.executable),
        '..',
        'Frameworks',
        f'{name}.framework',
        name
    )
    
    # 如果应用程序包中没有，则尝试从系统加载
    system_framework_path = f'/System/Library/Frameworks/{name}.framework/{name}'
    
    framework_paths = [app_framework_path, system_framework_path]
    
    for framework_path in framework_paths:
        try:
            if os.path.exists(framework_path):
                logging.debug(f"Loading framework: {framework_path}")
                framework = ctypes.CDLL(framework_path)
                logging.info(f"Successfully loaded {name} framework")
                return framework
        except Exception as e:
            logging.error(f"Error loading framework {name} from {framework_path}: {e}")
            
    logging.error(f"Framework not found: {name}")
    return None

def initialize_app():
    if platform.system() != 'Darwin':
        return

    # 加载必要的系统框架
    frameworks = ['CoreFoundation', 'IOKit', 'Security']
    for framework in frameworks:
        load_framework(framework)

    # 设置环境变量以确保正确的权限处理
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    
    # 确保当前工作目录设置正确
    if getattr(sys, 'frozen', False):
        # 如果是打包后的应用
        os.chdir(os.path.dirname(sys.executable))

# 执行初始化
initialize_app()

# Pre-load required frameworks
CoreFoundation = load_framework('CoreFoundation')
IOKit = load_framework('IOKit')

# 验证框架加载状态
if CoreFoundation and IOKit:
    logging.info("All required frameworks loaded successfully")
else:
    logging.warning("Some frameworks failed to load. Serial port functionality may be limited")
