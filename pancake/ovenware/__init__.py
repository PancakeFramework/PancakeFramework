from pancake import oven
import builtins
import logging

builtins.__dict__["oven"] = oven
builtins.__dict__["logging"] = logging

from abc import ABC, abstractmethod

# 导入 core 和 base 模块，确保基类和装饰器注册到 muffin_flour
from pancake.ovenware import core  # noqa: F401
from pancake.ovenware import base  # noqa: F401

logger = logging.getLogger(__name__)


def check_dependencies(deps: list[str], extras: str = None) -> bool:
    """
    统一依赖检查

    Args:
        deps: 需要检查的 Python 包名列表
        extras: pip extras 名称（如 "redis", "ai"）

    Returns:
        True = 全部可用, False = 有缺失
    """
    missing = []
    for dep in deps:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if not missing:
        return True
    msg = f"缺少可选依赖: {', '.join(missing)}"
    if extras:
        msg += f"，请运行: pip install pancake[{extras}]"
    logger.warning(msg)
    return False


class InitAction(ABC):
    """插件基类 — 所有 ovenware 插件必须继承此类

    生命周期顺序:
        1. __init__()  — 读取配置、初始化状态（加载阶段，按 init_order 排序）
        2. check()     — 环境/依赖检查（自动调用，返回 False 跳过此插件）
        3. build()     — 注册到 oven、构建组件（构建阶段，按 build_order 排序）
        4. startup()   — 应用启动时执行（async，注册到 on_startup）
        5. loop_method() — 长运行任务（如 uvicorn 服务器）
        6. shutdown()  — 应用关闭时执行（async，注册到 on_shutdown）
    """

    # === 元信息 ===
    name: str = ""                      # 插件名称（如 "web", "mybatis"）
    version: str = "0.1.0"              # 插件版本
    description: str = ""               # 插件描述

    # === 加载顺序 ===
    init_order: int = 0                 # 加载阶段顺序（值小先加载）
    build_order: int = 0                # 构建阶段顺序（值小先构建）

    # === 可选依赖 ===
    _dependencies: list[str] = []       # 需要的 Python 包名
    _extras: str = None                 # pip extras 名称（如 "redis", "ai"）

    @abstractmethod
    def __init__(self):
        """加载阶段：读取配置、初始化状态"""
        pass

    @abstractmethod
    def build(self):
        """构建阶段：注册到 oven、构建组件"""
        pass

    def check(self) -> bool:
        """环境检查（自动调用）

        返回 True 表示通过，False 表示跳过此插件。
        默认实现检查 _dependencies 是否可用。
        """
        if self._dependencies:
            return check_dependencies(self._dependencies, self._extras)
        return True

    async def startup(self):
        """应用启动时执行（可选）

        在 uvicorn event loop 中执行，适合初始化数据库连接等异步操作。
        基类会自动注册到 oven.muffin_egg["on_startup"]。
        """
        pass

    async def shutdown(self):
        """应用关闭时执行（可选）

        在 uvicorn event loop 关闭时执行，适合释放资源。
        基类会自动注册到 oven.muffin_egg["on_shutdown"]。
        """
        pass

    def loop_method(self):
        """长运行任务（可选）

        如 uvicorn 服务器启动。build 阶段后由 run.py 自动调用。
        """
        pass

    def get_info(self) -> dict:
        """返回插件元信息"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "init_order": self.init_order,
            "build_order": self.build_order,
            "dependencies": self._dependencies,
            "extras": self._extras,
        }


class Decorator(ABC):

    @abstractmethod
    def build(self):
        pass

builtins.__dict__["InitAction"] = InitAction
builtins.__dict__["Decorator"] = Decorator
builtins.__dict__["check_dependencies"] = check_dependencies

