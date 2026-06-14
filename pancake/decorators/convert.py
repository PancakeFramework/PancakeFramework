"""类型转换装饰器 — @service, @configuration, @function, @struct"""

from pancake.registry import export
from pancake.decorators.inject import inject


def _check_dough_type(cls, target_type):
    """检查类是否已应用其他类型装饰器，防止冲突"""
    existing = getattr(cls, '_dough_type', None)
    if existing and existing != target_type:
        raise TypeError(
            f"类 {cls.__name__} 已应用 @{existing} 装饰器，"
            f"不能同时应用 @{target_type} 装饰器"
        )


_SKIP_ATTRS = frozenset({
    '__module__', '__qualname__', '__doc__', '__annotations__',
    '__dict__', '__weakref__', '__slots__',
})


def _convert_class(cls, *bases, dough_type=None):
    """将普通类转换为继承指定基类的 Dough 子类"""
    from pancake.dough import DoughMeta

    if dough_type:
        _check_dough_type(cls, dough_type)

    for base in bases:
        if isinstance(cls, type(base)):
            if dough_type:
                cls._dough_type = dough_type
            return cls

    if not isinstance(cls, DoughMeta):
        # 自动保留原始类上由装饰器设置的属性（跳过 dunder 和方法）
        preserved = {}
        for attr, val in cls.__dict__.items():
            if attr in _SKIP_ATTRS or attr.startswith('__'):
                continue
            if callable(val) and not isinstance(val, type):
                continue
            preserved[attr] = val

        new_cls = type(cls.__name__, (cls,) + bases, {
            '__module__': cls.__module__,
            '__qualname__': cls.__qualname__,
            '__doc__': cls.__doc__,
            '__annotations__': dict(cls.__annotations__),
            **preserved,
        })
    else:
        cls.__bases__ = bases + cls.__bases__
        new_cls = cls

    if dough_type:
        new_cls._dough_type = dough_type
    return new_cls


@export
def service(cls):
    """@service — 将类转换为 Service（类似 Spring @Service）"""
    from pancake.base.service import Service
    return _convert_class(cls, Service, dough_type="service")


@export
def configuration(cls):
    """@configuration — 将类转换为 Configuration（类似 Spring @Configuration）"""
    from pancake.base.configuration import Configuration
    return _convert_class(cls, Configuration, dough_type="configuration")


@export
def function(func):
    """@function — 将函数转换为 Function 类（类似 Spring @Bean 方法）

    自动添加 @inject 注入依赖，包装为 Function 子类。

    Usage:
        @function
        def my_func(service: MyService) -> str:
            return service.get_data()

        # 使用:
        result = my_func()
    """
    from pancake.base.function import Function

    injected_func = inject(func)

    class_name = ''.join(word.capitalize() for word in func.__name__.split('_'))

    def call(self, *args, **kwargs):
        return injected_func(*args, **kwargs)

    new_cls = type(class_name, (Function,), {
        'call': call,
        '__module__': func.__module__,
        '__qualname__': func.__qualname__,
        '__doc__': func.__doc__,
        '_dough_type': 'function',
    })

    return new_cls


@export
def struct(cls):
    """@struct — 将类标记为数据结构（类似 dataclass，不注册到 IoC 容器）

    与 @service/@configuration 不同，@struct 不会创建实例注册到 DoughFactory。
    适用于 DTO、表单、配置数据等纯数据容器。
    """
    from dataclasses import dataclass

    cls = dataclass(cls)
    cls._dough_type = "struct"
    return cls
