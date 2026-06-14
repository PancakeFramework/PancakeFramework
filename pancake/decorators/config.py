"""配置与依赖装饰器 — @config, @depends_on, @import_class"""

import functools
import inspect
from pancake.registry import export


@export
def config(cls):
    """@config — 从配置注入 Struct 字段"""
    original_on_init = cls.on_init

    @functools.wraps(original_on_init)
    async def new_on_init(self):
        from pancake import settings
        for field_name in getattr(cls, '__dataclass_fields__', {}):
            if field_name.startswith("_"):
                continue
            config_key = f"{cls.__name__.lower()}.{field_name}"
            value = settings.get(config_key)
            if value is not None:
                setattr(self, field_name, value)
        if inspect.iscoroutinefunction(original_on_init):
            await original_on_init(self)
        else:
            original_on_init(self)

    cls.on_init = new_on_init
    return cls


@export
def depends_on(*deps: str):
    """@depends_on — 声明 Bean 依赖

    告知 DoughFactory 在创建该 Bean 之前，
    必须先创建指定的依赖 Bean。

    Usage:
        @depends_on("DatabaseService", "CacheService")
        class MyService(Dough): ...
    """
    def decorator(cls):
        cls._depends_on = list(deps)
        return cls
    return decorator


@export
def import_class(*classes: type):
    """@import_class — 导入外部类到工厂

    在 DoughFactory.create_all() 阶段，自动将指定的外部类
    注册到工厂中，无需手动 register。

    Usage:
        @import_class(DatabaseService, CacheService)
        class AppConfig(Configuration): ...
    """
    def decorator(cls):
        cls._imports = list(classes)
        return cls
    return decorator
