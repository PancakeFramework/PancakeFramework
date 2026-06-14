"""杂项命令：version, cover, update, install"""

import subprocess
import sys

from .utils import get_version
from pancake.exceptions import DependencyError


def cmd_version(args):
    """显示框架版本"""
    print(f"Pancake Framework v{get_version()}")


def cmd_cover(args):
    """显示 Pancake 封面"""
    from pancake.initialize.print_ico import print_cover
    print_cover()


def cmd_update(args):
    """更新 pancake_framework 包"""
    print("正在更新 Pancake Framework...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "pancake_framework"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("更新成功!")
        new_ver = get_version()
        print(f"当前版本: v{new_ver}")
        if result.stdout:
            print(result.stdout)
    else:
        raise DependencyError(f"更新失败: {result.stderr}")


_PKG_TO_MODULE = {
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "python-dateutil": "dateutil",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
}


def cmd_install(args):
    """安装缺失依赖"""
    print("检查依赖...")

    core_deps = [
        "pyyaml", "python-dotenv",
        "databases", "aiosqlite",
    ]

    missing = []
    for dep in core_deps:
        module = _PKG_TO_MODULE.get(dep, dep.replace("-", "_").replace("python_", ""))
        try:
            __import__(module)
        except ImportError:
            missing.append(dep)

    if not missing:
        print("  核心依赖已全部安装")
        return

    print(f"  缺失: {', '.join(missing)}")
    print("正在安装...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install"] + missing,
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("安装成功!")
    else:
        raise DependencyError(f"安装失败: {result.stderr}")
