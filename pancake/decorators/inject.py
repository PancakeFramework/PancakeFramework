"""注入装饰器 — @inject, @inject_name"""

import functools
import inspect
from pancake.registry import export


class _InjectName:
    """标记对象，告诉 @inject 按 bean name 查找"""
    def __init__(self, name: str):
        self.name = name


@export
def inject_name(name_or_func=None):
    """@inject_name / @inject_name("name") — 自动按名称注入依赖

    两种用法:
    1. 作为装饰器: @inject_name — 按形参名注入
    2. 作为参数默认值: def f(db = inject_name("my_db")) — 按指定名注入
    """
    if isinstance(name_or_func, str):
        return _InjectName(name_or_func)
    if name_or_func is not None:
        return _make_inject_wrapper(name_or_func, by_name=True)
    return _InjectName(None)


def _resolve_inject_params(func, kwargs, by_name=False):
    """解析并注入参数

    Args:
        by_name: True 时按名称解析（忽略类型注解），False 时按类型解析
    """
    from pancake.factory.dough_factory import DoughFactory

    for pname, param in inspect.signature(func).parameters.items():
        if pname in kwargs or pname in ("self", "cls"):
            continue

        # 1. 默认值是 _InjectName → 按指定 name 解析
        if isinstance(param.default, _InjectName):
            target_name = param.default.name or pname
            try:
                kwargs[pname] = DoughFactory.get().resolve(target_name)
            except ValueError:
                pass
            continue

        if by_name:
            # @inject_name 模式：按形参名解析
            try:
                kwargs[pname] = DoughFactory.get().resolve(pname)
            except ValueError:
                pass
        else:
            # @inject 模式：按类型注解解析，无注解则按形参名
            if param.annotation is not inspect.Parameter.empty:
                ann = param.annotation
                if isinstance(ann, str):
                    try:
                        ann = eval(ann, getattr(func, '__globals__', {}))
                    except Exception:
                        pass
                if ann and hasattr(ann, '__name__'):
                    try:
                        kwargs[pname] = DoughFactory.get().resolve(ann.__name__)
                    except ValueError:
                        pass
            else:
                # 无类型注解 → 按形参名解析
                try:
                    kwargs[pname] = DoughFactory.get().resolve(pname)
                except ValueError:
                    pass

    return kwargs


def _make_inject_class(cls):
    """@inject 用于类 — 在 on_init 中自动注入类型注解的属性"""
    annotations = {}
    for base in reversed(cls.__mro__):
        if hasattr(base, '__annotations__'):
            annotations.update(base.__annotations__)

    # 从类型注解推导依赖，确保拓扑排序先创建依赖 Bean
    deps = []
    for attr_name, attr_type in annotations.items():
        if attr_name.startswith('_'):
            continue
        if isinstance(attr_type, type) and hasattr(attr_type, '__name__'):
            deps.append(attr_type.__name__)
    if deps:
        existing = getattr(cls, '_depends_on', [])
        cls._depends_on = list(set(existing + deps))

    original_on_init = cls.on_init

    async def _auto_inject_on_init(self):
        from pancake.factory.dough_factory import DoughFactory
        factory = DoughFactory.get()
        for attr_name, attr_type in annotations.items():
            if attr_name.startswith('_'):
                continue
            if getattr(self, attr_name, None) is not None:
                continue
            type_name = attr_type.__name__ if hasattr(attr_type, '__name__') else str(attr_type)
            try:
                setattr(self, attr_name, factory.resolve(type_name))
            except (ValueError, Exception):
                pass
        await original_on_init(self)

    cls.on_init = _auto_inject_on_init
    return cls


def _make_inject_wrapper(func, by_name=False):
    """创建注入 wrapper（@inject 和 @inject_name 共用）

    保留 __annotations__ 和 __wrapped__ 供类型检查和调试使用，
    仅将 __signature__ 设为空，防止外部框架按原始签名解析参数。
    """
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            kwargs = _resolve_inject_params(func, kwargs, by_name=by_name)
            return await func(*args, **kwargs)
        async_wrapper.__signature__ = inspect.Signature()
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            kwargs = _resolve_inject_params(func, kwargs, by_name=by_name)
            return func(*args, **kwargs)
        sync_wrapper.__signature__ = inspect.Signature()
        return sync_wrapper


@export
def inject(func_or_cls):
    """@inject — 自动按类型注入依赖

    用于函数: 自动解析参数
    用于类: 自动解析类型注解的属性（在 on_init 中注入）

    解析优先级:
    1. 参数默认值 inject_name("name") → 按 bean name
    2. 有类型注解 → 按类型名
    3. 无类型注解 → 按形参名
    """
    if isinstance(func_or_cls, type):
        return _make_inject_class(func_or_cls)
    return _make_inject_wrapper(func_or_cls, by_name=False)
