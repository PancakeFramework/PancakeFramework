"""
生命周期管理模块
支持节点的初始化、启动、停止、错误处理等钩子
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional
from contextlib import asynccontextmanager

from pancake import oven

logger = logging.getLogger(__name__)


class Lifecycle:
    """
    生命周期基类

    使用方法:
        @langgraph_node("worker")
        class WorkerNode(Lifecycle):
            async def on_init(self):
                self.db = await connect_db()

            async def on_start(self):
                await self.db.connect()

            async def process(self, state):
                return await self.db.query(...)

            async def on_stop(self):
                await self.db.close()
    """

    async def on_init(self) -> None:
        """初始化钩子 - 创建时调用"""
        pass

    async def on_start(self) -> None:
        """启动钩子 - 开始处理前调用"""
        pass

    async def on_stop(self) -> None:
        """停止钩子 - 停止处理时调用"""
        pass

    async def on_error(self, error: Exception) -> None:
        """错误钩子 - 发生错误时调用"""
        logger.error(f"生命周期错误: {error}")

    async def on_complete(self, result: Any = None) -> None:
        """完成钩子 - 处理完成后调用"""
        pass


# 注册到 muffin_water，使其被 embed 自动注入到 builtins
oven.muffin_water["Lifecycle"] = Lifecycle


class LifecycleManager:
    """生命周期管理器"""

    def __init__(self):
        self._instances: dict[str, Lifecycle] = {}
        self._initialized: set[str] = set()
        self._started: set[str] = set()

    async def register(self, name: str, instance: Lifecycle) -> None:
        """注册生命周期实例"""
        self._instances[name] = instance
        logger.info(f"注册生命周期实例: {name}")

    async def initialize(self, name: str = None) -> None:
        """初始化实例"""
        if name:
            instances = {name: self._instances[name]}
        else:
            instances = self._instances

        for n, instance in instances.items():
            if n not in self._initialized:
                try:
                    await instance.on_init()
                    self._initialized.add(n)
                    logger.info(f"初始化完成: {n}")
                except Exception as e:
                    await instance.on_error(e)
                    raise

    async def start(self, name: str = None) -> None:
        """启动实例"""
        if name:
            instances = {name: self._instances[name]}
        else:
            instances = self._instances

        for n, instance in instances.items():
            if n not in self._started:
                try:
                    await instance.on_start()
                    self._started.add(n)
                    logger.info(f"启动完成: {n}")
                except Exception as e:
                    await instance.on_error(e)
                    raise

    async def stop(self, name: str = None) -> None:
        """停止实例"""
        if name:
            instances = {name: self._instances[name]}
        else:
            instances = self._instances

        for n, instance in instances.items():
            if n in self._started:
                try:
                    await instance.on_stop()
                    self._started.discard(n)
                    logger.info(f"停止完成: {n}")
                except Exception as e:
                    await instance.on_error(e)

    async def shutdown_all(self) -> None:
        """关闭所有实例"""
        await self.stop()
        self._instances.clear()
        self._initialized.clear()
        self._started.clear()


# 全局管理器
lifecycle_manager = LifecycleManager()


def lifecycle_node(name: str = None):
    """
    生命周期节点装饰器

    自动管理节点的生命周期钩子
    """
    def decorator(cls):
        nonlocal name
        if name is None:
            name = cls.__name__

        # 检查是否是 Lifecycle 子类
        if not issubclass(cls, Lifecycle):
            raise TypeError(f"{cls.__name__} 必须继承 Lifecycle")

        @functools.wraps(cls)
        async def wrapper(*args, **kwargs):
            # 复用已有实例，避免每次调用都创建新对象
            instance = lifecycle_manager._instances.get(name)
            if instance is None:
                instance = cls(*args, **kwargs)
                await lifecycle_manager.register(name, instance)
                await lifecycle_manager.initialize(name)
                await lifecycle_manager.start(name)

            # 调用主处理方法
            if hasattr(instance, "process"):
                result = await instance.process(kwargs.get("state"))
                await instance.on_complete(result)
                return result
            else:
                raise AttributeError(f"{cls.__name__} 必须实现 process() 方法")

        # 注册到 langgraph 节点
        oven.pancake_dough.setdefault("langgraph_node", {})[name] = wrapper

        return wrapper
    return decorator


@asynccontextmanager
async def lifecycle_context():
    """
    生命周期上下文管理器

    使用方法:
        async with lifecycle_context():
            # 执行操作
            pass
        # 自动关闭所有实例
    """
    try:
        yield lifecycle_manager
    finally:
        await lifecycle_manager.shutdown_all()


class Main(InitAction):
    """生命周期管理插件主类"""

    name = "lifecycle"
    init_order = 10
    description = "生命周期管理: 节点初始化、启动、停止、错误处理钩子"

    def __init__(self):
        pass

    def build(self):
        logger.info("生命周期管理模块构建完成")
