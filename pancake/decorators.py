"""
Decorators — 框架装饰器
提供 @DoughDecorator、@Singleton、@Prototype、@Lazy、@Maker、@noMaker、
@inject、@Config、@DependsOn、@Import 等声明式装饰器
"""

import functools
import inspect
from pancake.dough import Scope


# ---- 类装饰器 ----


def DoughDecorator(cls):
    """@Dough — 标记类为 Bean"""
    cls._scope = Scope.SINGLETON
    return cls


def Singleton(cls):
    """@Singleton — 单例作用域"""
    cls._scope = Scope.SINGLETON
    return cls


def Prototype(cls):
    """@Prototype — 每次获取创建新实例"""
    cls._scope = Scope.PROTOTYPE
    return cls


def Lazy(cls):
    """@Lazy — 延迟初始化"""
    cls._scope = Scope.LAZY
    cls._lazy = True
    return cls


# ---- 方法装饰器 ----


def Maker(func):
    """@Maker — 标记方法返回值为 Bean"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._is_maker = True
    return wrapper


def noMaker(func):
    """@noMaker — 排除方法，不自动注册"""
    func._no_maker = True
    return func


# ---- 注入装饰器 ----


def _resolve_inject_params(func, kwargs):
    """解析并注入参数（共用逻辑）"""
    hints = {}
    for pname, param in inspect.signature(func).parameters.items():
        if param.annotation is not inspect.Parameter.empty:
            ann = param.annotation
            if isinstance(ann, str):
                try:
                    ann = eval(ann, getattr(func, '__globals__', {}))
                except Exception:
                    pass
            hints[pname] = ann

    for param_name, param_type in hints.items():
        if param_name in kwargs:
            continue
        if param_name == "self" or param_name == "cls":
            continue
        if param_type and hasattr(param_type, '__name__'):
            from pancake.factory.dough_factory import DoughFactory
            try:
                kwargs[param_name] = DoughFactory.get().resolve(param_type.__name__)
            except ValueError:
                pass
    return kwargs


def inject(func):
    """@inject — 自动注入依赖

    从 DoughFactory 解析参数类型对应的 Bean。
    自动检测被装饰函数是否为 async，返回对应的 wrapper。
    """
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            kwargs = _resolve_inject_params(func, kwargs)
            return await func(*args, **kwargs)

        async_wrapper.__annotations__ = {}
        if hasattr(async_wrapper, '__wrapped__'):
            delattr(async_wrapper, '__wrapped__')
        async_wrapper.__signature__ = inspect.Signature()
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            kwargs = _resolve_inject_params(func, kwargs)
            return func(*args, **kwargs)

        sync_wrapper.__annotations__ = {}
        if hasattr(sync_wrapper, '__wrapped__'):
            delattr(sync_wrapper, '__wrapped__')
        sync_wrapper.__signature__ = inspect.Signature()
        return sync_wrapper


# ---- 配置装饰器 ----


def Config(cls):
    """@Config — 从配置注入 Struct 字段"""
    original_on_init = cls.on_init

    @functools.wraps(original_on_init)
    def new_on_init(self):
        from pancake import settings
        for field_name in getattr(cls, '__dataclass_fields__', {}):
            if field_name.startswith("_"):
                continue
            config_key = f"{cls.__name__.lower()}.{field_name}"
            value = settings.get(config_key)
            if value is not None:
                setattr(self, field_name, value)
        original_on_init(self)

    cls.on_init = new_on_init
    return cls


# ---- 依赖声明装饰器 ----


def DependsOn(*deps: str):
    """@DependsOn — 声明 Bean 依赖

    告知 DoughFactory 在创建该 Bean 之前，
    必须先创建指定的依赖 Bean。

    Usage:
        @DependsOn("DatabaseService", "CacheService")
        class MyService(Dough): ...
    """
    def decorator(cls):
        cls._depends_on = list(deps)
        return cls
    return decorator


def Import(*classes: type):
    """@Import — 导入外部类到工厂

    在 DoughFactory.create_all() 阶段，自动将指定的外部类
    注册到工厂中，无需手动 register。

    Usage:
        @Import(DatabaseService, CacheService)
        class AppConfig(Configuration): ...
    """
    def decorator(cls):
        cls._imports = list(classes)
        return cls
    return decorator
