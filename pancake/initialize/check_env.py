import subprocess
import sys
import os
import platform
import logging

from pancake.exceptions import DependencyError

logger = logging.getLogger(__name__)


def check_poetry_installed() -> bool:
    """检查 Poetry 是否已安装"""
    try:
        subprocess.run(
            ["poetry", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_poetry():
    """跨平台自动安装 Poetry"""
    print("正在安装 Poetry...")
    os_name = platform.system()

    try:
        if os_name == "Windows":
            install_cmd = "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
            subprocess.run(["powershell", "-Command", install_cmd], check=True, shell=True)
        else:
            subprocess.run(["curl", "-sSL", "https://install.python-poetry.org"], check=True)
        print("Poetry 安装成功！")
    except subprocess.CalledProcessError:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "poetry"], check=True)
        except subprocess.CalledProcessError as e:
            raise DependencyError(f"Poetry 安装失败: {e}") from e


def setup_current_directory(dependencies: list):
    """直接在当前目录初始化环境"""
    current_dir = os.getcwd()
    print(f"当前工作目录: {current_dir}")

    # 1. 初始化 Poetry
    print("正在初始化 Poetry...")
    subprocess.run(["poetry", "init", "-n"],
        capture_output=True,
        text=True)

    # 2. 配置虚拟环境在当前目录下 (.venv)
    print("配置虚拟环境路径...")
    subprocess.run(["poetry", "config", "virtualenvs.in-project", "true", "--local"], check=True)

    # 3. 安装依赖
    if dependencies:
        print(f"正在安装依赖: {dependencies}")
        subprocess.run(["poetry", "add"] + dependencies, capture_output=True, text=True)

    print("\n环境配置完成！")
    print(f"虚拟环境位置: {os.path.join(current_dir, '.venv')}")

def find_module(module_names: list) -> bool:
    """检查模块是否已安装"""
    import importlib.util

    for module_name in module_names:
        spec = importlib.util.find_spec(module_name)

        if spec is None:
            return False
    return True


def check_environment():
    """检查运行环境"""
    REQUIRED_LIBRARIES = ["python-dotenv", "pyyaml"]
    REQUIRED_MODULES = ["dotenv", "yaml"]
    if not find_module(REQUIRED_MODULES):
        # Check for non-interactive mode
        if os.getenv("PANCAKE_AUTO_INSTALL", "").lower() in ("1", "true", "yes"):
            auto_install = True
        elif not sys.stdin.isatty():
            raise DependencyError(
                "缺少必要的库，且运行在非交互模式。请设置 PANCAKE_AUTO_INSTALL=1 自动安装，或手动运行: pip install python-dotenv pyyaml"
            )
        else:
            auto_install = input("缺少必要的库，是否自动安装？ (y/n)").lower().startswith("y")

        if not auto_install:
            raise DependencyError("缺少必要的库: python-dotenv, pyyaml。请运行: pip install python-dotenv pyyaml")

        # 1. 检查 Poetry
        if not check_poetry_installed():
            install_poetry()
            if platform.system() == "Windows":
                import ctypes
                ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 0x0002, 5000, None)
            else:
                os.environ["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{os.environ['PATH']}"

        # 2. 直接在当前目录搭建
        setup_current_directory(REQUIRED_LIBRARIES)

        print("环境配置完成！", f"虚拟环境位置: {os.path.join(os.getcwd(), '.venv')}")
        raise DependencyError("环境配置完成，请重新启动项目: poetry run python main.py")
