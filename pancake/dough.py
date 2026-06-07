"""
Dough 系统 — Bean 基类、元类、作用域
"""

from abc import ABC, ABCMeta
from enum import Enum


class Scope(Enum):
    """Bean 作用域"""
    SINGLETON = "singleton"  # 全局唯一（默认）
    PROTOTYPE = "prototype"  # 每次创建新实例
    LAZY = "lazy"           # 首次使用时创建


class DoughMeta(ABCMeta):
    """元类：自动注册类到全局注册表

    跳过名为 "Dough" 的类（基类自身）
    """
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        if name != "Dough":
            from pancake.registry import register_class
            register_class(name, cls)
        return cls


class Dough(ABC, metaclass=DoughMeta):
    """Bean 基类 — 所有框架类型的基础

    生命周期:
        1. __init__()     — 构造
        2. on_init()      — @PostConstruct, 属性注入后
        3. on_start()     — 就绪，开始服务
        4. [使用中]
        5. on_stop()      — 停止服务
        6. on_destroy()   — @PreDestroy, 销毁前
    """

    _scope: Scope = Scope.SINGLETON
    _lazy: bool = False
    _name: str = ""

    def __init__(self):
        pass

    def on_init(self):
        """@PostConstruct — 属性注入后调用"""
        pass

    def on_start(self):
        """就绪 — 开始服务"""
        pass

    def on_stop(self):
        """停止服务"""
        pass

    def on_destroy(self):
        """@PreDestroy — 销毁前调用"""
        pass
