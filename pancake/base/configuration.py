"""Configuration 基类"""

import inspect
from pancake.dough import Dough


class Configuration(Dough):
    """配置类 — 非私有方法返回值自动注册为 Bean

    规则:
    1. 非私有方法自动扫描
    2. 返回值必须是对象（非 str/int/float/bool/None）
    3. @noMaker 装饰器可排除特定方法
    """

    async def on_init(self):
        from pancake.factory.dough_factory import DoughFactory

        # 收集基类中定义的方法名，避免递归调用 on_init 等生命周期方法
        base_methods = set()
        for base in type(self).__mro__[1:]:
            base_methods.update(base.__dict__.keys())

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("_"):
                continue
            if name in base_methods:
                continue
            if hasattr(method, "_no_maker"):
                continue
            # 支持 sync 和 async 的 maker 方法
            if inspect.iscoroutinefunction(method):
                result = await method()
            else:
                result = method()
            if result is not None and not isinstance(result, (str, int, float, bool)):
                DoughFactory.get().register_instance(name, result)
