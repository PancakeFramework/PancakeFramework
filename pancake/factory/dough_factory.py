"""
DoughFactory — Bean 工厂
替代原有 oven 模块，统一管理所有 Bean
"""

import asyncio
import inspect
import logging
from pancake.dough import Dough, Scope, _call_lifecycle

logger = logging.getLogger(__name__)


class DoughFactory:
    """Bean 工厂 — 管理 Bean 的注册、创建、生命周期

    支持多个独立工厂实例。
    生命周期方法支持同步和异步实现。
    """

    _factories: dict[str, "DoughFactory"] = {}

    def __init__(self, name: str = "default"):
        self.name = name
        self._classes: dict[str, type] = {}
        self._instances: dict[str, Dough] = {}
        self._load_order: list[str] = []
        DoughFactory._factories[name] = self

    @staticmethod
    def get(name: str = "default") -> "DoughFactory":
        """获取或创建工厂实例"""
        if name not in DoughFactory._factories:
            DoughFactory._factories[name] = DoughFactory(name)
        return DoughFactory._factories[name]

    def register(self, cls: type):
        """注册 Bean 类"""
        name = cls.__name__
        self._classes[name] = cls
        logger.debug(f"注册 Bean: {name}")

    def register_instance(self, name: str, instance: object):
        """注册已创建的实例"""
        self._instances[name] = instance
        logger.debug(f"注册实例: {name}")

    def resolve(self, name: str) -> Dough:
        """获取 Bean 实例"""
        # 已有实例
        if name in self._instances:
            instance = self._instances[name]
            # Prototype 每次返回新实例
            if hasattr(instance, '_scope') and instance._scope == Scope.PROTOTYPE:
                cls = self._classes.get(name)
                if cls:
                    return cls()
            return instance

        # Lazy 创建
        cls = self._classes.get(name)
        if cls is None:
            raise ValueError(f"未注册的 Bean: {name}")

        if cls._scope == Scope.LAZY:
            instance = cls()
            self._instances[name] = instance
            # Lazy 的 on_init 需要在事件循环中调用
            return instance

        raise ValueError(f"Bean {name} 尚未创建，请先调用 create_all()")

    def _resolve_dependency_order(self) -> list[str]:
        """拓扑排序确定 Bean 创建顺序（依赖优先）

        使用 Kahn 算法：先计算入度，再依次取出入度为 0 的节点。
        LAZY Bean 不参与排序（延迟创建）。
        """
        deps: dict[str, list[str]] = {}
        for name, cls in self._classes.items():
            if cls._scope == Scope.LAZY:
                continue
            deps[name] = getattr(cls, '_depends_on', [])

        in_degree: dict[str, int] = {name: 0 for name in deps}
        for name, dep_list in deps.items():
            for dep in dep_list:
                if dep in in_degree:
                    in_degree[name] += 1

        queue = [name for name, degree in in_degree.items() if degree == 0]
        order: list[str] = []

        while queue:
            queue.sort()
            node = queue.pop(0)
            order.append(node)

            for name, dep_list in deps.items():
                if node in dep_list:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(order) != len(deps):
            remaining = [n for n in deps if n not in order]
            raise ValueError(f"检测到循环依赖: {remaining}")

        return order

    # ---- 同步 API（兼容） ----

    def create_all(self):
        """创建所有注册的 Bean（同步版本，仅适用于纯同步生命周期）

        如果生命周期方法是 async 的，请使用 async_create_all()。
        """
        for name, cls in list(self._classes.items()):
            imports = getattr(cls, '_imports', [])
            for imported_cls in imports:
                if imported_cls.__name__ not in self._classes:
                    self.register(imported_cls)

        order = self._resolve_dependency_order()

        for name in order:
            cls = self._classes[name]
            try:
                instance = cls()
                self._instances[name] = instance
                self._load_order.append(name)
                # 同步调用 on_init（仅当方法不是 async 时）
                method = getattr(instance, 'on_init', None)
                if method and not inspect.iscoroutinefunction(method):
                    method()
                logger.debug(f"创建 Bean: {name}")
            except Exception as e:
                logger.error(f"创建 Bean {name} 失败: {e}")
                raise

    def startup_all(self):
        """执行所有 Bean 的 on_start（同步版本）"""
        for name in self._load_order:
            instance = self._instances.get(name)
            if instance:
                try:
                    method = getattr(instance, 'on_start', None)
                    if method and not inspect.iscoroutinefunction(method):
                        method()
                    logger.debug(f"启动 Bean: {name}")
                except Exception as e:
                    logger.error(f"启动 Bean {name} 失败: {e}")
                    raise

    def shutdown_all(self):
        """逆序执行 on_stop 和 on_destroy（同步版本）"""
        for name in reversed(self._load_order):
            instance = self._instances.get(name)
            if instance:
                try:
                    on_stop = getattr(instance, 'on_stop', None)
                    on_destroy = getattr(instance, 'on_destroy', None)
                    if on_stop and not inspect.iscoroutinefunction(on_stop):
                        on_stop()
                    if on_destroy and not inspect.iscoroutinefunction(on_destroy):
                        on_destroy()
                    logger.debug(f"关闭 Bean: {name}")
                except Exception as e:
                    logger.error(f"关闭 Bean {name} 失败: {e}")

        self._instances.clear()
        self._load_order.clear()

    # ---- 异步 API ----

    async def async_create_all(self):
        """创建所有注册的 Bean（异步版本，支持 async 生命周期）

        1. 处理 @Import：自动注册外部类
        2. 拓扑排序确定创建顺序
        3. 按顺序创建 Bean 并调用 on_init
        """
        for name, cls in list(self._classes.items()):
            imports = getattr(cls, '_imports', [])
            for imported_cls in imports:
                if imported_cls.__name__ not in self._classes:
                    self.register(imported_cls)

        order = self._resolve_dependency_order()

        for name in order:
            cls = self._classes[name]
            try:
                instance = cls()
                self._instances[name] = instance
                self._load_order.append(name)
                await _call_lifecycle(instance, 'on_init')
                logger.debug(f"创建 Bean: {name}")
            except Exception as e:
                logger.error(f"创建 Bean {name} 失败: {e}")
                raise

    async def async_startup_all(self):
        """执行所有 Bean 的 on_start（异步版本）"""
        for name in self._load_order:
            instance = self._instances.get(name)
            if instance:
                try:
                    await _call_lifecycle(instance, 'on_start')
                    logger.debug(f"启动 Bean: {name}")
                except Exception as e:
                    logger.error(f"启动 Bean {name} 失败: {e}")
                    raise

    async def async_shutdown_all(self):
        """逆序执行 on_stop 和 on_destroy（异步版本）"""
        for name in reversed(self._load_order):
            instance = self._instances.get(name)
            if instance:
                try:
                    await _call_lifecycle(instance, 'on_stop')
                    await _call_lifecycle(instance, 'on_destroy')
                    logger.debug(f"关闭 Bean: {name}")
                except Exception as e:
                    logger.error(f"关闭 Bean {name} 失败: {e}")

        self._instances.clear()
        self._load_order.clear()

    # ---- 查询 API ----

    def build_all(self):
        """执行所有 Bean 的 build（兼容旧插件）"""
        pass

    def get_all_instances(self) -> dict[str, Dough]:
        """获取所有已创建的实例"""
        return dict(self._instances)

    def get_all_classes(self) -> dict[str, type]:
        """获取所有注册的类"""
        return dict(self._classes)
